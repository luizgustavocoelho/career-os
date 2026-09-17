import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.main import app


@pytest.fixture
def database(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)  # Isolated test schema; app startup only uses migrations.
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(settings(), "registration_limit", 0)
    monkeypatch.setattr(settings(), "openai_api_key", "")
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(database):
    with TestClient(app) as c:
        yield c


def account(client, email="candidate@example.com"):
    r = client.post(
        "/api/auth/register",
        json={"name": "Candidato de teste", "email": email, "password": "testing-password-123!"},
    )
    assert r.status_code == 201, r.text
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return r.json()


@pytest.fixture
def user(client):
    return account(client)


@pytest.fixture
def vacancy():
    return {
        "title": "Engenheiro de Dados",
        "company": "Empresa de Teste",
        "location": "São Paulo",
        "description": "Construir pipelines de dados com Python e SQL. AWS é um diferencial.",
        "work_model": "remote",
        "seniority": "junior",
        "requirements": [
            {"skill": "Python", "mandatory": True, "description": "Pipelines Python"},
            {"skill": "SQL", "mandatory": True, "description": "Consultas SQL"},
            {"skill": "AWS", "mandatory": False, "description": "Diferencial"},
        ],
    }


def pdf_fixture():
    from io import BytesIO

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 50 780 Td (Test Candidate) Tj 0 -20 Td (Python SQL - candidate@example.com) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
