def supervisor_predict_fn(question: str) -> dict:
    result = my_supervisor_agent.invoke({"messages": [{"role": "user", "content": question}]})
    return {"response": result["messages"][-1]["content"]}
