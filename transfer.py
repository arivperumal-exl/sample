"""
Genie Agent Search App - Dummy/Demo Version
=============================================
Streamlit demo showing:
  - A central search box for asking questions
  - Left-sidebar filters: Unique ID, Line of Business (LOB)
  - Each LOB maps to its own "Genie" agent
  - Selecting a LOB routes the question to the matching agent

Run with:
    pip install streamlit
    streamlit run genie_search_app.py

Replace the dummy agent functions / DUMMY_DATA with real Genie API calls
(e.g. Databricks Genie API) once ready.
"""

import time
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

LOB_OPTIONS = ["Select Line of Business"] + list(LOB_AGENT_MAP.keys())


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
    """Pick the correct Genie agent for the selected Line of Business and call it."""
    if lob not in LOB_AGENT_MAP:
        return {"answer": "⚠️ Please select a valid Line of Business first.", "sql": None}

    agent_id = LOB_AGENT_MAP[lob]
    return call_genie_agent(agent_id=agent_id, question=question, unique_id=unique_id)


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

    selected_lob = st.selectbox(
        "Line of Business",
        options=LOB_OPTIONS,
        index=0,
        help="Determines which Genie agent handles your question.",
    )

    st.markdown("---")
    if selected_lob != "Select Line of Business":
        st.caption(f"Active agent: `{LOB_AGENT_MAP[selected_lob]}`")
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
    if selected_lob == "Select Line of Business":
        st.warning("Please choose a Line of Business from the left filter first.")
    elif not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner(f"Asking the {selected_lob} Genie agent..."):
            result = route_question_to_agent(
                lob=selected_lob,
                question=question,
                unique_id=selected_unique_id,
            )

        st.markdown("---")
        st.subheader("Answer")
        st.write(result["answer"])

        if result.get("sql"):
            with st.expander("Generated SQL (debug)"):
                st.code(result["sql"], language="sql")

# ---- Footer -------------------------------------------------------------
st.markdown("---")
st.caption(
    "Demo UI only. Search box → routes to the Genie agent mapped to the "
    "selected Line of Business, filtered by the chosen Unique ID."
)
