import os

import pytest
from sqlalchemy import create_engine, inspect, text

os.environ.setdefault("ENVIRONMENT", "test")
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# create_all does not alter an existing test database.
_inspector = inspect(engine)
if "post_images" in _inspector.get_table_names():
    _columns = {column["name"] for column in _inspector.get_columns("post_images")}
    with engine.begin() as _conn:
        if "place_name" not in _columns:
            _conn.execute(text("ALTER TABLE post_images ADD COLUMN place_name VARCHAR(200)"))
        if "position" not in _columns:
            _conn.execute(text("ALTER TABLE post_images ADD COLUMN position INTEGER NOT NULL DEFAULT 0"))


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
