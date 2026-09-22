from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback

GENIE_SPAN_TYPES = ("TOOL", "AGENT")  # confirmed from Step 3

@scorer
def correct_routing(expectations, trace):
    expected = expectations.get("expected_agents") or expectations.get("expected_agent")
    if not expected:
        return None
    expected_agents = expected if isinstance(expected, list) else [expected]

    called_agents = [s.name for s in trace.data.spans if s.span_type in GENIE_SPAN_TYPES]
    missing = [a for a in expected_agents if not any(a in c for c in called_agents)]

    return Feedback(
        value=len(missing) == 0,
        rationale=f"Expected: {expected_agents} | Called: {called_agents} | Missing: {missing}",
    )
