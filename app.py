"""
Streamlit chat app for a Databricks Supervisor Agent (Agent Bricks) with Genie subagents.

Ask a question -> the supervisor routes it to Genie (or another subagent) -> the app
renders the prose answer, the SQL Genie generated, and the result rows.

Configuration (environment variables)
-------------------------------------
SUPERVISOR_ENDPOINT   Name of the supervisor serving endpoint.       [required]
AUTH_MODE             "auto" | "obo" | "pat"                         [default: auto]
                        obo  - use the end user's forwarded token (Databricks Apps)
                        pat  - use DATABRICKS_HOST / DATABRICKS_TOKEN
                        auto - obo if the header is present, else pat
DATABRICKS_HOST       https://<workspace-host>                       [pat mode]
DATABRICKS_TOKEN      Personal access token                          [pat mode]

Run locally:   SUPERVISOR_ENDPOINT=my-supervisor AUTH_MODE=pat streamlit run app.py
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient

DEFAULT_ENDPOINT = os.getenv("SUPERVISOR_ENDPOINT", "")
AUTH_MODE = os.getenv("AUTH_MODE", "auto").lower()

st.set_page_config(page_title="Ask the Supervisor Agent", page_icon="🧭", layout="wide")


# ==========================================================================
# Auth / client
# ==========================================================================
def forwarded_token() -> str | None:
    """The end user's token, injected by Databricks Apps on every request."""
    try:
        return st.context.headers.get("X-Forwarded-Access-Token")
    except Exception:
        return None


def get_client():
    """Return an OpenAI-compatible client aimed at Databricks Model Serving.

    Never cache this. Under on-behalf-of-user auth the forwarded token is
    short-lived and goes stale across Streamlit WebSocket reconnects, which
    shows up as an app that works for a few minutes then throws 401s.
    """
    token = forwarded_token()
    mode = AUTH_MODE
    if mode == "auto":
        mode = "obo" if token else "pat"

    if mode == "obo":
        if not token:
            raise RuntimeError(
                "AUTH_MODE=obo but no X-Forwarded-Access-Token header was found. "
                "Run inside Databricks Apps with user authorization enabled, "
                "or set AUTH_MODE=pat."
            )
        w = WorkspaceClient(token=token, auth_type="pat")
    else:
        w = WorkspaceClient()  # reads DATABRICKS_HOST / DATABRICKS_TOKEN

    return w.serving_endpoints.get_open_ai_client(), mode


# ==========================================================================
# Parsing the Responses API output
# ==========================================================================
def as_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    for attr in ("model_dump", "dict"):
        if hasattr(obj, attr):
            try:
                return getattr(obj, attr)()
            except Exception:
                pass
    return {}


def maybe_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


def find_sql(node: Any, depth: int = 0) -> str | None:
    """Genie's generated SQL, wherever the endpoint decided to nest it."""
    if depth > 6 or not isinstance(node, (dict, list)):
        return None
    if isinstance(node, dict):
        for key in ("query", "sql", "generated_sql", "statement", "query_text"):
            val = node.get(key)
            if isinstance(val, str) and val.strip().lower().startswith(
                ("select", "with", "show", "describe")
            ):
                return val
        for val in node.values():
            found = find_sql(val, depth + 1)
            if found:
                return found
    else:
        for val in node:
            found = find_sql(val, depth + 1)
            if found:
                return found
    return None


def find_columns(node: Any, depth: int = 0) -> list[str]:
    """Column names, which often live in a sibling manifest rather than beside the rows."""
    if depth > 6 or not isinstance(node, (dict, list)):
        return []
    if isinstance(node, dict):
        cols = node.get("columns")
        if isinstance(cols, list) and cols:
            names = [c.get("name") if isinstance(c, dict) else c for c in cols]
            names = [n for n in names if isinstance(n, str)]
            if names:
                return names
        for val in node.values():
            names = find_columns(val, depth + 1)
            if names:
                return names
    else:
        for val in node:
            names = find_columns(val, depth + 1)
            if names:
                return names
    return []


