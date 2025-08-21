# Application Failure Triage Agent (Sample)

Generic first-line support API for failures from Azure Data Factory, Synapse, Fabric, Databricks/Spark, Kubernetes, and any app. It accepts failure events, summarizes the error (Azure OpenAI or safe fallback), and optionally notifies Teams/email.

## Features
* Single POST endpoint `/api/v1/notify` protected by an API key header.
* Accepts a generic failure payload: pipelineName, runId, activityName, errorMessage, errorCode, timestamp, environment; plus optional metadata: source, resourceUrl, component, severity, tags, correlationId, region.
* Calls Azure OpenAI with a tuned prompt to produce: simplified_error, probable_reason, probable_fix, confidence. Gracefully falls back if AI is unavailable.
* Sends Teams card (adaptive-like simple JSON) via incoming webhook.
* Optionally sends email via Microsoft Graph (client credentials) if configured.
* No persistence; completely stateless.
* CORS enabled for browser/Swagger usage.
* Diagnostics endpoint `/diagnostics/openai`.
* Optional CSV logging of analyses for auditing (disabled by default).

## Quick Start

### 1. Clone & configure
Copy `.env.example` to `.env` and fill values.

### 2. Install dependencies
Use Python 3.10+.

#### Install required packages
Run the following command to install all required packages:
```
pip install fastapi uvicorn python-dotenv httpx
```

Or, to install all dependencies including tests:
```
pip install .[test]
```
Or with uv / poetry adapt accordingly.

### 3. Run locally
```
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for interactive Swagger UI.

To enable CSV logging, add to your `.env`:
```
ENABLE_CSV_LOGGING=true
# Optional custom path; defaults to ./analysis_log.csv
CSV_LOG_PATH=C:\\temp\\analysis_log.csv
```

### 4. Sample request
```
POST http://localhost:8000/api/v1/notify
Headers: x-api-key: <your key>
Body (JSON):
{
  "pipelineName": "Ingest_Customer",
  "runId": "1234-5678",
  "activityName": "CopyFromBlob",
  "errorMessage": "ErrorCode=SqlOperationFailed,'Type=Microsoft.DataTransfer.Common.Shared.HybridDeliveryException,..." ,
  "errorCode": "SqlOperationFailed",
  "timestamp": "2025-08-13T12:30:00Z",
  "environment": "prod",
  "source": "adf",
  "resourceUrl": "https://adf.microsoft.com/.../runs/1234-5678",
  "component": "ingestion",
  "severity": "error",
  "tags": ["team-data", "app-claims"],
  "correlationId": "trace-abc",
  "region": "eastus"
}
```

Optional while testing: add `?return_only=true` to skip notifications and return only the analysis.

### 5. ADF / Synapse / Fabric / Databricks Integration
Use a Web / REST activity in a pipeline failure path calling this endpoint with the required JSON and API key header.

### 6. Deploy (Azure App Service example)
Containerize or push code. Provide environment variables in App Service configuration settings.

## Security
* Simple shared secret via `x-api-key` header. Rotate regularly; consider Azure API Management or OAuth2 for production.
* Error text is lightly redacted (password/secret/key/pwd patterns) before AI/notifications.
* Keep `.env` out of source control; rotate secrets if exposed.

## Prompt Strategy
We provide the LLM a structured system + user message pair guiding it to produce JSON fields. The backend parses & validates before forwarding notifications.

## Testing
Run unit tests:
```
pytest
```

### Diagnostics
* `/healthz` basic check
* `/diagnostics/openai` returns connectivity/config status to your Azure OpenAI endpoint

## Future Enhancements
* Retry logic / backoff for Teams & Graph
* Support Adaptive Cards rich layouts
* Multi-channel routing rules
* Caching repeated error analyses

MIT License.
