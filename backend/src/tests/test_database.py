from app.core.database import get_db
from litestar import Litestar, get
from litestar.di import NamedDependency, Provide
from litestar.testing import TestClient


def test_get_db_uses_app_state_when_available():
    expected_db = object()

    @get("/test-db", sync_to_thread=False)
    def endpoint(db: NamedDependency[object]) -> bool:
        return db is expected_db

    app = Litestar(
        route_handlers=[endpoint],
        dependencies={"db": Provide(get_db, sync_to_thread=False)},
    )
    app.state.db = expected_db

    with TestClient(app=app) as client:
        response = client.get("/test-db")

    assert response.json() is True
