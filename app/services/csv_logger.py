from __future__ import annotations
import csv
import os
from datetime import datetime
from typing import Optional
from app.core.config import get_settings
from app.models.schemas import NotificationPayload

CSV_HEADERS = [
    "timestamp",
    "pipelineName",
    "runId",
    "activityName",
    "errorCode",
    "environment",
    "source",
    "component",
    "severity",
    "correlationId",
    "region",
    "resourceUrl",
    "simplified_error",
    "probable_reason",
    "probable_fix",
    "confidence",
]

def _resolve_path() -> str:
    settings = get_settings()
    return settings.csv_log_path or os.path.join(os.getcwd(), "analysis_log.csv")

def append_analysis(payload: NotificationPayload) -> Optional[str]:
    # Wrapper to choose between CSV and ADLS logging
    settings = get_settings()
    if getattr(settings, "enable_adls_logging", False):
        from app.services.adls_logger import ADLSLogger
        logger = ADLSLogger()
        return logger.append_analysis(payload)
    elif getattr(settings, "enable_csv_logging", False):
        path = _resolve_path()
        try:
            log_payload(payload)
            return path
        except Exception:
            return None
    else:
        return None

def log_payload(payload: NotificationPayload) -> None:
    settings = get_settings()
    if not getattr(settings, "enable_csv_logging", False):
        return
    path = _resolve_path()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    file_exists = os.path.isfile(path)
    row = [
        datetime.utcnow().isoformat(),
        payload.pipelineName,
        payload.runId or '',
        payload.activityName or '',
        payload.errorCode or '',
        payload.environment or '',
        getattr(payload, 'source', None) or '',
        getattr(payload, 'component', None) or '',
        getattr(payload, 'severity', None) or '',
        getattr(payload, 'correlationId', None) or '',
        getattr(payload, 'region', None) or '',
        str(getattr(payload, 'resourceUrl', None) or ''),
        (payload.analysis.simplified_error or '').replace('\n',' ')[:4000],
        (payload.analysis.probable_reason or '').replace('\n',' ')[:4000],
        (payload.analysis.probable_fix or '').replace('\n',' ')[:4000],
        f"{getattr(payload.analysis, 'confidence', 0.0):.2f}",
    ]
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(path) == 0:
            writer.writerow(CSV_HEADERS)
        writer.writerow(row)
