from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from app.api.routes import router as notify_router
from app.core.config import get_settings
import httpx
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(override=True)

app = FastAPI(title="ADF Monitor Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(notify_router)

@app.get("/healthz")
async def health():
    s = get_settings()
    return {"status": "ok", "openai_configured": bool(s.azure_openai_api_key and s.azure_openai_endpoint)}

@app.get("/diagnostics/openai")
async def diag_openai():
    s = get_settings()
    if not (s.azure_openai_api_key and s.azure_openai_endpoint and s.azure_openai_deployment):
        return {"configured": False, "reason": "Missing one of endpoint/deployment/api key"}
    url = f"{s.azure_openai_endpoint.rstrip('/')}/openai/deployments/{s.azure_openai_deployment}/chat/completions?api-version={s.azure_openai_api_version}"
    headers = {"api-key": s.azure_openai_api_key, "Content-Type": "application/json"}
    body = {"messages": [{"role": "user", "content": "Ping"}], "max_tokens": 1}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post(url, headers=headers, json=body)
        return {"configured": True, "status_code": r.status_code, "ok": r.status_code < 400, "body_start": r.text[:180]}
    except httpx.RequestError as ex:
        return {"configured": True, "network_error": str(ex.__class__.__name__), "detail": str(ex)}

@app.post("/diagnostics/reload-settings")
async def reload_settings():
    # Reload .env and clear cached settings so new env vars are applied
    load_dotenv(override=True)
    from app.core import config as cfg
    cfg.get_settings.cache_clear()  # type: ignore[attr-defined]
    s = cfg.get_settings()
    # Return a safe subset for quick verification
    return {
        "reloaded": True,
        "enable_csv_logging": getattr(s, "enable_csv_logging", False),
        "csv_log_path": getattr(s, "csv_log_path", None),
        "disable_notifications": getattr(s, "disable_notifications", False),
    }

@app.exception_handler(Exception)
async def unhandled(exc: Exception, request):  # type: ignore
    return JSONResponse(status_code=500, content={"detail": str(exc)})
