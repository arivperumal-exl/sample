from mlflow.genai.judges import make_judge

correctness_judge = make_judge(
    name="correctness_check",
    instructions=(
        "Judge whether the response correctly answers the question asked, "
        "based on the data in the system. Mark it as failing if it makes up "
        "an answer using data that doesn't exist, or answers a different "
        "question than what was asked. "
        "Question: {{ inputs }}\nResponse: {{ outputs }}"
    ),
)
