from databricks.sdk import WorkspaceClient
import json

w = WorkspaceClient()
client = w.serving_endpoints.get_open_ai_client()

ENDPOINT = "<your-supervisor-endpoint-name>"
question = "Your question here"

stream = client.responses.create(
    model=ENDPOINT,
    input=[{"role": "user", "content": question}],
    stream=True,
)

step = 0
answer_started = False

for event in stream:
    etype = event.type

    # A completed output item = one "step"
    if etype == "response.output_item.done":
        item = event.item

        if item.type == "function_call":
            step += 1
            args = item.arguments
            try:
                args = json.dumps(json.loads(args), indent=2)
            except Exception:
                pass
            print(f"\n🔧 Step {step}: calling `{item.name}`\n{args}")

        elif item.type == "function_call_output":
            out = item.output
            print(f"   ✅ Result: {out[:500]}{'...' if len(out) > 500 else ''}")

        elif item.type == "reasoning":
            print("   💭 (reasoning)")

    # Final answer streams token by token
    elif etype == "response.output_text.delta":
        if not answer_started:
            print("\n📝 Final answer:\n")
            answer_started = True
        print(event.delta, end="", flush=True)

print()
