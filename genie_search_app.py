"""
Genie Agent Search App - Dummy/Demo Version
=============================================
Streamlit demo showing:
  - A central search box for asking questions
  - Left-sidebar filters: Unique ID, Line of Business (LOB) -- multi-select
  - Each LOB maps to its own "Genie" agent
  - A question can be routed to ONE agent or FANNED OUT to MULTIPLE agents
    at once (when the user selects more than one LOB, or asks a
    cross-LOB question), with the individual answers merged into one view.

Run with:
    pip install streamlit
    streamlit run genie_search_app.py

Replace the dummy agent functions / DUMMY_DATA with real Genie API calls
(e.g. Databricks Genie API) once ready.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

# ---------------------------------------------------------------------------
# 1. CONFIG / DUMMY DATA
# ---------------------------------------------------------------------------

# Dummy Unique IDs (e.g. customer/policy/account IDs) shown in the filter.
DUMMY_UNIQUE_IDS = ["ALL", "UID-1001", "UID-1002", "UID-1003", "UID-1004"]

# Each Line of Business (LOB) is served by its own Genie agent.
# Map LOB -> Genie space/agent id (dummy values, swap with real ones).
LOB_AGENT_MAP = {
    "Auto Insurance": "genie_space_auto_001",
    "Home Insurance": "genie_space_home_002",
    "Life Insurance": "genie_space_life_003",
    "Health Insurance": "genie_space_health_004",
}

LOB_OPTIONS = list(LOB_AGENT_MAP.keys())


# ---------------------------------------------------------------------------
# 2. GENIE AGENT CALL (DUMMY IMPLEMENTATION)
# ---------------------------------------------------------------------------
def call_genie_agent(agent_id: str, question: str, unique_id: str) -> dict:
    """
    Dummy stand-in for a real Genie agent call.

    In production, replace this with something like the Databricks Genie API:

        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        conversation = w.genie.start_conversation(space_id=agent_id, content=question)
        message = w.genie.wait_for_final_message(...)
        return message

    Here we just fake a short delay and return a canned response so the UI
    flow can be demoed end-to-end.
    """
    time.sleep(0.6)  # simulate network/agent latency

    return {
        "agent_id": agent_id,
        "answer": (
            f"[DUMMY RESPONSE from `{agent_id}`]\n\n"
            f"You asked: \"{question}\"\n"
            f"Filtered by Unique ID: {unique_id}\n\n"
            f"(This is placeholder text. Wire this function to the real "
            f"Genie agent API to get live answers.)"
        ),
        "sql": "SELECT * FROM dummy_table WHERE id = '{}' LIMIT 10;".format(unique_id),
    }


def route_question_to_agent(lob: str, question: str, unique_id: str) -> dict:
    """Pick the correct Genie agent for a single Line of Business and call it."""
    agent_id = LOB_AGENT_MAP[lob]
    result = call_genie_agent(agent_id=agent_id, question=question, unique_id=unique_id)
    result["lob"] = lob
    return result


def ask_multiple_genies(lobs: list, question: str, unique_id: str) -> list:
    """
    Fan the same question out to MULTIPLE Genie agents at once (one per
    selected LOB) and gather all responses. Each agent only knows about its
    own LOB's data, so this is how a cross-LOB question (e.g. "compare auto
    and home claims for this customer") gets answered: ask each relevant
    agent independently, then merge the answers in the UI.

    Uses a thread pool so the (network-bound) agent calls run concurrently
    instead of one after another.
    """
    results = []
    with ThreadPoolExecutor(max_workers=max(len(lobs), 1)) as pool:
        futures = {
            pool.submit(route_question_to_agent, lob, question, unique_id): lob
            for lob in lobs
        }
        for future in as_completed(futures):
            results.append(future.result())

    # keep results in the same order the user selected the LOBs
    order = {lob: i for i, lob in enumerate(lobs)}
    results.sort(key=lambda r: order[r["lob"]])
    return results


def synthesize_combined_answer(question: str, per_agent_results: list) -> str:
    """
    Dummy stand-in for a final "combine" step. In production you could send
    all the individual agent answers to an LLM to synthesize one cohesive
    answer to the original cross-LOB question. Here we just concatenate them.
    """
    if len(per_agent_results) <= 1:
        return ""

    lines = [f"**Combined summary across {len(per_agent_results)} lines of business:**", ""]
    for r in per_agent_results:
        lines.append(f"- **{r['lob']}**: {r['answer'].splitlines()[-1]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. STREAMLIT PAGE LAYOUT
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Genie Search Demo", layout="wide")

# ---- Sidebar: Filters -------------------------------------------------
with st.sidebar:
    st.header("Filters")

    selected_unique_id = st.selectbox(
        "Unique ID",
        options=DUMMY_UNIQUE_IDS,
        index=0,
        help="Filter results to a specific record.",
    )

    selected_lobs = st.multiselect(
        "Line of Business",
        options=LOB_OPTIONS,
        default=[],
        help=(
            "Determines which Genie agent(s) handle your question. "
            "Select more than one to ask a question across multiple "
            "lines of business at once."
        ),
    )

    st.markdown("---")
    if selected_lobs:
        st.caption("Active agent(s):")
        for lob in selected_lobs:
            st.caption(f"- {lob} → `{LOB_AGENT_MAP[lob]}`")
    else:
        st.caption("No agent selected yet.")

# ---- Main area: Centered search box -----------------------------------
st.title("Ask Genie")

# Center the search box using columns
left_pad, center, right_pad = st.columns([1, 2, 1])

with center:
    question = st.text_input(
        label="",
        placeholder="Ask a question about your data...",
        label_visibility="collapsed",
    )
    ask_clicked = st.button("Search", use_container_width=True)

# ---- Handle search --------------------------------------------------
if ask_clicked:
    if not selected_lobs:
        st.warning("Please choose at least one Line of Business from the left filter.")
    elif not question.strip():
        st.warning("Please enter a question.")
    else:
        spinner_msg = (
            f"Asking the {selected_lobs[0]} Genie agent..."
            if len(selected_lobs) == 1
            else f"Asking {len(selected_lobs)} Genie agents in parallel..."
        )
        with st.spinner(spinner_msg):
            results = ask_multiple_genies(
                lobs=selected_lobs,
                question=question,
                unique_id=selected_unique_id,
            )

        st.markdown("---")

        # If multiple LOBs were queried, show a combined summary first.
        if len(results) > 1:
            st.subheader("Combined Answer")
            st.markdown(synthesize_combined_answer(question, results))
            st.markdown("---")

        st.subheader("Answer" if len(results) == 1 else "Per-Agent Answers")

        # Each agent's raw answer, in its own tab, so it's clear which LOB
        # agent produced which part of the answer.
        tabs = st.tabs([r["lob"] for r in results])
        for tab, result in zip(tabs, results):
            with tab:
                st.caption(f"Agent: `{result['agent_id']}`")
                st.write(result["answer"])
                if result.get("sql"):
                    with st.expander("Generated SQL (debug)"):
                        st.code(result["sql"], language="sql")

# ---- Footer -------------------------------------------------------------
st.markdown("---")
st.caption(
    "Demo UI only. Search box → routes to the Genie agent(s) mapped to the "
    "selected Line(s) of Business, filtered by the chosen Unique ID. "
    "Selecting multiple lines of business fans the question out to each "
    "agent concurrently and merges their answers."
)
