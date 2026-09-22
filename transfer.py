import mlflow

trace = mlflow.get_trace("tr-your-trace-id")
for s in trace.data.spans:
    print(s.span_id, "| name:", s.name, "| type:", s.span_type)
    print("  outputs:", s.outputs)
