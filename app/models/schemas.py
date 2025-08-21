from __future__ import annotations
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

class FailureNotification(BaseModel):
    pipelineName: str
    runId: Optional[str] = None
    activityName: Optional[str] = None
    errorMessage: str
    errorCode: Optional[str] = None
    timestamp: Optional[datetime] = None
    environment: Optional[str] = Field(default="prod")
    source: Optional[str] = Field(default=None, description="Origin of the call, e.g., adf|synapse|fabric|databricks|app|other")
    resourceUrl: Optional[HttpUrl] = Field(default=None, description="Link to the failing resource/run details")
    component: Optional[str] = Field(default=None, description="Sub-system, e.g., ingestion|transform|api|db|ui|batch")
    severity: Optional[str] = Field(default="error", description="Severity level: info|warning|error|critical")
    tags: Optional[List[str]] = Field(default=None, description="Free-form routing tags")
    correlationId: Optional[str] = Field(default=None, description="Trace/span/run correlation id")
    region: Optional[str] = Field(default=None, description="Azure or deployment region")

class AnalysisResult(BaseModel):
    simplified_error: str
    probable_reason: str
    probable_fix: str
    confidence: float = 0.6

class NotificationPayload(BaseModel):
    pipelineName: str
    runId: Optional[str]
    activityName: Optional[str]
    errorCode: Optional[str]
    environment: Optional[str]
    source: Optional[str]
    resourceUrl: Optional[HttpUrl]
    component: Optional[str]
    severity: Optional[str]
    tags: Optional[List[str]]
    correlationId: Optional[str]
    region: Optional[str]
    raw_error: str
    analysis: AnalysisResult
