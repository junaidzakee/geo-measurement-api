import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import files as files_module
from app.database import Base, get_db
from app.main import app
from app.services import file_handler


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # temporary upload folder
    monkeypatch.setattr(file_handler, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(files_module, "UPLOAD_DIR", tmp_path / "uploads")

    # temporary database
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()