from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

#Test: add health check
def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
