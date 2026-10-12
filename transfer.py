import mlflow
import mlflow.genai.datasets
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

# TODO: your dataset name from Step 3 (check the Datasets tab for the exact name)
dataset = mlflow.genai.datasets.get_dataset(name="catalog.schema.agent_eval_questions")

# TODO: your agent's serving endpoint name (find it under "Serving" in the left sidebar)
w = WorkspaceClient()

def ask_my_agent(question: str) -> dict:
    response = w.serving_endpoints.query(
        name="your-supervisor-endpoint-name",
        messages=[ChatMessage(role=ChatMessageRole.USER, content=question)],
    )
    choice = response.choices[0] if response.choices else None
    message = choice.message if choice else None
    return {"response": message.content if message else ""}

with mlflow.start_run(run_name="first_eval_run"):
    results = mlflow.genai.evaluate(
        data=dataset,
        predict_fn=ask_my_agent,
    )
