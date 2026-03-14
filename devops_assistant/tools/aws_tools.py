"""
AWS tool implementations callable by the DevOps assistant.
Each function maps to a real boto3 action.
"""
import json
import boto3
from botocore.exceptions import ClientError


def create_s3_bucket(bucket_name: str, region: str = "us-east-1") -> dict:
    """Create an S3 bucket."""
    s3 = boto3.client("s3", region_name=region)
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        return {"status": "success", "bucket": bucket_name, "region": region}
    except ClientError as e:
        return {"status": "error", "message": str(e)}


def list_s3_buckets() -> dict:
    """List all S3 buckets in the account."""
    s3 = boto3.client("s3")
    try:
        response = s3.list_buckets()
        buckets = [b["Name"] for b in response.get("Buckets", [])]
        return {"status": "success", "buckets": buckets}
    except ClientError as e:
        return {"status": "error", "message": str(e)}


def get_cloudwatch_logs(log_group: str, limit: int = 20) -> dict:
    """Fetch the latest log events from a CloudWatch log group."""
    logs = boto3.client("logs")
    try:
        # Get the most recent log stream
        streams = logs.describe_log_streams(
            logGroupName=log_group,
            orderBy="LastEventTime",
            descending=True,
            limit=1,
        )
        if not streams["logStreams"]:
            return {"status": "error", "message": "No log streams found"}

        stream_name = streams["logStreams"][0]["logStreamName"]
        events = logs.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            limit=limit,
        )
        messages = [e["message"] for e in events["events"]]
        return {"status": "success", "log_group": log_group, "stream": stream_name, "events": messages}
    except ClientError as e:
        return {"status": "error", "message": str(e)}


def generate_iam_policy(service: str, actions: list[str], resource: str = "*") -> dict:
    """Generate a minimal IAM policy JSON for a given service and actions."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [f"{service}:{a}" for a in actions],
                "Resource": resource,
            }
        ],
    }
    return {"status": "success", "policy": json.dumps(policy, indent=2)}


def list_lambda_functions() -> dict:
    """List all Lambda functions in the account."""
    lam = boto3.client("lambda")
    try:
        response = lam.list_functions()
        functions = [
            {"name": f["FunctionName"], "runtime": f.get("Runtime", "N/A")}
            for f in response.get("Functions", [])
        ]
        return {"status": "success", "functions": functions}
    except ClientError as e:
        return {"status": "error", "message": str(e)}


# Registry maps tool names to callables — used by the agent router
TOOL_REGISTRY = {
    "create_s3_bucket": create_s3_bucket,
    "list_s3_buckets": list_s3_buckets,
    "get_cloudwatch_logs": get_cloudwatch_logs,
    "generate_iam_policy": generate_iam_policy,
    "list_lambda_functions": list_lambda_functions,
}
