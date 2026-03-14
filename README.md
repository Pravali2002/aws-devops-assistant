# AWS DevOps Assistant — How It Works

## What We Built

A backend service where a developer types something like *"create an S3 bucket"* in plain English, and the system figures out what AWS action to run and actually runs it.

**The flow:**
```
User message → FastAPI → Bedrock (Claude) → AWS tool → response
```

---

## Project Structure

```
devops_assistant/
├── main.py              ← FastAPI app (/ask endpoint)
├── bedrock_client.py    ← Sends prompts to Claude via Bedrock
├── agentcore_app.py     ← AgentCore-compatible entrypoint
├── tools/
│   └── aws_tools.py     ← S3, CloudWatch, IAM, Lambda tools
└── requirements.txt
```

---

## File by File

### `requirements.txt`

**How we finalized the dependencies:**
The goal was to keep it minimal — only pull in what's strictly needed for each layer of the stack. No extra frameworks, no bloat. Here's the reasoning behind each choice:

| Dependency | Why this one | Why not alternatives |
|---|---|---|
| `fastapi` | Modern, fast, async-ready Python web framework with automatic docs at `/docs` | Flask is older and more manual; Django is overkill for a single endpoint |
| `uvicorn` | The ASGI server that actually runs FastAPI | Gunicorn alone can't run async FastAPI apps; uvicorn is the standard pairing |
| `boto3` | Official AWS SDK for Python — the only real choice for talking to AWS services | No real alternative; it's maintained by AWS itself |
| `pydantic` | FastAPI uses it internally for request/response validation; we use it to define `AskRequest` and `AskResponse` shapes | Already a FastAPI dependency, so zero extra cost |
| `bedrock-agentcore` | Required wrapper to deploy the agent to AgentCore Runtime — provides `BedrockAgentCoreApp` | Only needed for AgentCore deployment; not used in local FastAPI mode |

**Why we pinned versions (e.g. `fastapi==0.111.0`):**
Pinning prevents surprise breakages when you install on a different machine or later date. These were the latest stable versions at the time of writing.

---

### `tools/aws_tools.py`
Where the actual AWS actions live. Each function does one thing:

| Function | What it does |
|---|---|
| `create_s3_bucket` | Creates an S3 bucket via boto3 |
| `list_s3_buckets` | Lists all buckets in your account |
| `get_cloudwatch_logs` | Fetches recent log events from a log group |
| `generate_iam_policy` | Builds a policy JSON (no AWS call, just constructs it) |
| `list_lambda_functions` | Lists all Lambda functions |

At the bottom there's a `TOOL_REGISTRY` dict — a simple lookup table of string name → function. The router uses it to call the right tool by name.

---

### `bedrock_client.py`
Talks to Claude via Amazon Bedrock. It sends the user's message with a system prompt that tells Claude:

> "If the user wants an AWS action, respond with JSON like `{"action": "create_s3_bucket", "params": {"bucket_name": "my-bucket"}}`"
> "If it's a question, just answer in plain text."

Claude acts as the brain — it reads the natural language and decides what tool to call and with what parameters.

---

### `main.py`
The FastAPI entry point. Exposes one main endpoint: `POST /ask`

What happens when you send a message:
1. Your message hits `/ask`
2. It gets sent to `ask_bedrock()` — Claude reads it and responds
3. We try to parse the response as JSON
   - **If it parses** → it's a tool call. We look up the action in `TOOL_REGISTRY` and run it
   - **If it doesn't parse** → Claude gave a plain text answer. We return that directly

There's also a `GET /tools` endpoint that lists available tool names.

---

### `agentcore_app.py`
Same logic as `main.py` but wrapped for AgentCore deployment. AgentCore expects this exact pattern:

```python
app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context):
    ...

if __name__ == "__main__":
    app.run()
```

When you run `agentcore launch`, it packages this file, deploys it as a serverless container on AWS, and gives you a managed endpoint — no server to manage yourself.

---

## The Big Picture

```
You type:  "create an S3 bucket named my-bucket"
                        ↓
           FastAPI /ask receives it
                        ↓
           Claude (Bedrock) reads it + system prompt
           Claude responds:
           {"action": "create_s3_bucket", "params": {"bucket_name": "my-bucket"}}
                        ↓
           main.py parses JSON, looks up "create_s3_bucket" in TOOL_REGISTRY
                        ↓
           boto3 actually creates the bucket on AWS
                        ↓
           You get back: {"status": "success", "bucket": "my-bucket"}
```

If you ask something like *"explain what a Lambda cold start is"*, Claude answers in plain text and no AWS action is taken.

---

## How to Run Locally

```bash
pip install -r devops_assistant/requirements.txt
uvicorn devops_assistant.main:app --reload
```

Example requests:

```bash
# Create a bucket
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "create an S3 bucket named my-devops-bucket-123"}'

# Generate an IAM policy
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "generate an IAM policy for bedrock with InvokeModel access"}'

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "explain what a Lambda cold start is"}'
```

---

## Deploy to AgentCore (Optional)

```bash
pip install bedrock-agentcore-starter-toolkit
agentcore configure --entrypoint devops_assistant/agentcore_app.py --region us-east-1
agentcore launch
agentcore invoke '{"prompt": "list my S3 buckets"}'
```

---

## Is This Connected to AWS?

Yes — this project uses `boto3` which reads your AWS credentials automatically from your environment.
It checks in this order:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file (set by `aws configure`)
3. IAM role attached to the machine (if running on EC2/ECS/Lambda)

**To verify your connection is working:**
```bash
aws sts get-caller-identity
```
You should see your Account ID, User ID, and ARN. If you get an error, your credentials are not set up.

---

## Prerequisites

- AWS credentials configured — run `aws configure` and enter your Access Key, Secret Key, and region
- Bedrock model access enabled for `anthropic.claude-3-sonnet-20240229-v1:0` in your region
  - Go to AWS Console → Amazon Bedrock → Model access → Request access for Claude 3 Sonnet

---

## Running on a New System (Anyone's Machine)

Step by step from scratch:

**1. Clone or copy the project**
```bash
git clone <your-repo-url>
cd devops_assistant
```

**2. Set up Python (3.10+ required)**
```bash
python --version   # should be 3.10 or higher
```

**3. Create a virtual environment (recommended)**
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Configure AWS credentials**
```bash
aws configure
# Enter: AWS Access Key ID
# Enter: AWS Secret Access Key
# Enter: Default region (e.g. us-east-1)
# Enter: Output format (json)
```

**6. Run the server**
```bash
uvicorn devops_assistant.main:app --reload
```

**7. Test it**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "list my S3 buckets"}'
```

---

## Containerizing with Docker

If you want to package this as a Docker container (for deployment to ECS, Kubernetes, or just consistent environments):

**1. Create a `Dockerfile` in the project root**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY devops_assistant/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY devops_assistant/ ./devops_assistant/

EXPOSE 8000

CMD ["uvicorn", "devops_assistant.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. Build the image**
```bash
docker build -t devops-assistant .
```

**3. Run the container**

Pass AWS credentials as environment variables (never bake them into the image):
```bash
docker run -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_DEFAULT_REGION=us-east-1 \
  devops-assistant
```

Or mount your local credentials file:
```bash
docker run -p 8000:8000 \
  -v ~/.aws:/root/.aws:ro \
  devops-assistant
```

**4. Test it**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "list my S3 buckets"}'
```

**Tip:** If deploying to AWS ECS or EKS, attach an IAM role to the task/pod instead of passing credentials — that's the secure production approach.
