def publish_lti(state):
    print("📣 Publishing to LTI:", state.artifact)
    state.version_pin = "v1-approved"
    return state
