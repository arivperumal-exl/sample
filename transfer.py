from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback

@scorer
def agent_name_mentioned(outputs, expectations):
    expected_name = expectations.get("expected_agent_name")
    response_text = outputs.get("response", "")
    passed = expected_name.lower() in response_text.lower()
    return Feedback(
        value=passed,
        rationale=f"Looking for '{expected_name}' in response: {'found' if passed else 'not found'}",
    )
