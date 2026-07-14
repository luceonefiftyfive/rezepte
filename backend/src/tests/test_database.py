from app.core.database import get_db
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


def test_get_db_uses_app_state_when_available():
    app = FastAPI()
    expected_db = object()
    app.state.db = expected_db

    @app.get("/test-db")
    def endpoint(db=Depends(get_db)):
        return db is expected_db

    with TestClient(app) as client:
        response = client.get("/test-db")

    assert response.json() is True
