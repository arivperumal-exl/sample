from mlflow.genai.judges import make_judge

sql_equivalence_judge = make_judge(
    name="sql_equivalence",
    instructions=(
        "Compare the generated SQL to the expected SQL. They are equivalent if they "
        "would return the same result, even if written differently (aliases, clause "
        "order, formatting, join syntax). "
        "Expected: {{ expectations }}\nGenerated: {{ outputs }}"
    ),
)

@scorer
def sql_correctness(expectations, trace):
    expected_map = expectations.get("expected_sql_by_agent")
    if not expected_map and expectations.get("expected_sql"):
        expected_map = {"_single": expectations["expected_sql"]}
    if not expected_map:
        return None

    genie_spans = [s for s in trace.data.spans if "genie" in s.name.lower()]
    per_agent_results = {}

    for agent_name, expected_sql in expected_map.items():
        matching_span = (
            genie_spans[0] if agent_name == "_single" and genie_spans
            else next((s for s in genie_spans if agent_name in s.name), None)
        )
        if matching_span is None:
            per_agent_results[agent_name] = False
            continue
        generated_sql = matching_span.outputs.get("query") or matching_span.outputs.get("sql")
        verdict = sql_equivalence_judge(
            expectations={"expected_sql": expected_sql},
            outputs={"generated_sql": generated_sql},
        )
        per_agent_results[agent_name] = verdict.value

    return Feedback(value=all(per_agent_results.values()), rationale=str(per_agent_results))
