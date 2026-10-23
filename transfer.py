from mlflow.genai.judges import make_judge

agent_name_judge = make_judge(
    name="agent_name_check",
    instructions=(
        "Check whether the response mentions or refers to using the expected "
        "sub-agent/data source. This can be an exact name match, or a close "
        "paraphrase that clearly refers to the same source (e.g. 'sales data', "
        "'the sales system' both count as referring to 'sales_genie_space'). "
        "Fail only if there is no reasonable indication the expected source was used. "
        "Expected agent: {{ expectations }}\n"
        "Response: {{ outputs }}"
    ),
)
