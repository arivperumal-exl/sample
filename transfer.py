from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

w = WorkspaceClient()

def supervisor_predict_fn(question: str) -> dict:
    response = w.serving_endpoints.query(
        name="your-supervisor-endpoint-name",  # <-- put your actual endpoint name here
        messages=[
            ChatMessage(role=ChatMessageRole.USER, content=question)
        ],
    )
    return {"response": response.choices[0].message.content}
