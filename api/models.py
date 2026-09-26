"""SQLModel tables and API schemas.

Every table carries a ``synthetic`` flag so demo data can never be confused with
real observations. Coordinates are rounded to about 100 m before storage and
observers are pseudonymous codes only.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


COORD_DECIMALS = 3  # 0.001 degree is about 111 m of latitude


def round_coord(value: float) -> float:
    """Round a coordinate to about 100 m."""
    return round(float(value), COORD_DECIMALS)


def new_observer_code() -> str:
    """Random pseudonymous observer code, e.g. OBS-7F3K2Q."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "OBS-" + "".join(secrets.choice(alphabet) for _ in range(6))


class FindingType(str, Enum):
    habitat = "habitat"
    larvae = "larvae"
    adult_mosquito = "adult_mosquito"
    predator = "predator"
    dead_bird = "dead_bird"


class FindingStatus(str, Enum):
    pending = "pending"  # AI suggested, citizen has not answered
    confirmed = "confirmed"  # citizen accepted the suggestion
    corrected = "corrected"  # citizen changed the suggestion
    rejected = "rejected"  # citizen rejected the suggestion
    manual = "manual"  # no AI involved, citizen answered directly
    expert_review = "expert_review"  # flagged, e.g. implausible by GBIF


class ObserverTier(str, Enum):
    new = "new"
    calibrated = "calibrated"
    trusted = "trusted"


class ActionStatus(str, Enum):
    drafted = "drafted"
    approved = "approved"
    dismissed = "dismissed"


# ---------------------------------------------------------------- tables


class Site(SQLModel, table=True):
    id: str = Field(primary_key=True, description="ENORA site code, e.g. C1")
    name: str
    city_id: str = Field(index=True)
    city_name: str
    lat: float
    lon: float
    altitude: Optional[float] = None
    synthetic: bool = False


class Observer(SQLModel, table=True):
    id: str = Field(default_factory=new_observer_code, primary_key=True)
    tier: ObserverTier = ObserverTier.new
    team: Optional[str] = None
    calibration: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    synthetic: bool = False


class CheckIn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_uuid: str = Field(index=True, unique=True, description="Idempotency key from the offline queue")
    site_id: str = Field(foreign_key="site.id", index=True)
    observer_id: str = Field(foreign_key="observer.id", index=True)
    observed_at: datetime
    lat: Optional[float] = None
    lon: Optional[float] = None
    consent: bool
    answers: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    synthetic: bool = False


class Finding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    checkin_id: int = Field(foreign_key="checkin.id", index=True)
    type: FindingType
    subject: str = Field(description="What was assessed, e.g. larval_dip_3, amphibian, dead_bird")
    ai_label: Optional[str] = None
    ai_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    ai_reason: Optional[str] = None
    ai_provider: Optional[str] = None
    key_label: Optional[str] = Field(default=None, description="Result of the guided key, if any")
    citizen_answer: Optional[str] = None
    count: Optional[int] = Field(default=None, ge=0)
    status: FindingStatus = FindingStatus.manual
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    synthetic: bool = False


class Photo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    finding_id: Optional[int] = Field(default=None, foreign_key="finding.id", index=True)
    content_type: str = "image/jpeg"
    width: int
    height: int
    sha256: str
    exif_stripped: bool = True
    path: str
    synthetic: bool = False


class RiskScore(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: str = Field(foreign_key="site.id", index=True)
    week: str = Field(index=True, description="ISO week, e.g. 2026-W38")
    total: float
    band: str
    factors: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    explanation: str
    config_version: str
    dominant: Optional[str] = None
    coverage: float = 1.0
    range_low: float = 0.0
    range_high: float = 1.0
    needs_data: bool = False
    alert: bool = False
    as_of: Optional[str] = None
    checkin_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    computed_at: datetime = Field(default_factory=utcnow)
    synthetic: bool = False


class Action(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: str = Field(foreign_key="site.id", index=True)
    risk_score_id: Optional[int] = Field(default=None, foreign_key="riskscore.id")
    driver: str = Field(description="Dominant risk factor that triggered the draft")
    measure_id: str
    title: str
    rationale: str
    status: ActionStatus = ActionStatus.drafted
    approved_by: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    contributors: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    synthetic: bool = False


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    observer_id: str = Field(foreign_key="observer.id", index=True)
    action_id: Optional[int] = Field(default=None, foreign_key="action.id")
    kind: str = Field(description="alert_raised or action_taken")
    text: str
    read: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    synthetic: bool = False


# ---------------------------------------------------------------- schemas


class SiteCreate(SQLModel):
    id: str
    name: str
    city_id: str
    city_name: str
    lat: float
    lon: float
    altitude: Optional[float] = None
    synthetic: bool = False


class SiteUpdate(SQLModel):
    name: Optional[str] = None
    altitude: Optional[float] = None


OBSERVER_CODE_PATTERN = r"^OBS-[A-Z0-9]{6}$"


class ObserverCreate(SQLModel):
    id: Optional[str] = Field(default=None, regex=OBSERVER_CODE_PATTERN, description="Client-generated pseudonymous code")
    team: Optional[str] = None
    synthetic: bool = False


class ObserverUpdate(SQLModel):
    tier: Optional[ObserverTier] = None
    team: Optional[str] = None
    calibration: Optional[dict[str, Any]] = None


class FindingIn(SQLModel):
    """A finding submitted as part of a check-in."""

    type: FindingType
    subject: str
    ai_label: Optional[str] = None
    ai_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    ai_reason: Optional[str] = None
    ai_provider: Optional[str] = None
    key_label: Optional[str] = None
    citizen_answer: Optional[str] = None
    count: Optional[int] = Field(default=None, ge=0)
    status: FindingStatus = FindingStatus.manual
    data: dict[str, Any] = Field(default_factory=dict)
    synthetic: bool = False


class CheckInCreate(SQLModel):
    client_uuid: str
    site_id: str
    observer_id: str
    observed_at: datetime
    lat: Optional[float] = None
    lon: Optional[float] = None
    consent: bool
    answers: dict[str, Any] = Field(default_factory=dict)
    findings: list[FindingIn] = Field(default_factory=list)
    synthetic: bool = False


class CheckInUpdate(SQLModel):
    answers: Optional[dict[str, Any]] = None
    consent: Optional[bool] = None


class FindingCreate(FindingIn):
    checkin_id: int


class FindingUpdate(SQLModel):
    citizen_answer: Optional[str] = None
    status: Optional[FindingStatus] = None
    count: Optional[int] = Field(default=None, ge=0)


class RiskScoreCreate(SQLModel):
    site_id: str
    week: str
    total: float
    band: str
    factors: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str
    config_version: str
    synthetic: bool = False


class RiskScoreUpdate(SQLModel):
    explanation: Optional[str] = None


class ActionCreate(SQLModel):
    site_id: str
    risk_score_id: Optional[int] = None
    driver: str
    measure_id: str
    title: str
    rationale: str
    contributors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    synthetic: bool = False


class ActionUpdate(SQLModel):
    title: Optional[str] = None
    rationale: Optional[str] = None
    measure_id: Optional[str] = None


class MessageCreate(SQLModel):
    observer_id: str
    action_id: Optional[int] = None
    kind: str
    text: str
    synthetic: bool = False


class MessageUpdate(SQLModel):
    read: Optional[bool] = None
