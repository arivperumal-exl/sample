import json
from databricks.sdk import WorkspaceClient
from databricks_openai import DatabricksOpenAI

ENDPOINT = "<your-supervisor-endpoint-name>"

# Optional manual overrides: tool name / Genie space ID -> friendly name
MANUAL_NAMES = {
    # "01f0abc123...": "Sales Genie",
}

MAX_RESULT_CHARS = 500

w = WorkspaceClient()
client = DatabricksOpenAI()


def load_genie_names() -> dict:
    names = {}
    try:
        page_token = None
        while True:
            resp = (
                w.genie.list_spaces(page_token=page_token)
                if page_token
                else w.genie.list_spaces()
            )
            for s in resp.spaces or []:
                names[s.space_id] = s.title
            page_token = resp.next_page_token
            if not page_token:
                break
    except Exception as e:
        print(f"[warn] Could not list Genie spaces: {e}")
    names.update(MANUAL_NAMES)
    return names


GENIE_NAMES = load_genie_names()


def friendly_name(tool_name: str) -> str:
    for space_id, title in GENIE_NAMES.items():
        if space_id and space_id in tool_name:
            return title
    return tool_name


def format_args(arguments: str) -> str:
    try:
        data = json.loads(arguments)
    except Exception:
        return arguments

    if isinstance(data, dict):
        for key in ("query", "question", "input", "prompt", "text"):
            if key in data:
                return str(data[key])
        return "\n".join(str(v) for v in data.values())
    if isinstance(data, list):
        return "\n".join(str(v) for v in data)
    return str(data)


def truncate(text, limit: int = MAX_RESULT_CHARS) -> str:
    text = text if isinstance(text, str) else str(text)
    return text if len(text) <= limit else text[:limit] + "..."


def ask(question: str, debug: bool = False) -> None:
    stream = client.responses.create(
        model=ENDPOINT,
        input=[{"role": "user", "content": question}],
        stream=True,
    )

    step = 0
    answer_started = False

    for event in stream:
        if debug:
            print(event.model_dump())

        if event.type == "response.output_item.done":
            item = event.item

            if item.type == "function_call":
                step += 1
                print(f"\n🔧 Step {step}: {friendly_name(item.name)}")
                print(f"   ❓ {format_args(item.arguments)}")

            elif item.type == "function_call_output":
                print(f"   ✅ Result: {truncate(item.output)}")

            elif item.type == "reasoning":
                print("   💭 (reasoning)")

        elif event.type == "response.output_text.delta":
            if not answer_started:
                print("\n📝 Final answer:\n")
                answer_started = True
            print(event.delta, end="", flush=True)

    print()
