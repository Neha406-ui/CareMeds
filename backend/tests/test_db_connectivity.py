import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_db_connectivity_unconfigured(monkeypatch):
    # Ensure DATABASE_URL is not set
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Reload config by re-importing modules is tricky; just call endpoint
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    # When unconfigured, status should be unconfigured
    assert data["status"] == "unconfigured"
    assert "message" in data