def find_table(node: Any, depth: int = 0) -> tuple[list, list] | None:
    """Return (rows, column_names) from a Genie result set, if present."""
    if depth > 6 or not isinstance(node, (dict, list)):
        return None

    if isinstance(node, dict):
        rows = None
        for key in ("data_array", "data", "rows", "records", "result"):
            candidate = node.get(key)
            if isinstance(candidate, list) and candidate:
                rows = candidate
                break

        if rows and isinstance(rows[0], (list, tuple)):
            cols = node.get("columns") or node.get("schema") or []
            if isinstance(cols, dict):
                cols = cols.get("columns", [])
            names = [c.get("name") if isinstance(c, dict) else c for c in cols]
            return rows, [n for n in names if n]

        if rows and isinstance(rows[0], dict):
            return rows, list(rows[0].keys())

        for val in node.values():
            found = find_table(val, depth + 1)
            if found:
                return found
    else:
        for val in node:
            found = find_table(val, depth + 1)
            if found:
                return found
    return None


def harvest(item: Any) -> list[dict]:
    """Turn one response output item into renderable artifacts."""
    d = as_dict(item)
    itype = d.get("type", "")
    out: list[dict] = []

    if itype in ("function_call", "tool_call", "custom_tool_call"):
        out.append(
            {
                "kind": "call",
                "name": d.get("name") or d.get("tool_name") or "subagent",
                "args": maybe_json(d.get("arguments") or d.get("input") or {}),
            }
        )
        return out

    if itype in ("function_call_output", "tool_call_output", "custom_tool_call_output"):
        payload = maybe_json(d.get("output", d))
        sql = find_sql(payload)
        if sql:
            out.append({"kind": "sql", "sql": sql})
        table = find_table(payload)
        if table:
            rows, cols = table
            # Databricks statement responses keep the schema in a sibling manifest,
            # so fall back to a whole-payload search when the rows came bare.
            if not cols:
                cols = find_columns(payload)
            if cols and rows and isinstance(rows[0], (list, tuple)):
                cols = cols[: len(rows[0])]
            out.append({"kind": "table", "rows": rows, "cols": cols})
        if not out:
            out.append({"kind": "raw", "payload": payload})
        return out

    return out


def collect_text(response: Any) -> str:
    if getattr(response, "output_text", None):
        return response.output_text
    parts = []
    for item in getattr(response, "output", None) or []:
        d = as_dict(item)
        if d.get("type") in ("message", "output_message"):
            for chunk in d.get("content") or []:
                c = as_dict(chunk)
                if c.get("type") in ("output_text", "text"):
                    parts.append(c.get("text", ""))
    return "".join(parts)


# ==========================================================================
# Rendering
# ==========================================================================
def widget_key(prefix: str) -> str:
    """Stable, unique widget keys. Streamlit rejects duplicates, and two identical
    result tables in one conversation would otherwise collide."""
    n = st.session_state.get("_kseq", 0) + 1
    st.session_state["_kseq"] = n
    return f"{prefix}_{n}"


def render_artifact(art: dict) -> None:
    kind = art["kind"]

    if kind == "call":
        with st.expander(f"🔧 Delegated to `{art['name']}`"):
            st.code(json.dumps(art["args"], indent=2, default=str), language="json")

    elif kind == "sql":
        with st.expander("🧾 Generated SQL"):
            st.code(art["sql"], language="sql")

    elif kind == "table":
        try:
            df = pd.DataFrame(art["rows"], columns=art["cols"] or None)
        except Exception:
            st.write(art["rows"])
            return
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Genie returns no visualizations over the API, so offer a chart ourselves.
        label = df.columns[0]
        plot_cols = [c for c in df.select_dtypes("number").columns if c != label]
        if len(df) > 1 and plot_cols:
            with st.expander("📊 Quick chart"):
                st.bar_chart(df.set_index(label)[plot_cols])

        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode(),
            file_name="genie_result.csv",
            mime="text/csv",
            key=widget_key("dl"),
        )

    elif kind == "raw":
        with st.expander("📎 Subagent output"):
            st.write(art["payload"])


