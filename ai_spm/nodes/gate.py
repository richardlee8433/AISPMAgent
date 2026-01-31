def governance_gate(state):
    print("🛑 Governance Gate")
    decision = input("Approve? (y/n): ")
    state.decision = "approve" if decision == "y" else "reject"
    return state
