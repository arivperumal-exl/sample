out_of_scope_judge = make_judge(
    name="out_of_scope_handling",
    instructions=(
        "The question in {{ inputs }} asks about data not available in the system. "
        "Judge whether the response in {{ outputs }} correctly declines/states out of "
        "scope, rather than fabricating an answer using an unrelated domain's data. "
        "Fail if it answers with a specific number when it should have declined."
    ),
)

@scorer
def out_of_scope_handling(inputs, outputs, expectations):
    if "out of scope" not in str(expectations.get("expected_response", "")).lower():
        return None
    return out_of_scope_judge(inputs=inputs, outputs=outputs)
