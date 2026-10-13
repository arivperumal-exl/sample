import mlflow.genai.datasets

dataset = mlflow.genai.datasets.get_dataset(name="catalog.schema.agent_eval_questions")

records = [
    {
        "inputs": {"question": "How many sales cases were there in Q3?"},
        "expectations": {"expected_response": "There were 42 sales cases in Q3."}
    },
    {
        "inputs": {"question": "What is the total count of support tickets last month?"},
        "expectations": {"expected_sql": "SELECT COUNT(*) FROM tickets WHERE ..."}
    },
    # add as many as you want here
]

dataset = dataset.merge_records(records)
