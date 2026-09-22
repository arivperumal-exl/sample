import mlflow

mlflow.set_experiment("/Users/you@company.com/genie-supervisor-eval")

with mlflow.start_run(run_name="supervisor_eval_v1"):
    results = mlflow.genai.evaluate(
        data=dataset,
        predict_fn=supervisor_predict_fn,
        scorers=[correct_routing, sql_correctness, out_of_scope_handling, out_of_scope_disclosed_first],
    )
