import pytest
from fastapi.testclient import TestClient
import uuid
from app import app
client = TestClient(app)
def test_create_valid_scheduled_trigger():
    response = client.post(
        "/triggers/",
        json = {
            "name": str(uuid.uuid4()),
            "trigger_type": "scheduled",
            "schedule": "2026-01-25T14:00:00Z",
            "is_recurring": False,
            "payload": "{}"
        })
    assert response.status_code == 200
    assert response.json()["id"] is not None
def test_create_valid_api_trigger():
    response = client.post(
        "/triggers/",
        json = {
            "name": str(uuid.uuid4()),
            "trigger_type": "api",
            "payload": "{\"key\": \"value\"}"
        })
    assert response.status_code == 200
    assert response.json()["id"] is not None
def test_create_invalid_trigger_type():
    response = client.post(
        "/triggers/",
        json = {
            "name": str(uuid.uuid4()),
            "trigger_type": "invalid_type",
            "payload": "{}"
        })
    assert response.status_code == 400
    assert "Trigger type must be either 'scheduled' or 'api'" in response.json()["detail"]
def test_create_recurring_without_interval():
    response = client.post(
        "/triggers/",
        json = {
            "name": str(uuid.uuid4()),
            "trigger_type": "scheduled",
            "is_recurring": True,
            "payload": "{}"
        })
    assert response.status_code == 400
    assert "Recurring triggers must have 'interval_seconds' defined" in response.json()["detail"]
def test_create_api_trigger_with_invalid_payload():
    response = client.post(
        "/triggers/",
        json = {
            "name": str(uuid.uuid4()),
            "trigger_type": "api",
            "payload": "invalid_json"
        })
    assert response.status_code == 400
    assert "Payload must be valid JSON" in response.json()["detail"]
