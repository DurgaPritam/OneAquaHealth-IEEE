"""Pure pieces of the pre-registered backtest. No network."""

from datetime import date, datetime

import math

import pandas as pd

from analysis.backtest import (
    evaluation_sundays,
    lead_weeks,
    norm_name,
    parse_case_date,
    signal_date,
    weekly_suitability,
    wilson,
)
from api.risk.config import load_config


def test_parse_case_date_handles_excel_serials_timestamps_strings_and_blanks() -> None:
    assert parse_case_date(43318) == date(2018, 8, 6)  # 2018 file stores Excel serial numbers
    assert parse_case_date(43318.0) == date(2018, 8, 6)
    assert parse_case_date(pd.Timestamp("2019-07-29")) == date(2019, 7, 29)
    assert parse_case_date(datetime(2023, 7, 16, 0, 0)) == date(2023, 7, 16)
    assert parse_case_date("2021-09-16") == date(2021, 9, 16)
    for blank in (None, float("nan"), pd.NaT, "", "nan"):
        assert parse_case_date(blank) is None


def test_norm_name_matches_across_files() -> None:
    assert norm_name("Bouches-du-Rhône") == norm_name("Bouches-du-Rhone")
    assert norm_name("Reggio nell’Emilia") == norm_name("Reggio nell'Emilia")


def test_evaluation_sundays_span_april_to_november() -> None:
    days = evaluation_sundays(2023)
    assert days[0] == date(2023, 4, 2) and days[-1] == date(2023, 11, 26)
    assert all(d.weekday() == 6 for d in days)
    assert all((b - a).days == 7 for a, b in zip(days, days[1:]))


def _weeks(values: list[float | None]) -> list[tuple[date, float | None]]:
    return list(zip(evaluation_sundays(2023), values))


def test_signal_needs_two_consecutive_weeks_and_is_the_second_sunday() -> None:
    weeks = _weeks([0.2, 0.6, 0.4, 0.55, 0.5, 0.9])
    c = signal_date(weeks, 0.5)
    assert c.crossing == date(2023, 4, 23) and c.signal == date(2023, 4, 30)
    assert not c.left_censored


def test_missing_value_breaks_the_run_and_no_crossing_is_a_miss() -> None:
    assert signal_date(_weeks([0.6, None, 0.6, 0.4]), 0.5).signal is None
    assert signal_date(_weeks([0.1, 0.2, 0.3]), 0.5).signal is None


def test_left_censored_when_first_two_weeks_are_above() -> None:
    assert signal_date(_weeks([0.7, 0.7, 0.1]), 0.5).left_censored


def test_lead_weeks_sign_and_rounding() -> None:
    assert lead_weeks(date(2023, 7, 16), date(2023, 6, 4)) == 6.0
    assert lead_weeks(date(2023, 6, 1), date(2023, 6, 4)) == -0.4
    assert lead_weeks(date(2023, 6, 1), None) is None


def test_wilson_interval() -> None:
    lo, hi = wilson(8, 10)
    assert math.isclose(lo, 0.4902, abs_tol=1e-3) and math.isclose(hi, 0.9433, abs_tol=1e-3)
    assert wilson(0, 10)[0] == 0.0 and wilson(10, 10)[1] == 1.0
    assert all(math.isnan(x) for x in wilson(0, 0))


def test_weekly_suitability_uses_production_index() -> None:
    cfg = load_config()
    sundays = evaluation_sundays(2023)[:2]
    daily = [{"date": (sundays[0].fromordinal(sundays[0].toordinal() - 20 + i)).isoformat(), "tmean": 24.0, "precip": 0.0} for i in range(30)]
    weeks = weekly_suitability(daily, sundays, cfg)
    # 14 days x 9.7 degree-days = 135.8 > 109, so temperature 1; 14 dry days, so dry spell 1
    assert weeks[0][1] == 1.0
    assert weekly_suitability([], sundays, cfg)[0][1] is None
