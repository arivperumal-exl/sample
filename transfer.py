out_of_scope_order_judge = make_judge(
    name="out_of_scope_disclosed_first",
    instructions=(
        "The question in {{ inputs }} has one in-scope part and one out-of-scope part. "
        "Pass only if the response in {{ outputs }} states the out-of-scope part BEFORE "
        "answering the in-scope part. Fail if disclosure is missing or comes after."
    ),
)

@scorer
def out_of_scope_disclosed_first(inputs, outputs, expectations):
    if "before answering" not in str(expectations.get("expected_response", "")).lower():
        return None
    return out_of_scope_order_judge(inputs=inputs, outputs=outputs)
