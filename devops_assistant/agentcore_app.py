"""
AgentCore-compatible entrypoint.
Deploy this file with: agentcore configure --entrypoint devops_assistant/agentcore_app.py
                        agentcore launch
"""
import json
from bedrock_agentcore import BedrockAgentCoreApp

from devops_assistant.bedrock_client import ask_bedrock
from devops_assistant.tools.aws_tools import TOOL_REGISTRY

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    user_message = payload.get("prompt", "")
    if not user_message:
        return {"error": "No prompt provided"}

    raw = ask_bedrock(user_message)

    try:
        parsed = json.loads(raw)
        action = parsed.get("action")
        params = parsed.get("params", {})
        if action in TOOL_REGISTRY:
            result = TOOL_REGISTRY[action](**params)
            return {"action": action, "result": result}
    except (json.JSONDecodeError, KeyError):
        pass

    return {"reply": raw}


if __name__ == "__main__":
    app.run()
