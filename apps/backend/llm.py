"""Claude via AWS Bedrock (Converse API). Only used by /chat and /finalize."""
import boto3
from .config import AWS_REGION, BEDROCK_MODEL_ID

_client = None


def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _client


def complete(system: str, messages: list[dict], max_tokens: int = 1500) -> str:
    """
    messages: [{"role": "user"|"assistant", "content": "..."}]
    Returns the assistant's text reply.
    """
    converse_messages = [
        {"role": m["role"], "content": [{"text": m["content"]}]} for m in messages
    ]
    resp = _bedrock().converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": system}],
        messages=converse_messages,
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.4},
    )
    return resp["output"]["message"]["content"][0]["text"]
