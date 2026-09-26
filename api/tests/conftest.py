from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api import models  # noqa: F401
from api.db import get_session
from api.main import app


@pytest.fixture()
def engine():  # type: ignore[no-untyped-def]
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    with Session(engine) as s:
        yield s


@pytest.fixture()
def client(engine, tmp_path, monkeypatch) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    from api import photos

    monkeypatch.setattr(photos, "PHOTO_DIR", tmp_path)
    monkeypatch.setenv("RISK_ON_SUBMIT", "0")  # no network in tests

    def override() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


SITE = {"id": "C1", "name": "Exploratório", "city_id": "CO", "city_name": "Coimbra", "lat": 40.19787, "lon": -8.42865}


@pytest.fixture()
def site(client: TestClient) -> dict:
    return client.post("/api/sites", json=SITE).json()


@pytest.fixture()
def observer(client: TestClient) -> dict:
    return client.post("/api/observers", json={"team": "Test team"}).json()


def checkin_payload(observer_id: str, **over) -> dict:
    body = {
        "client_uuid": "11111111-1111-1111-1111-111111111111",
        "site_id": "C1",
        "observer_id": observer_id,
        "observed_at": "2026-09-20T09:00:00Z",
        "lat": 40.197871234,
        "lon": -8.428651234,
        "consent": True,
        "answers": {"flow_NP": "present"},
        "findings": [
            {"type": "larvae", "subject": "dip_1", "count": 4},
            {"type": "predator", "subject": "amphibians", "ai_label": "amphibian_frog", "ai_confidence": 0.7,
             "ai_reason": "Green frog visible on the bank", "citizen_answer": "amphibian_frog", "status": "confirmed"},
        ],
    }
    body.update(over)
    return body
