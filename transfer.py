import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

url = f"{w.config.host}/serving-endpoints/your-supervisor-endpoint-name/invocations"
headers = w.config.authenticate()
headers["Content-Type"] = "application/json"
payload = {"messages": [{"role": "user", "content": "abc"}]}

response = requests.post(url, headers=headers, json=payload)
print(response.status_code)
print(response.text)   # <-- this is the part we actually need
