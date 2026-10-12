from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_residents_requires_auth():
    resp = client.get('/api/residents')
    assert resp.status_code == 401
