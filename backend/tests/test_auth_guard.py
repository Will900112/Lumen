"""Every user-facing endpoint must reject unauthenticated requests."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

PROTECTED_ENDPOINTS = [
    ("POST", "/recommend", {"questionnaire": {}}),
    ("POST", "/chat", {"session_id": "x", "message": "hi"}),
    ("GET", "/sessions", None),
    ("GET", "/sessions/some-id", None),
    ("POST", "/list/add", {"session_id": "x", "name": "Vitamin D3"}),
    ("GET", "/list", None),
    ("DELETE", "/list/some-id", None),
]


@pytest.mark.parametrize("method,path,body", PROTECTED_ENDPOINTS)
def test_endpoint_requires_auth(method, path, body):
    response = client.request(method, path, json=body)
    assert response.status_code == 401


def test_invalid_token_is_rejected():
    response = client.get(
        "/sessions", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
