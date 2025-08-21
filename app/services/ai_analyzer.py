from __future__ import annotations
import json
import httpx
from .exceptions import AIAnalysisError
import re
from app.core.config import get_settings
from app.models.schemas import AnalysisResult, FailureNotification

PROMPT_TEMPLATE = """You are an assistant that analyzes failure messages across Azure Data Factory, Synapse, Fabric, Databricks, Spark, Kubernetes, generic apps and services.
Return a concise JSON with keys: simplified_error, probable_reason, probable_fix.
Add a numeric field 'confidence' between 0 and 1 indicating how confident you are in the analysis.
Keep each value under 400 characters, no markdown, no extra keys.

Context:
Pipeline Name: {pipeline}
Activity: {activity}
Error Code: {code}
Environment: {environment}
Source: {source}
Component: {component}
Severity: {severity}
Correlation Id: {correlation_id}
Region: {region}
Resource URL: {resource_url}
Raw Error: {error}
"""

SENSITIVE_PATTERNS = [
    r"(?i)(password\s*=\s*)([^;\s]+)",
    r"(?i)(secret\s*=\s*)([^;\s]+)",
    r"(?i)(key\s*=\s*)([^;\s]+)",
    r"(?i)(pwd\s*=\s*)([^;\s]+)",
]

def redact(text: str) -> str:
    t = text
    for pat in SENSITIVE_PATTERNS:
        t = re.sub(pat, r"\1***", t)
    return t

async def analyze_failure(data: FailureNotification) -> AnalysisResult:
    settings = get_settings()
    if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
        # Fallback naive heuristic (no external call) for local testing
        return AnalysisResult(
            simplified_error=(data.errorMessage[:180] + '...') if len(data.errorMessage) > 180 else data.errorMessage,
            probable_reason="Heuristic: check connectivity / credentials / resource limits.",
            probable_fix="Validate linked service creds, network access, and activity configuration."
        )
    prompt = PROMPT_TEMPLATE.format(
        pipeline=data.pipelineName,
        activity=data.activityName or "N/A",
        code=data.errorCode or "N/A",
        environment=getattr(data, 'environment', None) or "N/A",
        source=getattr(data, 'source', None) or "N/A",
        component=getattr(data, 'component', None) or "N/A",
        severity=getattr(data, 'severity', None) or "N/A",
        correlation_id=getattr(data, 'correlationId', None) or "N/A",
        region=getattr(data, 'region', None) or "N/A",
        resource_url=str(getattr(data, 'resourceUrl', None) or "N/A"),
        error=redact(data.errorMessage)
    )
    # Minimal Azure OpenAI Chat Completions request using REST
    url = f"{settings.azure_openai_endpoint}openai/deployments/{settings.azure_openai_deployment}/chat/completions?api-version={settings.azure_openai_api_version}"
    headers = {"api-key": settings.azure_openai_api_key, "Content-Type": "application/json"}
    body = {
        "messages": [
            {"role": "system", "content": "You output only JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
        "response_format": {"type": "json_object"}
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=body)
    except httpx.RequestError as ex:
        # Network or DNS issue – fallback gracefully
        return AnalysisResult(
            simplified_error=(data.errorMessage[:180] + '...') if len(data.errorMessage) > 180 else data.errorMessage,
            probable_reason=f"Network error calling Azure OpenAI: {ex.__class__.__name__}",
            probable_fix="Verify endpoint DNS, firewall, and that deployment name is correct."
        )
    if r.status_code >= 400:
        # Provide structured fallback instead of raising to avoid 502 for operational issues
        return AnalysisResult(
            simplified_error=(data.errorMessage[:180] + '...') if len(data.errorMessage) > 180 else data.errorMessage,
            probable_reason=f"Azure OpenAI HTTP {r.status_code} - possibly bad deployment or key.",
            probable_fix="Confirm deployment name, rotate key, verify model availability in region."
        )
    try:
        content = r.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return AnalysisResult(**parsed)
    except Exception as e:  # noqa
        return AnalysisResult(
            simplified_error=(data.errorMessage[:180] + '...') if len(data.errorMessage) > 180 else data.errorMessage,
            probable_reason=f"Failed to parse AI response: {e.__class__.__name__}",
            probable_fix="Inspect raw response, adjust response_format or deployment model."
        )
