"""
FastAPI backend — /ask endpoint routes natural language to AWS tools via Bedrock.
"""
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from devops_assistant.bedrock_client import ask_bedrock
from devops_assistant.tools.aws_tools import TOOL_REGISTRY

app = FastAPI(title="AWS DevOps Assistant")


class AskRequest(BaseModel):
    message: str


class AskResponse(BaseModel):
    reply: str
    action_taken: str | None = None
    result: dict | None = None


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    raw = ask_bedrock(req.message)

    # Try to parse as a tool-call JSON
    try:
        parsed = json.loads(raw)
        action = parsed.get("action")
        params = parsed.get("params", {})

        if action not in TOOL_REGISTRY:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        result = TOOL_REGISTRY[action](**params)
        return AskResponse(
            reply=f"Executed: {action}",
            action_taken=action,
            result=result,
        )
    except (json.JSONDecodeError, KeyError):
        # Bedrock returned plain text (explanation / informational)
        return AskResponse(reply=raw)


@app.get("/tools")
def list_tools():
    """Return available tool names."""
    return {"tools": list(TOOL_REGISTRY.keys())}
