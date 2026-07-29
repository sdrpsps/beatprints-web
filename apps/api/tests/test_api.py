from types import SimpleNamespace

from fastapi.testclient import TestClient

from beatprints_api.api import dependencies
from beatprints_api.api.routes import catalog, posters
from beatprints_api.main import app
from beatprints_api.spotify import SpotifyNotConfiguredError

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "data": {"status": "ok"},
        "message": "success",
    }
    assert response.headers["x-request-id"]
    process_time = response.headers["x-process-time"]
    assert float(process_time) >= 0
    assert len(process_time.rsplit(".", maxsplit=1)[-1]) == 3


def test_track_requires_exactly_one_source() -> None:
    response = client.post(
        "/v1/posters/track",
        json={
            "provider": "deezer",
            "query": "Apples - Rocco",
            "catalog_id": 123,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == 42200
    assert response.json()["data"]["errors"]
    assert "Exactly one" in response.text
    assert response.headers["x-process-time"]


def test_album_metadata_is_validated() -> None:
    response = client.post(
        "/v1/posters/album",
        json={
            "metadata": {
                "title": "Album",
                "artists": ["Artist"],
                "released": "2026",
                "tracks": [],
                "cover_url": "https://example.com/cover.jpg",
                "label": "Independent",
            }
        },
    )
    assert response.status_code == 422
    assert set(response.json()) == {"code", "data", "message"}


def test_track_returns_png(monkeypatch) -> None:
    monkeypatch.setattr(
        posters.beatprints_service,
        "generate_track",
        lambda request: (b"\x89PNG\r\n\x1a\n", "poster.png"),
    )
    response = client.post(
        "/v1/posters/track",
        json={
            "query": "Apples - Rocco",
            "lyrics": "one\ntwo\nthree\nfour",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert 'filename="poster.png"' in response.headers["content-disposition"]
    assert response.headers["x-process-time"]


def test_search_returns_rich_frontend_data(monkeypatch) -> None:
    monkeypatch.setattr(
        catalog.beatprints_service,
        "search_catalog",
        lambda query, search_type, limit, provider: [
            {
                "id": 5416564,
                "provider": "deezer",
                "type": "track",
                "title": "Summer Breeze",
                "artists": ["Seals and Crofts"],
                "cover_url": "https://example.com/cover.jpg",
                "link": "https://www.deezer.com/track/5416564",
                "release_date": "1977-10-11",
                "release_year": 1977,
                "album": {
                    "id": 496095,
                    "title": "Seals & Crofts' Greatest Hits",
                },
                "duration_seconds": 205,
                "duration": "03:25",
                "explicit": False,
                "isrc": "USWB19901645",
            }
        ],
    )
    response = client.get(
        "/v1/search",
        params={
            "query": "Summer Breeze",
            "type": "track",
            "provider": "all",
        },
    )
    body = response.json()
    result = body["data"][0]
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "success"
    assert result["cover_url"] == "https://example.com/cover.jpg"
    assert result["provider"] == "deezer"
    assert result["album"]["id"] == 496095
    assert result["duration"] == "03:25"
    assert result["release_date"] == "1977-10-11"
    assert result["release_year"] == 1977
    assert "track_count" not in result


def test_explicit_spotify_search_reports_missing_configuration(monkeypatch) -> None:
    def not_configured(*args) -> list[dict]:
        raise SpotifyNotConfiguredError("Spotify search is not configured")

    monkeypatch.setattr(catalog.beatprints_service, "search_catalog", not_configured)

    response = client.get(
        "/v1/search",
        params={
            "query": "Summer Breeze",
            "type": "track",
            "provider": "spotify",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "code": 50300,
        "data": None,
        "message": "Spotify search is not configured",
    }
    assert response.headers["x-process-time"]


def test_api_key_can_protect_v1_routes(monkeypatch) -> None:
    monkeypatch.setattr(
        dependencies,
        "settings",
        SimpleNamespace(api_key="correct-secret"),
    )
    missing = client.get("/v1/themes")
    accepted = client.get(
        "/v1/themes",
        headers={"Authorization": "Bearer correct-secret"},
    )
    assert missing.status_code == 401
    assert missing.json()["code"] == 40100
    assert accepted.status_code == 200


def test_unhandled_error_uses_unified_response(monkeypatch) -> None:
    def fail(_request) -> tuple[bytes, str]:
        raise RuntimeError("sensitive implementation detail")

    monkeypatch.setattr(posters.beatprints_service, "generate_track", fail)
    response = client.post(
        "/v1/posters/track",
        json={
            "query": "Apples - Rocco",
            "lyrics": "one\ntwo\nthree\nfour",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "code": 50000,
        "data": None,
        "message": "Internal server error",
    }
    assert response.headers["x-process-time"]


def test_not_found_uses_unified_response() -> None:
    response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "code": 40400,
        "data": None,
        "message": "Not Found",
    }
    assert response.headers["x-process-time"]


def test_openapi_includes_descriptions_and_request_examples() -> None:
    schema = app.openapi()
    search = schema["paths"]["/v1/search"]["get"]
    track = schema["paths"]["/v1/posters/track"]["post"]
    album = schema["paths"]["/v1/posters/album"]["post"]

    assert all(parameter.get("description") for parameter in search["parameters"])
    provider = next(
        parameter
        for parameter in search["parameters"]
        if parameter["name"] == "provider"
    )
    assert set(provider["schema"]["enum"]) == {"deezer", "spotify", "all"}
    assert "503" in search["responses"]
    assert track["requestBody"]["content"]["application/json"]["schema"].get(
        "description"
    )
    assert album["requestBody"]["content"]["application/json"]["schema"].get(
        "description"
    )
    assert set(track["requestBody"]["content"]["application/json"]["examples"]) == {
        "search",
        "catalog_id",
        "custom",
    }
    assert set(album["requestBody"]["content"]["application/json"]["examples"]) == {
        "search",
        "catalog_id",
        "custom",
    }
