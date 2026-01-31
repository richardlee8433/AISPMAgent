def evaluate(state):
    print("📊 Evaluation: scoring output")
    state.evidence = {"score": 0.7, "risk": "medium"}
    return state
