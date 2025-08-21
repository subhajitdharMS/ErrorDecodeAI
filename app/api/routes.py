from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from app.models.schemas import FailureNotification, NotificationPayload
from app.services import ai_analyzer, notifier
from app.services import csv_logger
from app.services.exceptions import AIAnalysisError, NotificationDispatchError
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["notify"])

async def api_key_auth(x_api_key: str = Header(...)):
    settings = get_settings()
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

@router.post("/notify")
async def notify_failure(payload: FailureNotification, return_only: bool = Query(False, description="If true, skip sending notifications and just return analysis."), auth=Depends(api_key_auth)):
    try:
        analysis = await ai_analyzer.analyze_failure(payload)
    except AIAnalysisError as e:
        raise HTTPException(status_code=502, detail=str(e))
    notif_payload = NotificationPayload(
        pipelineName=payload.pipelineName,
        runId=payload.runId,
        activityName=payload.activityName,
        errorCode=payload.errorCode,
        environment=payload.environment,
        source=getattr(payload, 'source', None),
        resourceUrl=getattr(payload, 'resourceUrl', None),
        component=getattr(payload, 'component', None),
        severity=getattr(payload, 'severity', None),
        tags=getattr(payload, 'tags', None),
        correlationId=getattr(payload, 'correlationId', None),
        region=getattr(payload, 'region', None),
        raw_error=payload.errorMessage,
        analysis=analysis
    )
    settings = get_settings()
    metadata = {
        "pipelineName": payload.pipelineName,
        "runId": payload.runId,
        "activityName": payload.activityName,
        "errorCode": payload.errorCode,
        "environment": payload.environment,
        "source": getattr(payload, 'source', None),
        "resourceUrl": getattr(payload, 'resourceUrl', None),
        "component": getattr(payload, 'component', None),
        "severity": getattr(payload, 'severity', None),
        "tags": getattr(payload, 'tags', None),
        "correlationId": getattr(payload, 'correlationId', None),
        "region": getattr(payload, 'region', None),
    }
    # Optional CSV logging
    csv_path = None
    try:
        csv_path = csv_logger.append_analysis(notif_payload)
    except Exception:
        csv_path = None
    if csv_path:
        metadata["csv_path"] = csv_path
    if return_only or settings.disable_notifications:
        return {"status": "analysis_only", "metadata": metadata, "analysis": analysis}
    try:
        await notifier.dispatch_notifications(notif_payload)
    except NotificationDispatchError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"status": "sent", "metadata": metadata, "analysis": analysis}
