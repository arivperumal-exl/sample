import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Get workspace URL and auth token automatically
host = w.config.host
token = w.config.token

def ask_my_agent(question: str) -> dict:
    url = f"{host}/serving-endpoints/your-supervisor-endpoint-name/invocations"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"messages": [{"role": "user", "content": question}]}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # throws a clear error if the HTTP call itself failed
    result = response.json()    # plain Python dict, no SDK typing involved

    return result
