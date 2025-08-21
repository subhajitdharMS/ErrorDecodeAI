from __future__ import annotations
import os
from functools import lru_cache
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class Settings(BaseModel):
    api_key: str = Field(default="", alias="API_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")

    teams_webhook_url: Optional[str] = Field(default=None, alias="TEAMS_WEBHOOK_URL")

    alert_emails: List[str] = Field(default_factory=list, alias="ALERT_EMAILS")
    sender_email: Optional[str] = Field(default=None, alias="SENDER_EMAIL")

    tenant_id: Optional[str] = Field(default=None, alias="AZURE_TENANT_ID")
    client_id: Optional[str] = Field(default=None, alias="AZURE_CLIENT_ID")
    client_secret: Optional[str] = Field(default=None, alias="AZURE_CLIENT_SECRET")
    disable_notifications: bool = Field(default=False, alias="DISABLE_NOTIFICATIONS")
    enable_csv_logging: bool = Field(default=False, alias="ENABLE_CSV_LOGGING")
    csv_log_path: Optional[str] = Field(default=None, alias="CSV_LOG_PATH")

    class Config:
        populate_by_name = True

    @field_validator("alert_emails", mode="before")
    @classmethod
    def split_emails(cls, v):
        if isinstance(v, str):
            # Allow comma or semicolon separated
            parts = [p.strip() for p in v.replace(";", ",").split(",") if p.strip()]
            return parts
        return v

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Load from environment variables (dotenv can be loaded in main)
    data = {k: v for k, v in os.environ.items()}
    return Settings(**data)
