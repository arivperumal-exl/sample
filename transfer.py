This is based on Databricks' official docs, current as of Aug 2026. Here's the full picture of what you can connect to a **Databricks Supervisor Agent** (their multi-agent orchestration product) as subagents/tools — up to 50 total per supervisor:

## Supported subagent/tool types

| Type | What it is | Permission end users need |
|---|---|---|
| **Genie Agent** | Natural-language querying over structured data (a Genie Space wrapped as an agent) | Access to the Genie Agent + underlying Unity Catalog objects |
| **Published dashboard** | A shared Databricks dashboard the supervisor can pull insights from | `CAN VIEW` on the dashboard |
| **Knowledge Assistant agent endpoint** | RAG-style chatbot over documents | `CAN QUERY` on the endpoint |
| **Model serving endpoint** | Any custom model served on Model Serving | `CAN QUERY` on the endpoint |
| **Unity Catalog function** | Custom tool/function registered in UC | `EXECUTE` on the function |
| **Unity Catalog table** | Direct table access | `SELECT` + `USE CATALOG`/`USE SCHEMA` |
| **Unity Catalog volume** | File/volume access | `READ VOLUME` + `USE CATALOG`/`USE SCHEMA` |
| **AI Search index** (Delta Sync only) | Vector search over embeddings | `USE CATALOG`/`USE SCHEMA` + `SELECT` on the index |
| **Another Supervisor Agent** | Nest supervisors (supervisor-of-supervisors) | `CAN QUERY` on that supervisor |
| **Web search** | Built-in, no setup — runs on `databricks-gpt-5` regardless of the model powering your supervisor | None extra; end user approves each search; requires workspace to have `databricks-gpt-5` allowlisted, and isn't available with the Enhanced Security & Compliance add-on |
| **External MCP server** | Any third-party MCP server, connected via UC or Databricks Marketplace | `USE CONNECTION` on the UC connection |
| **Unity Catalog MCP Service** | MCP service registered inside UC | `EXECUTE` + `USE CATALOG`/`USE SCHEMA` |
| **Custom MCP server** | Self-hosted MCP server (as a Databricks App) | `CAN_USE` on the app |
| **Custom agent** | Any agent you author and deploy as a Databricks App (via Responses API) | `CAN_USE` on the app |

## Also built in automatically
**Code execution** — every supervisor gets a sandboxed serverless code-exec tool (Python/SQL/shell) with no internet access and read-only access limited to the UC tables/volumes you've already added as tools. You don't configure this separately.

## Key constraints
- Max 50 agents/tools per supervisor.
- Access control cascades: end users only see/use subagents they personally have permission on — if they have none, the supervisor ends the conversation; if partial, it silently avoids the ones they can't reach.
- You can manage all of this via UI or the (Beta) Databricks SDK for Python (`SupervisorAgent`, `Tool` objects).

Source: [Databricks docs — Use Supervisor Agent](https://docs.databricks.com/aws/en/agents/agent-bricks/multi-agent-supervisor)

Want me to go deeper on any one integration type (e.g., how to wire up an external MCP server or a Genie Agent specifically)?
