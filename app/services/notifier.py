from __future__ import annotations
import json
import httpx
from typing import List
from app.core.config import get_settings
from app.models.schemas import NotificationPayload
from .exceptions import NotificationDispatchError

async def send_teams(payload: NotificationPayload) -> None:
    settings = get_settings()
    if not settings.teams_webhook_url:
        return
    card = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": f"Pipeline Failure: {payload.pipelineName}",
        "themeColor": "EA4300",
        "title": f"Pipeline Failure: {payload.pipelineName}",
        "sections": [
            {
                "facts": [
                    {"name": "Run Id", "value": payload.runId or "-"},
                    {"name": "Activity", "value": payload.activityName or "-"},
                    {"name": "Error Code", "value": payload.errorCode or "-"},
                    {"name": "Environment", "value": payload.environment or "-"},
                    {"name": "Source", "value": getattr(payload, 'source', None) or "-"},
                    {"name": "Component", "value": getattr(payload, 'component', None) or "-"},
                    {"name": "Severity", "value": getattr(payload, 'severity', None) or "-"},
                    {"name": "Correlation Id", "value": getattr(payload, 'correlationId', None) or "-"},
                    {"name": "Region", "value": getattr(payload, 'region', None) or "-"},
                    {"name": "Tags", "value": ", ".join(getattr(payload, 'tags', []) or []) if getattr(payload, 'tags', None) else '-'},
                    {"name": "Link", "value": str(getattr(payload, 'resourceUrl', None) or '-')},
                ],
                "text": f"**Simplified:** {payload.analysis.simplified_error}\n\n**Reason:** {payload.analysis.probable_reason}\n\n**Fix:** {payload.analysis.probable_fix}"
            }
        ]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(settings.teams_webhook_url, json=card)
    if r.status_code >= 400:
        raise NotificationDispatchError(f"Teams webhook error {r.status_code}: {r.text}")

async def send_email(payload: NotificationPayload) -> None:
    settings = get_settings()
    if not settings.alert_emails or not settings.client_id or not settings.client_secret or not settings.tenant_id:
        return
    # Acquire token using client credentials via MS identity platform
    token_url = f"https://login.microsoftonline.com/{settings.tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(token_url, data=data)
        if token_resp.status_code >= 400:
            raise NotificationDispatchError(f"Auth fail: {token_resp.text}")
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise NotificationDispatchError("No access token returned")
        subject = f"[Failure] {payload.pipelineName} ({payload.environment or '-'})"
        body_html = f"""
<h3>Pipeline Failure: {payload.pipelineName}</h3>
<p>
  <b>Run Id:</b> {payload.runId or '-'}<br/>
  <b>Activity:</b> {payload.activityName or '-'}<br/>
  <b>Error Code:</b> {payload.errorCode or '-'}<br/>
  <b>Environment:</b> {payload.environment or '-'}<br/>
  <b>Source:</b> {getattr(payload, 'source', None) or '-'}<br/>
    <b>Component:</b> {getattr(payload, 'component', None) or '-'}<br/>
    <b>Severity:</b> {getattr(payload, 'severity', None) or '-'}<br/>
    <b>Correlation Id:</b> {getattr(payload, 'correlationId', None) or '-'}<br/>
    <b>Region:</b> {getattr(payload, 'region', None) or '-'}<br/>
  <b>Tags:</b> {', '.join(getattr(payload, 'tags', []) or []) if getattr(payload, 'tags', None) else '-'}<br/>
  <b>Link:</b> <a href="{str(getattr(payload, 'resourceUrl', None) or '#')}">Open</a>
</p>
<p><b>Simplified:</b> {payload.analysis.simplified_error}</p>
<p><b>Probable Reason:</b> {payload.analysis.probable_reason}</p>
<p><b>Probable Fix:</b> {payload.analysis.probable_fix}</p>
<p><b>Confidence:</b> {payload.analysis.confidence:.2f}</p>
<details><summary>Raw Error</summary><pre>{json.dumps(payload.raw_error)[:4000]}</pre></details>
"""
        graph_url = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail".format(sender=settings.sender_email or settings.alert_emails[0])
        mail_json = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in settings.alert_emails],
            },
            "saveToSentItems": "false"
        }
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        send_resp = await client.post(graph_url, headers=headers, json=mail_json)
        if send_resp.status_code >= 400:
            raise NotificationDispatchError(f"Graph sendMail error {send_resp.status_code}: {send_resp.text}")

async def dispatch_notifications(payload: NotificationPayload) -> None:
    # Fire Teams then email; failures raise.
    await send_teams(payload)
    await send_email(payload)
