import re

import pytest
from pydantic import ValidationError

from api import models as m


def test_round_coord_is_about_100_m() -> None:
    assert m.round_coord(40.197871234) == 40.198
    assert m.round_coord(-8.428651234) == -8.429


def test_observer_code_is_pseudonymous() -> None:
    code = m.new_observer_code()
    assert re.fullmatch(r"OBS-[A-Z2-9]{6}", code)
    assert m.new_observer_code() != code


def test_observer_has_no_personal_fields() -> None:
    fields = set(m.Observer.model_fields)
    assert not fields & {"name", "email", "phone", "telecom", "address"}


@pytest.mark.parametrize("table", [m.Site, m.Observer, m.CheckIn, m.Finding, m.Photo, m.RiskScore, m.Action, m.Message])
def test_every_table_has_synthetic_flag(table) -> None:  # type: ignore[no-untyped-def]
    assert "synthetic" in table.model_fields


def test_finding_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        m.FindingIn(type="larvae", subject="dip_1", ai_confidence=1.5)


def test_finding_type_is_closed_list() -> None:
    with pytest.raises(ValidationError):
        m.FindingIn(type="dragon", subject="x")


def test_negative_count_rejected() -> None:
    with pytest.raises(ValidationError):
        m.FindingIn(type="larvae", subject="dip_1", count=-1)
