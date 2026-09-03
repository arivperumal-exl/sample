"""Minimal Streamlit app that queries a Databricks Supervisor Agent.

Run locally:
    pip install streamlit openai databricks-sdk
    export DATABRICKS_HOST="https://adb-1234567890.12.azuredatabricks.net"
    export DATABRICKS_TOKEN="dapi..."
    streamlit run streamlit_supervisor_app.py

The endpoint name is entered in the sidebar, so nothing in this file needs editing.
"""

import os

import streamlit as st
from databricks.sdk import WorkspaceClient

st.set_page_config(page_title="Ask the supervisor", page_icon="*")
st.title("Ask the supervisor")

endpoint = st.sidebar.text_input(
    "Serving endpoint name",
    value=os.environ.get("SERVING_ENDPOINT", ""),
    help="Find it under Agents -> your agent -> Endpoint",
)
if st.sidebar.button("Clear conversation"):
    st.session_state.messages = []
    st.rerun()


@st.cache_resource
def get_client():
    """Authenticates from DATABRICKS_HOST/TOKEN, an OAuth service principal, or a
    Databricks notebook -- whichever is available."""
    client = WorkspaceClient().serving_endpoints.get_open_ai_client()
    return client.with_options(timeout=600)


def answer_text(resp):
    """Supervisor replies mix reasoning and tool-call items with the final message,
    so pull out the text rather than indexing into resp.output[0]."""
    txt = getattr(resp, "output_text", None)
    if txt:
        return txt
    parts = []
    for item in resp.output or []:
        for chunk in getattr(item, "content", None) or []:
            if getattr(chunk, "type", None) in ("output_text", "text"):
                parts.append(chunk.text)
    return "\n".join(parts)


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])

if question := st.chat_input("Ask a question"):
    if not endpoint:
        st.error("Enter your serving endpoint name in the sidebar first.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": question})
    st.chat_message("user").markdown(question)

    with st.chat_message("assistant"):
        slot = st.empty()
        slot.markdown("_Working..._")
        try:
            # The endpoint is stateless, so the full history goes with every call.
            resp = get_client().responses.create(
                model=endpoint,
                input=st.session_state.messages,
            )
            answer = answer_text(resp).strip()
            if not answer:
                answer = "_No text came back. This usually means missing access to the subagents._"
        except Exception as exc:
            answer = f"Request failed: {exc}"
        slot.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
