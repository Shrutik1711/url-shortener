from datetime import datetime

import pytest

from app import create_app
from app.utils import is_valid_alias, is_valid_url


@pytest.fixture
def now(monkeypatch):
    """Fake clock: change now['t'] to 'travel' in time."""
    state = {"t": datetime(2026, 10, 26, 9, 0, 0)}
    monkeypatch.setattr("app.routes.utcnow", lambda: state["t"])
    return state


@pytest.fixture
def client(tmp_path, now):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
    })
    return app.test_client()


def make(client, url="https://example.com/page", **extra):
    return client.post("/links", json={"original_url": url, **extra})


def test_create_and_redirect(client):
    resp = make(client, "https://example.com/a?b=1")
    assert resp.status_code == 201
    code = resp.get_json()["short_code"]

    redirect = client.get(f"/{code}")
    assert redirect.status_code == 307
    assert redirect.headers["Location"] == "https://example.com/a?b=1"


def test_custom_alias_and_duplicate_alias(client):
    first = make(client, "https://first.example.com", custom_alias="promo")
    assert first.status_code == 201
    assert first.get_json()["short_code"] == "promo"

    second = make(client, "https://second.example.com", custom_alias="promo")
    assert second.status_code == 409
    assert "already in use" in second.get_json()["error"]
    
    assert client.get("/promo").headers["Location"] == "https://first.example.com"


@pytest.mark.parametrize("url", ["", "example.com", "ftp://x.com/f", "javascript:alert(1)", "http://", "a b"])
def test_invalid_url_rejected(client, url):
    assert make(client, url).status_code == 400


@pytest.mark.parametrize("alias", ["ab", "has space", "a/b", "links", "x" * 33, ""])
def test_invalid_alias_rejected(client, alias):
    assert make(client, custom_alias=alias).status_code == 400


def test_body_must_be_json_object(client):
    resp = client.post("/links", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_unknown_code_is_404(client):
    resp = client.get("/nothere")
    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"]


def test_expired_link_is_410_and_boundary(client, now):
    code = make(client, expires_at="2026-10-26T10:00:00Z").get_json()["short_code"]

    now["t"] = datetime(2026, 10, 26, 9, 59, 59)
    assert client.get(f"/{code}").status_code == 307

    now["t"] = datetime(2026, 10, 26, 10, 0, 0)  
    resp = client.get(f"/{code}")
    assert resp.status_code == 410
    assert "expired" in resp.get_json()["error"]


def test_expiry_timezone_is_converted_to_utc(client):
    resp = make(client, expires_at="2026-12-01T12:00:00+05:30")
    assert resp.get_json()["expires_at"] == "2026-12-01T06:30:00Z"


def test_expiry_in_past_or_bad_format_rejected(client):
    assert make(client, expires_at="2020-01-01T00:00:00Z").status_code == 400
    assert make(client, expires_at="tomorrow").status_code == 400


def test_stats_count_clicks_and_last_clicked(client, now):
    code = make(client).get_json()["short_code"]

    stats = client.get(f"/links/{code}/stats").get_json()
    assert stats["total_clicks"] == 0 and stats["last_clicked_at"] is None

    for minute in (5, 10, 15):
        now["t"] = datetime(2026, 10, 26, 9, minute, 0)
        client.get(f"/{code}")

    stats = client.get(f"/links/{code}/stats").get_json()
    assert stats["total_clicks"] == 3
    assert stats["last_clicked_at"] == "2026-10-26T09:15:00Z"


def test_expired_clicks_not_counted(client, now):
    code = make(client, expires_at="2026-10-26T10:00:00Z").get_json()["short_code"]
    client.get(f"/{code}")  # 1 real click
    now["t"] = datetime(2026, 10, 26, 11, 0, 0)
    client.get(f"/{code}") 

    stats = client.get(f"/links/{code}/stats").get_json()
    assert stats["total_clicks"] == 1
    assert stats["expired"] is True


def test_stats_unknown_code_is_404(client):
    assert client.get("/links/nope/stats").status_code == 404


def test_validators():
    assert is_valid_url("https://example.com/x?y=1")
    assert not is_valid_url(None)
    assert is_valid_alias("My-Link_1")
    assert not is_valid_alias("links")