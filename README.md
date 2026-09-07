# Supervisor Agent chat app

Streamlit chat UI over a Databricks Supervisor Agent. Ask a question, the supervisor
routes it to Genie (or another subagent), and the app renders the answer, the SQL Genie
generated, and the result rows.

```
app.py             the app
requirements.txt   dependencies
app.yaml           Databricks Apps entry point
```

## Run it locally first

```bash
pip install -r requirements.txt

export DATABRICKS_HOST=https://<your-workspace-host>
export DATABRICKS_TOKEN=<personal-access-token>
export SUPERVISOR_ENDPOINT=<your-supervisor-endpoint>
export AUTH_MODE=pat

streamlit run app.py
```

The endpoint name is at **Agents → your supervisor → Endpoint**. Its task type must be
**Agent (Responses)** — the app calls the Responses API, not chat completions.

## Deploy to Databricks Apps

```bash
databricks apps create supervisor-chat
databricks sync . /Workspace/Users/<you>/supervisor-chat
databricks apps deploy supervisor-chat \
  --source-code-path /Workspace/Users/<you>/supervisor-chat
```

Then in the app's settings:

1. Set `SUPERVISOR_ENDPOINT` (edit `app.yaml`, or set it in the UI).
2. Add the supervisor serving endpoint as a **resource** with `CAN QUERY`.
3. Enable **user authorization** so the end user's token is forwarded.

With `AUTH_MODE=auto` the app detects the forwarded token and switches to
on-behalf-of-user automatically. Each viewer then queries as themselves, and the
supervisor's built-in access controls apply per person.

## Run it from a notebook instead

If you're demoing over the cluster driver proxy, keep `AUTH_MODE=pat` and follow the
driver-proxy notebook — every viewer will query as the token's owner.

## Grants the caller needs

| Object | Grant |
|---|---|
| Supervisor endpoint | `CAN QUERY` |
| Genie Agent | Access / `CAN RUN` |
| Unity Catalog tables | `SELECT`, plus `USE CATALOG` and `USE SCHEMA` |
| SQL warehouse | `CAN USE` |

Missing Genie or table grants do not raise an error. The supervisor quietly routes away
from what the caller can't reach, so the answer just looks unhelpful. Check grants first
whenever results seem thin.

## What the app handles

- **Streaming** — `response.output_text.delta` for prose, `response.output_item.done`
  for tool calls and their output.
- **Genie output** — generated SQL rendered with `st.code`, result rows with
  `st.dataframe`, plus a CSV download and an optional bar chart. Genie does not return
  its visualizations over the API, so charts are built app-side.
- **Subagent trace** — a sidebar toggle shows which subagent the supervisor called and
  with what arguments. Useful when routing looks wrong.
- **Fresh auth per turn** — the forwarded token is re-read on every request. Caching the
  client is what causes an app to work for a few minutes and then throw 401s.

## Verification note

The response-parsing helpers (`find_sql`, `find_columns`, `find_table`, `harvest`) were
reviewed by hand but not executed — the sandbox was unavailable. They are written
defensively and fall back to a raw-payload expander when a shape isn't recognized. If a
Genie result renders as raw JSON instead of a table, turn on the subagent trace, copy the
payload shape, and the key lists in those helpers can be widened to match.
