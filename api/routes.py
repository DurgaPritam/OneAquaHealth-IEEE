"""HTTP routes. Simple resources use the CRUD factory; check-ins and photos need custom logic."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from api import models as m
from api import photos
from api.crud import crud_router, get_or_404
from api.db import get_session

sites = crud_router(m.Site, m.SiteCreate, m.SiteUpdate, "/api/sites", "sites", ("city_id", "synthetic"))
observers = crud_router(m.Observer, m.ObserverCreate, m.ObserverUpdate, "/api/observers", "observers", ("tier", "team"))
findings = crud_router(m.Finding, m.FindingCreate, m.FindingUpdate, "/api/findings", "findings", ("checkin_id", "type", "status"))
risk_scores = crud_router(m.RiskScore, m.RiskScoreCreate, m.RiskScoreUpdate, "/api/risk-scores", "risk", ("site_id", "week"))
actions = crud_router(m.Action, m.ActionCreate, m.ActionUpdate, "/api/actions", "actions", ("site_id", "status"))
messages = crud_router(m.Message, m.MessageCreate, m.MessageUpdate, "/api/messages", "messages", ("observer_id", "read"))
checkins = crud_router(m.CheckIn, None, m.CheckInUpdate, "/api/checkins", "checkins", ("site_id", "observer_id", "synthetic"))


class CheckInResult(BaseModel):
    checkin: m.CheckIn
    findings: list[m.Finding]
    duplicate: bool


sync = APIRouter(tags=["checkins"])


@sync.post("/api/checkins", response_model=CheckInResult, status_code=201)
def submit_checkin(payload: m.CheckInCreate, session: Session = Depends(get_session)) -> CheckInResult:
    """Store a check-in and its findings.

    Idempotent on ``client_uuid``: the offline queue may send the same
    check-in twice, and the second call returns the stored record.
    """
    if not payload.consent:
        raise HTTPException(422, "Consent is required to store a check-in")
    get_or_404(session, m.Site, payload.site_id)
    get_or_404(session, m.Observer, payload.observer_id)

    existing = session.exec(select(m.CheckIn).where(m.CheckIn.client_uuid == payload.client_uuid)).first()
    if existing is not None:
        stored = session.exec(select(m.Finding).where(m.Finding.checkin_id == existing.id)).all()
        return CheckInResult(checkin=existing, findings=list(stored), duplicate=True)

    checkin = m.CheckIn.model_validate(payload.model_dump(exclude={"findings"}))
    if checkin.lat is not None and checkin.lon is not None:
        checkin.lat, checkin.lon = m.round_coord(checkin.lat), m.round_coord(checkin.lon)
    session.add(checkin)
    session.flush()
    rows = [m.Finding.model_validate({**f.model_dump(), "checkin_id": checkin.id}) for f in payload.findings]
    session.add_all(rows)
    session.commit()
    session.refresh(checkin)
    for row in rows:
        session.refresh(row)
    return CheckInResult(checkin=checkin, findings=rows, duplicate=False)


@sync.put("/api/observers/{observer_id}", response_model=m.Observer)
def register_observer(observer_id: str, payload: m.ObserverCreate, session: Session = Depends(get_session)) -> m.Observer:
    """Idempotent registration of a client-generated pseudonymous code (offline first)."""
    if not re.fullmatch(m.OBSERVER_CODE_PATTERN, observer_id):
        raise HTTPException(422, "Observer id must be a pseudonymous code like OBS-7F3K2Q")
    body = m.ObserverCreate.model_validate({**payload.model_dump(), "id": observer_id})
    existing = session.get(m.Observer, observer_id)
    if existing is not None:
        return existing
    row = m.Observer.model_validate(body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


media = APIRouter(prefix="/api/photos", tags=["photos"])


@media.post("", response_model=m.Photo, status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    finding_id: int | None = None,
    session: Session = Depends(get_session),
) -> m.Photo:
    """Upload a photo. EXIF is stripped and the image downscaled before storage."""
    if finding_id is not None:
        get_or_404(session, m.Finding, finding_id)
    try:
        clean = photos.sanitise(await file.read())
    except Exception as exc:  # Pillow raises several types for bad input
        raise HTTPException(422, "Not a readable image") from exc
    path = photos.store(clean)
    row = m.Photo(finding_id=finding_id, width=clean.width, height=clean.height, sha256=clean.sha256, path=str(path))
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@media.get("/{photo_id}", response_model=m.Photo)
def get_photo(photo_id: int, session: Session = Depends(get_session)) -> m.Photo:
    return get_or_404(session, m.Photo, photo_id)


@media.get("/{photo_id}/content")
def get_photo_content(photo_id: int, session: Session = Depends(get_session)) -> FileResponse:
    row = get_or_404(session, m.Photo, photo_id)
    return FileResponse(row.path, media_type=row.content_type)


@media.delete("/{photo_id}", status_code=204)
def delete_photo(photo_id: int, session: Session = Depends(get_session)) -> None:
    row = get_or_404(session, m.Photo, photo_id)
    session.delete(row)
    session.commit()


ai = APIRouter(prefix="/api/ai", tags=["ai"])


@ai.get("/status")
def ai_status() -> dict:
    """Which provider is active. The UI shows a "demo AI (mock)" badge when mock is true."""
    from api.ai import service

    return service.status()


@ai.post("/suggest")
async def ai_suggest(
    finding_type: str,
    file: UploadFile = File(...),
    site_id: str | None = None,
    key_result: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    """Suggest a label for a photo. The citizen must accept, change or reject it."""
    from api.ai import service

    lat = lon = None
    if site_id:
        site = get_or_404(session, m.Site, site_id)
        lat, lon = site.lat, site.lon
    try:
        clean = photos.sanitise(await file.read(), max_edge=1024)
    except Exception as exc:
        raise HTTPException(422, "Not a readable image") from exc
    try:
        return service.suggest(clean.data, finding_type, lat, lon, key_result)
    except service.NeverAnalysed as exc:
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


ALL_ROUTERS = [ai, sync, sites, observers, checkins, findings, media, risk_scores, actions, messages]
