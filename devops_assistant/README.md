# AWS DevOps Assistant

Natural language → Bedrock reasoning → AWS actions.

## Project structure

```
devops_assistant/
├── main.py            # FastAPI app  (/ask endpoint)
├── bedrock_client.py  # Calls Claude via Bedrock
├── agentcore_app.py   # AgentCore-compatible entrypoint
├── tools/
│   └── aws_tools.py   # S3, CloudWatch, IAM, Lambda tools
└── requirements.txt
```

## Run locally

```bash
pip install -r devops_assistant/requirements.txt
uvicorn devops_assistant.main:app --reload
```

Then POST to `http://localhost:8000/ask`:

```json
{ "message": "create an S3 bucket named my-test-bucket-123" }
{ "message": "generate an IAM policy for Bedrock with InvokeModel access" }
{ "message": "explain what a Lambda cold start is" }
```

## Deploy to AgentCore

```bash
pip install bedrock-agentcore-starter-toolkit
agentcore configure --entrypoint devops_assistant/agentcore_app.py --region us-east-1
agentcore launch
agentcore invoke '{"prompt": "list my S3 buckets"}'
```

## Prerequisites

- AWS credentials configured (`aws configure` or env vars)
- Bedrock model access enabled for `anthropic.claude-3-sonnet-20240229-v1:0` in your region
