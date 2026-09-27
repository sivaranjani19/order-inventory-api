import pytest
from sqlmodel import Session, SQLModel, create_engine
from fastapi.testclient import TestClient
from app.main import app, get_session
import sqlite3

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"

@pytest.fixture
def client(db_path):
    test_db_url = f"sqlite:///{db_path}"
    test_engine = create_engine(
      test_db_url,
      connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(test_engine)
    def get_session_override():
            with Session(test_engine) as session:
                yield session

    app.dependency_overrides[get_session] = get_session_override

    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()

@pytest.fixture
def db_cursor(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    yield cursor
    conn.close()