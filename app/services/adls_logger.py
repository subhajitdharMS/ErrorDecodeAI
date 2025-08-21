from azure.storage.blob import BlobServiceClient
import os
from app.core.config import get_settings
from app.models.schemas import NotificationPayload
import csv
from datetime import datetime
import io

class ADLSLogger:
    def __init__(self):
        settings = get_settings()
        self.account_url = settings.adls_account_url
        self.container_name = settings.adls_container_name
        self.credential = settings.adls_credential
        self.blob_name = settings.adls_blob_name or "analysis_log.csv"
        self.enabled = getattr(settings, "enable_adls_logging", False)
        if self.enabled:
            self.client = BlobServiceClient(account_url=self.account_url, credential=self.credential)

    def append_analysis(self, payload: NotificationPayload):
        if not self.enabled:
            return None
        # Download existing blob or create new
        try:
            blob_client = self.client.get_blob_client(container=self.container_name, blob=self.blob_name)
            try:
                stream = blob_client.download_blob().readall()
                content = stream.decode('utf-8')
            except Exception:
                content = ''
            output = io.StringIO()
            writer = csv.writer(output)
            if not content:
                writer.writerow([
                    "timestamp", "pipelineName", "runId", "activityName", "errorCode", "environment", "source", "component", "severity", "correlationId", "region", "resourceUrl", "simplified_error", "probable_reason", "probable_fix", "confidence"
                ])
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
            if content:
                output.write(content)
            writer.writerow(row)
            blob_client.upload_blob(output.getvalue(), overwrite=True)
            return self.blob_name
        except Exception as e:
            return None
