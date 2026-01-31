def archive_cos(state):
    print("🗂 Archiving to COS:", state.artifact)
    state.version_pin = "v1-archived"
    return state
