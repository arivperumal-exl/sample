from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

def supervisor_predict_fn(question: str) -> dict:
    response = w.serving_endpoints.query(
        name="your-supervisor-endpoint-name",  # TODO: your actual endpoint name
        messages=[{"role": "user", "content": question}],
    )
    return {"response": response.choices[0].message.content}
