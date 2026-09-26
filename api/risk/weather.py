"""Daily mean temperature and precipitation from Open-Meteo, cached on disk.

Recent days come from the forecast API (past_days); older ranges from the
historical archive. Both need no key. Data: Open-Meteo.com, CC BY 4.0.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

FORECAST = "https://api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
CACHE_DIR = Path(os.environ.get("WEATHER_CACHE", "var/weather"))
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"

Fetch = Callable[[str, dict[str, Any]], dict[str, Any]]


def _http(url: str, params: dict[str, Any]) -> dict[str, Any]:
    res = httpx.get(url, params=params, timeout=20)
    res.raise_for_status()
    return res.json()


def daily(lat: float, lon: float, start: date, end: date, today: date | None = None, fetch: Fetch = _http,
          cache_dir: Path | None = None) -> list[dict[str, Any]]:
    """Daily rows {date, tmean, precip} for [start, end]. Cells are rounded to 0.1 degree to share cache entries."""
    cache_dir = cache_dir or CACHE_DIR
    lat_r, lon_r = round(lat, 1), round(lon, 1)
    key = cache_dir / f"{lat_r}_{lon_r}_{start}_{end}.json"
    if key.exists():
        return json.loads(key.read_text())
    today = today or date.today()
    params = {"latitude": lat_r, "longitude": lon_r, "daily": "temperature_2m_mean,precipitation_sum", "timezone": "UTC"}
    if (today - start).days <= 90:
        params |= {"start_date": start.isoformat(), "end_date": end.isoformat()}
        data = fetch(FORECAST, params)
    else:
        params |= {"start_date": start.isoformat(), "end_date": end.isoformat()}
        data = fetch(ARCHIVE, params)
    d = data["daily"]
    rows = [{"date": t, "tmean": tm, "precip": p} for t, tm, p in zip(d["time"], d["temperature_2m_mean"], d["precipitation_sum"])]
    if end < today:  # do not cache ranges that may still change
        cache_dir.mkdir(parents=True, exist_ok=True)
        key.write_text(json.dumps(rows))
    return rows


def window(lat: float, lon: float, as_of: date, days: int, fetch: Fetch = _http, cache_dir: Path | None = None) -> list[dict[str, Any]]:
    return daily(lat, lon, as_of - timedelta(days=days - 1), as_of, fetch=fetch, cache_dir=cache_dir)