def render_message(msg: dict, show_trace: bool) -> None:
    with st.chat_message(msg["role"]):
        if msg.get("content"):
            st.markdown(msg["content"])
        for art in msg.get("artifacts", []):
            if art["kind"] in ("call", "raw") and not show_trace:
                continue
            render_artifact(art)


# ==========================================================================
# Calling the supervisor
# ==========================================================================
def ask(client, endpoint: str, history: list[dict], stream: bool, show_trace: bool):
    """Returns (answer_text, artifacts)."""
    payload = [{"role": m["role"], "content": m["content"]} for m in history if m.get("content")]
    artifacts: list[dict] = []

    if not stream:
        resp = client.responses.create(model=endpoint, input=payload)
        for item in getattr(resp, "output", None) or []:
            artifacts.extend(harvest(item))
        text = collect_text(resp)
        st.markdown(text)
        for art in artifacts:
            if art["kind"] in ("call", "raw") and not show_trace:
                continue
            render_artifact(art)
        return text, artifacts

    with st.spinner("Routing to a subagent…"):
        events = client.responses.create(model=endpoint, input=payload, stream=True)

    slot = st.empty()
    buf: list[str] = []
    for event in events:
        etype = getattr(event, "type", "") or ""
        if etype.endswith("output_text.delta"):
            buf.append(getattr(event, "delta", "") or "")
            slot.markdown("".join(buf) + "▌")
        elif etype.endswith("output_item.done"):
            artifacts.extend(harvest(getattr(event, "item", None)))
        elif etype == "error":
            st.error(getattr(event, "message", "Streaming error"))

    text = "".join(buf)
    slot.markdown(text)
    for art in artifacts:
        if art["kind"] in ("call", "raw") and not show_trace:
            continue
        render_artifact(art)
    return text, artifacts


# ==========================================================================
# UI
# ==========================================================================
st.session_state.setdefault("messages", [])

with st.sidebar:
    st.markdown("### Connection")
    endpoint = st.text_input(
        "Supervisor endpoint",
        value=DEFAULT_ENDPOINT,
        placeholder="my-supervisor-agent",
        help="Agents → your supervisor → Endpoint. Task type must be Agent (Responses).",
    )
    stream_on = st.toggle("Stream the answer", value=True)
    show_trace = st.toggle("Show subagent trace", value=True)

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    tok = forwarded_token()
    st.caption(
        f"Auth: **{'on-behalf-of-user' if tok else 'service principal / PAT'}**\n\n"
        + ("Queries run as the signed-in user." if tok else "Queries run as one shared identity.")
    )

st.title("🧭 Ask the Supervisor Agent")
st.caption("Questions are routed to Genie and your other subagents. Answers, SQL and rows appear below.")

if not endpoint:
    st.info("Enter your supervisor endpoint name in the sidebar to start.")
    st.stop()

st.session_state["_kseq"] = 0  # reset widget-key counter for this script run
for msg in st.session_state.messages:
    render_message(msg, show_trace)

if prompt := st.chat_input("e.g. Which region grew fastest last quarter?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            client, mode = get_client()
            answer, artifacts = ask(
                client, endpoint, st.session_state.messages, stream_on, show_trace
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "artifacts": artifacts}
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"{type(exc).__name__}: {exc}")
            st.markdown(
                "**Check, in order:**\n"
                "- The endpoint's task type is **Agent (Responses)** — a chat-completions "
                "model will 404 here.\n"
                "- The caller has `CAN QUERY` on the supervisor endpoint.\n"
                "- The caller has access to the Genie Agent, `SELECT` on its Unity Catalog "
                "tables, and `CAN USE` on the SQL warehouse.\n"
                "- In `pat` mode, `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are set."
            )
            st.session_state.messages.pop()  # drop the unanswered turn
