"""
Integration test: Ingest API → clone → parse → chunk pipeline (no real DB).

Uses httpx test client and mocks heavy dependencies.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """Replace the DB session with a mock so we don't need Postgres."""
    mock_session = MagicMock()
    monkeypatch.setattr("app.api.routes.ingest.get_db", lambda: iter([mock_session]))
    return mock_session


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_returns_repo_id():
    with patch("app.api.routes.ingest.IngestionService") as MockService:
        mock_instance = MockService.return_value
        mock_repo = MagicMock()
        mock_repo.id = "test-repo-id"
        mock_repo.status = "pending"
        mock_instance.create_repo_record.return_value = mock_repo

        response = client.post(
            "/api/ingest",
            json={"github_url": "https://github.com/example/myproject"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "repo_id" in data
