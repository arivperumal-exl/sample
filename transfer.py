# Databricks notebook source
# MAGIC %md
# MAGIC # Query an Agent Bricks Supervisor Agent
# MAGIC
# MAGIC Calls a deployed Supervisor Agent endpoint from Python and displays the answer.
# MAGIC
# MAGIC Auth is automatic inside a Databricks notebook -- the notebook runs as you, so no
# MAGIC host URL or token is needed.
# MAGIC
# MAGIC **Before you run:** you (or whoever runs this) need `CAN QUERY` on the supervisor
# MAGIC *and* access to every subagent it coordinates. See the troubleshooting cell at the bottom.

# COMMAND ----------

# MAGIC %pip install -U databricks-openai databricks-sdk

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Find your endpoint name
# MAGIC
# MAGIC Also visible on the **Agents** page -> your agent -> **Endpoint**.

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
for e in w.serving_endpoints.list():
    print(e.name)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Configure the client

# COMMAND ----------

from databricks_openai import DatabricksOpenAI

ENDPOINT = "<paste-your-endpoint-name-here>"

# Supervisors fan out to subagents and may run sandboxed code, so responses are slow.
client = DatabricksOpenAI(timeout=600)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Helper to extract the answer text
# MAGIC
# MAGIC Supervisor replies contain reasoning and tool-call items alongside the final message,
# MAGIC so don't index blindly into `resp.output[0]`.

# COMMAND ----------

def extract_text(resp):
    """Pull the assistant's text out of a Responses-API reply."""
    txt = getattr(resp, "output_text", None)
    if txt:
        return txt
    parts = []
    for item in (resp.output or []):
        for c in (getattr(item, "content", None) or []):
            if getattr(c, "type", None) in ("output_text", "text"):
                parts.append(c.text)
    return "\n".join(parts)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Ask a single question

# COMMAND ----------

question = "What were the top three drivers of usage growth last quarter?"

resp = client.responses.create(
    model=ENDPOINT,
    input=[{"role": "user", "content": question}],
)

print(extract_text(resp))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Stream the answer (recommended)
# MAGIC
# MAGIC Shows progress instead of leaving the cell hanging for a minute or more.

# COMMAND ----------

stream = client.responses.create(
    model=ENDPOINT,
    input=[{"role": "user", "content": question}],
    stream=True,
)

for chunk in stream:
    if getattr(chunk, "type", "") == "response.output_text.delta":
        print(chunk.delta, end="")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Multi-turn conversation
# MAGIC
# MAGIC The endpoint is stateless, so resend the history on every call.
# MAGIC
# MAGIC Only the assistant's text is appended (not the full `resp.output`) to keep the
# MAGIC payload clean and avoid resending tool-call items the endpoint may reject.

# COMMAND ----------

history = []


def ask(question, stream=False):
    history.append({"role": "user", "content": question})

    if stream:
        parts = []
        for chunk in client.responses.create(model=ENDPOINT, input=history, stream=True):
            if getattr(chunk, "type", "") == "response.output_text.delta":
                print(chunk.delta, end="")
                parts.append(chunk.delta)
        print()
        answer = "".join(parts)
    else:
        resp = client.responses.create(model=ENDPOINT, input=history)
        answer = extract_text(resp)

    history.append({"role": "assistant", "content": answer})
    return answer


print(ask("How many active users did we have in August?"))
print(ask("And how does that compare to July?"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Render nicely (optional)

# COMMAND ----------

answer = ask("Give me a short markdown summary of last quarter's performance.")

displayHTML(f"<div style='font-family:sans-serif;white-space:pre-wrap'>{answer}</div>")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reusable input widget (optional)

# COMMAND ----------

dbutils.widgets.text("question", "", "Ask the supervisor")

q = dbutils.widgets.get("question")
if q.strip():
    print(ask(q, stream=True))
else:
    print("Enter a question in the widget at the top of the notebook.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Troubleshooting
# MAGIC
# MAGIC | Symptom | Likely cause |
# MAGIC |---|---|
# MAGIC | `PERMISSION_DENIED` / 403 | You lack `CAN QUERY` on the supervisor. Agents page -> kebab menu -> Manage permissions. |
# MAGIC | Endpoint not in the `list()` output | Wrong workspace, or you have no permission to see it. |
# MAGIC | Agent replies but refuses to answer, or ends the conversation | You lack access to the **subagents**. Genie Agent needs the underlying UC grants; Knowledge Assistant needs `CAN QUERY` on its endpoint; UC function needs `EXECUTE`; UC table needs `SELECT` + `USE CATALOG` + `USE SCHEMA`. |
# MAGIC | Empty string from `extract_text` | Inspect the raw shape with `resp.model_dump()`. |
# MAGIC | Timeout | Raise `timeout` on the client, or use background mode -- see the Supervisor Agent long-running tasks docs. |
# MAGIC | `404` on `responses.create` | The endpoint may expose Chat Completions instead. Try `client.chat.completions.create(model=ENDPOINT, messages=[...])`. |
# MAGIC | First call is very slow, then fast | Scale-to-zero cold start. Normal. |
# MAGIC
# MAGIC If you schedule this as a job, it runs as a **service principal**, not as you --
# MAGIC that principal needs the same supervisor and subagent permissions listed above.
