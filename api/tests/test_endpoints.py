from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.tests.conftest import checkin_payload


def test_openapi_lists_all_resources(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/api/sites", "/api/observers", "/api/checkins", "/api/findings", "/api/photos",
              "/api/risk-scores", "/api/actions", "/api/messages"]:
        assert p in paths


def test_site_crud(client: TestClient, site: dict) -> None:
    assert client.get("/api/sites/C1").json()["name"] == "Exploratório"
    assert client.get("/api/sites", params={"city_id": "CO"}).json()[0]["id"] == "C1"
    assert client.get("/api/sites", params={"city_id": "OS"}).json() == []
    assert client.patch("/api/sites/C1", json={"name": "Renamed"}).json()["name"] == "Renamed"
    assert client.delete("/api/sites/C1").status_code == 204
    assert client.get("/api/sites/C1").status_code == 404


def test_observer_crud(client: TestClient, observer: dict) -> None:
    oid = observer["id"]
    assert oid.startswith("OBS-")
    assert observer["tier"] == "new"
    res = client.patch(f"/api/observers/{oid}", json={"tier": "calibrated", "calibration": {"flow_NP": 0.8}})
    assert res.json()["tier"] == "calibrated"
    assert client.get("/api/observers", params={"tier": "calibrated"}).json()[0]["id"] == oid
    assert client.delete(f"/api/observers/{oid}").status_code == 204


def test_checkin_submit_rounds_coordinates_and_stores_findings(client: TestClient, site: dict, observer: dict) -> None:
    res = client.post("/api/checkins", json=checkin_payload(observer["id"]))
    assert res.status_code == 201
    body = res.json()
    assert body["duplicate"] is False
    assert body["checkin"]["lat"] == 40.198 and body["checkin"]["lon"] == -8.429
    assert len(body["findings"]) == 2
    frog = body["findings"][1]
    assert frog["ai_label"] == "amphibian_frog" and frog["citizen_answer"] == "amphibian_frog"


def test_checkin_is_idempotent_on_client_uuid(client: TestClient, site: dict, observer: dict) -> None:
    first = client.post("/api/checkins", json=checkin_payload(observer["id"])).json()
    second = client.post("/api/checkins", json=checkin_payload(observer["id"])).json()
    assert second["duplicate"] is True
    assert second["checkin"]["id"] == first["checkin"]["id"]
    assert len(client.get("/api/checkins").json()) == 1


def test_checkin_requires_consent(client: TestClient, site: dict, observer: dict) -> None:
    res = client.post("/api/checkins", json=checkin_payload(observer["id"], consent=False))
    assert res.status_code == 422


def test_checkin_unknown_site_404(client: TestClient, observer: dict) -> None:
    res = client.post("/api/checkins", json=checkin_payload(observer["id"], site_id="NOPE"))
    assert res.status_code == 404


def test_checkin_list_filter_update_delete(client: TestClient, site: dict, observer: dict) -> None:
    cid = client.post("/api/checkins", json=checkin_payload(observer["id"])).json()["checkin"]["id"]
    assert len(client.get("/api/checkins", params={"site_id": "C1"}).json()) == 1
    assert client.patch(f"/api/checkins/{cid}", json={"answers": {"flow_NP": "absent"}}).json()["answers"] == {"flow_NP": "absent"}
    client.get(f"/api/findings?checkin_id={cid}")  # findings exist before delete
    for f in client.get("/api/findings", params={"checkin_id": cid}).json():
        client.delete(f"/api/findings/{f['id']}")
    assert client.delete(f"/api/checkins/{cid}").status_code == 204


def test_finding_crud(client: TestClient, site: dict, observer: dict) -> None:
    cid = client.post("/api/checkins", json=checkin_payload(observer["id"])).json()["checkin"]["id"]
    f = client.post("/api/findings", json={"checkin_id": cid, "type": "dead_bird", "subject": "dead_bird", "count": 1}).json()
    assert f["status"] == "manual"
    assert client.patch(f"/api/findings/{f['id']}", json={"status": "expert_review"}).json()["status"] == "expert_review"
    assert len(client.get("/api/findings", params={"type": "dead_bird"}).json()) == 1
    assert client.get("/api/findings/abc").status_code == 404


