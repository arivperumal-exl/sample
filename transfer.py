import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

def ask_my_agent(question: str) -> dict:
    url = f"{w.config.host}/serving-endpoints/your-supervisor-endpoint-name/invocations"
    headers = w.config.authenticate()  # SDK builds correct auth headers for you
    headers["Content-Type"] = "application/json"

    payload = {"messages": [{"role": "user", "content": question}]}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
