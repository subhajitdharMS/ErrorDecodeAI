import os
import pytest
from httpx import AsyncClient
from dotenv import load_dotenv
from app.main import app

load_dotenv(override=True)

@pytest.mark.asyncio
async def test_notify_basic(monkeypatch):
    os.environ['API_KEY'] = 'test-key'

    async def fake_analyze(data):
        from app.models.schemas import AnalysisResult
        return AnalysisResult(simplified_error='simple', probable_reason='reason', probable_fix='fix')

    # Patch analyzer
    from app.services import ai_analyzer
    monkeypatch.setattr(ai_analyzer, 'analyze_failure', fake_analyze)

    async def fake_dispatch(payload):
        return None
    from app.services import notifier
    monkeypatch.setattr(notifier, 'dispatch_notifications', fake_dispatch)

    async with AsyncClient(app=app, base_url='http://test') as client:
        r = await client.post('/api/v1/notify', headers={'x-api-key': 'test-key'}, json={
            'pipelineName': 'Pipe', 'errorMessage': 'Something bad'
        })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['status'] == 'sent'
    # Monkeypatched analyzer returns fixed value 'simple'
    assert data['analysis']['simplified_error'] == 'simple'

@pytest.mark.asyncio
async def test_notify_return_only(monkeypatch):
    os.environ['API_KEY'] = 'test-key'
    os.environ['DISABLE_NOTIFICATIONS'] = 'False'

    async def fake_analyze(data):
        from app.models.schemas import AnalysisResult
        return AnalysisResult(simplified_error='only', probable_reason='r', probable_fix='f')

    from app.services import ai_analyzer
    monkeypatch.setattr(ai_analyzer, 'analyze_failure', fake_analyze)

    # Ensure dispatch would raise if called (to validate it's skipped)
    from app.services import notifier
    async def fail_dispatch(payload):  # pragma: no cover
        raise AssertionError('dispatch should not be called')
    monkeypatch.setattr(notifier, 'dispatch_notifications', fail_dispatch)

    async with AsyncClient(app=app, base_url='http://test') as client:
        r = await client.post('/api/v1/notify?return_only=true', headers={'x-api-key': 'test-key'}, json={
            'pipelineName': 'Pipe', 'errorMessage': 'Err'
        })
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'analysis_only'
    assert body['analysis']['simplified_error'] == 'only'