def _jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (3200, 2000), (10, 120, 90))
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"  # Make
    exif[0x8825] = {2: (40.0, 11.0, 52.0)}  # GPSInfo
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def test_photo_upload_strips_exif_and_downscales(client: TestClient) -> None:
    raw = _jpeg_with_exif()
    assert b"SecretCameraMaker" in raw
    res = client.post("/api/photos", files={"file": ("cup.jpg", raw, "image/jpeg")})
    assert res.status_code == 201
    row = res.json()
    assert max(row["width"], row["height"]) == 1600
    content = client.get(f"/api/photos/{row['id']}/content").content
    assert b"SecretCameraMaker" not in content
    assert not Image.open(io.BytesIO(content)).getexif()
    assert client.get(f"/api/photos/{row['id']}").json()["exif_stripped"] is True
    assert client.delete(f"/api/photos/{row['id']}").status_code == 204


def test_photo_rejects_non_image(client: TestClient) -> None:
    res = client.post("/api/photos", files={"file": ("x.jpg", b"not an image", "image/jpeg")})
    assert res.status_code == 422


def test_risk_score_crud(client: TestClient, site: dict) -> None:
    body = {"site_id": "C1", "week": "2026-W38", "total": 0.42, "band": "moderate", "config_version": "test",
            "explanation": "x", "factors": [{"name": "temperature", "value": 0.5}]}
    r = client.post("/api/risk-scores", json=body).json()
    assert r["factors"][0]["name"] == "temperature"
    assert client.get("/api/risk-scores", params={"week": "2026-W38"}).json()[0]["id"] == r["id"]
    assert client.patch(f"/api/risk-scores/{r['id']}", json={"explanation": "y"}).json()["explanation"] == "y"
    assert client.delete(f"/api/risk-scores/{r['id']}").status_code == 204


def test_action_and_message_crud(client: TestClient, site: dict, observer: dict) -> None:
    a = client.post("/api/actions", json={"site_id": "C1", "driver": "stagnation", "measure_id": "M-4.3.1",
                                          "title": "Verification visit", "rationale": "r"}).json()
    assert a["status"] == "drafted"
    assert client.patch(f"/api/actions/{a['id']}", json={"title": "Edited"}).json()["title"] == "Edited"
    msg = client.post("/api/messages", json={"observer_id": observer["id"], "action_id": a["id"],
                                              "kind": "alert_raised", "text": "Your observation helped raise an alert"}).json()
    assert msg["read"] is False
    assert client.patch(f"/api/messages/{msg['id']}", json={"read": True}).json()["read"] is True
    assert len(client.get("/api/messages", params={"observer_id": observer["id"]}).json()) == 1
    assert client.delete(f"/api/messages/{msg['id']}").status_code == 204
    assert client.delete(f"/api/actions/{a['id']}").status_code == 204


@pytest.mark.parametrize("path", ["/api/sites/X", "/api/observers/X", "/api/checkins/1", "/api/risk-scores/1",
                                  "/api/actions/1", "/api/messages/1", "/api/photos/1"])
def test_missing_items_404(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404


def test_register_observer_is_idempotent(client: TestClient) -> None:
    a = client.put("/api/observers/OBS-AB12CD", json={"team": "t"})
    b = client.put("/api/observers/OBS-AB12CD", json={})
    assert a.status_code == b.status_code == 200
    assert a.json()["id"] == b.json()["id"] == "OBS-AB12CD"


def test_register_observer_rejects_non_pseudonymous_id(client: TestClient) -> None:
    assert client.put("/api/observers/jane.doe@example.org", json={}).status_code == 422
