from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from beatprints_api.api import dependencies
from beatprints_api.api.routes import catalog, posters
from beatprints_api.main import app, create_app
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
    assert process_time.isdigit()


def test_web_app_is_served_without_shadowing_api(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>BeatPrints</h1>")
    (tmp_path / "favicon.svg").write_text("<svg></svg>")
    web_client = TestClient(create_app(web_root=tmp_path))

    assert web_client.get("/").text == "<h1>BeatPrints</h1>"
    assert web_client.get("/studio").text == "<h1>BeatPrints</h1>"
    assert web_client.get("/favicon.svg").text == "<svg></svg>"
    assert web_client.head("/favicon.svg").status_code == 200
    assert web_client.get("/health").json()["data"]["status"] == "ok"


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
        lambda request: posters.beatprints_service.PosterResult(
            b"\x89PNG\r\n\x1a\n",
            "poster.png",
            {"metadata": 12.6, "render": 34.6},
        ),
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
    assert "queue;dur=" in response.headers["server-timing"]
    assert "metadata;dur=13" in response.headers["server-timing"]
    assert "render;dur=35" in response.headers["server-timing"]
    assert response.headers["x-process-time"]


def test_poster_response_supports_unicode_filenames(monkeypatch) -> None:
    monkeypatch.setattr(
        posters.beatprints_service,
        "generate_album",
        lambda request: posters.beatprints_service.PosterResult(
            b"\x89PNG\r\n\x1a\n",
            "我在切爾諾貝爾　等你 - Juno Mak.png",
            {},
        ),
    )
    response = client.post(
        "/v1/posters/album",
        json={"query": "test"},
    )

    assert response.status_code == 200
    assert 'filename="beatprints-poster.png"' in response.headers["content-disposition"]
    assert "filename*=UTF-8''%E6%88%91" in response.headers["content-disposition"]


def test_platform_links_require_at_least_one_url() -> None:
    response = client.post(
        "/v1/posters/track",
        json={
            "catalog_id": "spotify-track-id",
            "platform_links": {},
            "lyrics": "one\ntwo\nthree\nfour",
        },
    )

    assert response.status_code == 422
    assert "at least one platform URL" in response.text


def test_selected_qr_platform_requires_its_link() -> None:
    response = client.post(
        "/v1/posters/track",
        json={
            "catalog_id": "spotify-track-id",
            "qr_platform": "apple_music",
            "platform_links": {
                "spotify": "https://open.spotify.com/track/spotify-track-id"
            },
            "lyrics": "one\ntwo\nthree\nfour",
        },
    )

    assert response.status_code == 422
    assert "platform_links.apple_music is required" in response.text


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


def test_lyrics_preview_preserves_catalog_reference(monkeypatch) -> None:
    monkeypatch.setattr(
        catalog.beatprints_service,
        "preview_lyrics",
        lambda provider, catalog_id: {
            "provider": provider,
            "catalog_id": catalog_id,
            "instrumental": False,
            "lines": [
                {"index": 1, "text": "First line"},
                {"index": 2, "text": "Second line"},
                {"index": 3, "text": "Third line"},
                {"index": 4, "text": "Fourth line"},
            ],
        },
    )

    response = client.get(
        "/v1/lyrics",
        params={"provider": "deezer", "catalog_id": "5416564"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "provider": "deezer",
        "catalog_id": "5416564",
        "instrumental": False,
        "lines": [
            {"index": 1, "text": "First line"},
            {"index": 2, "text": "Second line"},
            {"index": 3, "text": "Third line"},
            {"index": 4, "text": "Fourth line"},
        ],
    }


def test_apple_music_match_preserves_selected_catalog_reference(monkeypatch) -> None:
    seen: dict[str, str] = {}

    def match(provider: str, catalog_id: str, item_type: str) -> dict:
        seen.update(provider=provider, catalog_id=catalog_id, item_type=item_type)
        return {
            "url": "https://music.apple.com/us/album/example/123456789?i=123456790",
            "title": "Example",
            "artists": ["Artist"],
            "album": "Example Album",
            "type": item_type,
        }

    monkeypatch.setattr(catalog.beatprints_service, "match_apple_music", match)

    response = client.get(
        "/v1/platform-links/apple-music",
        params={"provider": "deezer", "catalog_id": "5416564", "type": "track"},
    )

    assert response.status_code == 200
    assert seen == {"provider": "deezer", "catalog_id": "5416564", "item_type": "track"}
    assert response.json()["data"] == {
        "url": "https://music.apple.com/us/album/example/123456789?i=123456790",
        "title": "Example",
        "artists": ["Artist"],
        "album": "Example Album",
        "type": "track",
    }


def test_apple_music_match_returns_not_found_when_not_confident(monkeypatch) -> None:
    def no_match(*_args: object) -> None:
        raise catalog.beatprints_service.AppleMusicNoMatchError(
            "No confident Apple Music match was found"
        )

    monkeypatch.setattr(catalog.beatprints_service, "match_apple_music", no_match)

    response = client.get(
        "/v1/platform-links/apple-music",
        params={"provider": "spotify", "catalog_id": "track-id", "type": "track"},
    )

    assert response.status_code == 404
    assert response.json()["message"] == "No confident Apple Music match was found"


def test_apple_music_link_resolve_returns_link_metadata(monkeypatch) -> None:
    seen: dict[str, str] = {}

    def resolve(url: str) -> dict:
        seen["url"] = url
        return {
            "url": url,
            "title": "Manual match",
            "artists": ["Artist"],
            "album": "Album",
            "cover_url": "https://example.com/cover.jpg",
            "type": "track",
        }

    monkeypatch.setattr(catalog.beatprints_service, "resolve_apple_music_url", resolve)
    url = "https://music.apple.com/us/album/example/123456789?i=123456790"

    response = client.get("/v1/platform-links/apple-music/resolve", params={"url": url})

    assert response.status_code == 200
    assert seen == {"url": url}
    assert response.json()["data"]["cover_url"] == "https://example.com/cover.jpg"


def test_deezer_track_can_match_spotify(monkeypatch) -> None:
    monkeypatch.setattr(
        catalog.beatprints_service,
        "match_deezer_to_spotify",
        lambda catalog_id, item_type: {
            "url": "https://open.spotify.com/track/spotify-track-id",
            "title": "Example",
            "artists": ["Artist"],
            "album": "Album",
            "cover_url": "https://i.scdn.co/image/example",
            "type": item_type,
        },
    )

    response = client.get(
        "/v1/platform-links/spotify",
        params={"provider": "deezer", "catalog_id": "5416564", "type": "track"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["url"] == "https://open.spotify.com/track/spotify-track-id"


def test_spotify_link_resolve_returns_link_metadata(monkeypatch) -> None:
    seen: dict[str, str] = {}

    def resolve(url: str) -> dict:
        seen["url"] = url
        return {
            "url": url,
            "title": "Manual Spotify match",
            "artists": ["Artist"],
            "album": "Album",
            "cover_url": "https://i.scdn.co/image/example",
            "type": "track",
        }

    monkeypatch.setattr(catalog.beatprints_service, "resolve_spotify_url", resolve)
    url = "https://open.spotify.com/track/7lp5evZr7qEDwlv5PS8b6i"

    response = client.get("/v1/platform-links/spotify/resolve", params={"url": url})

    assert response.status_code == 200
    assert seen == {"url": url}
    assert response.json()["data"]["cover_url"] == "https://i.scdn.co/image/example"


def test_track_allows_empty_instrumental_text() -> None:
    from beatprints_api.models import TrackPosterRequest

    request = TrackPosterRequest(
        provider="deezer",
        catalog_id=5416564,
        instrumental_text="",
    )

    assert request.instrumental_text == ""


def test_empty_instrumental_text_is_safe_for_upstream_renderer() -> None:
    from beatprints_api.services.beatprints import _renderable_lyrics

    assert _renderable_lyrics("") == " "
    assert _renderable_lyrics("visible") == "visible"


def test_track_rejects_more_than_four_poster_text_lines() -> None:
    from beatprints_api.models import TrackPosterRequest

    with pytest.raises(ValueError, match="at most four lines"):
        TrackPosterRequest(
            provider="deezer",
            catalog_id=1,
            lyrics="one\ntwo\nthree\nfour\nfive",
        )

    with pytest.raises(ValueError, match="at most four lines"):
        TrackPosterRequest(
            provider="deezer",
            catalog_id=1,
            instrumental_text="one\ntwo\nthree\nfour\nfive",
        )


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
    lyrics = schema["paths"]["/v1/lyrics"]["get"]
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
    assert lyrics["responses"]["200"]["content"]["application/json"]["schema"]
    assert track["requestBody"]["content"]["application/json"]["schema"].get(
        "description"
    )
    assert album["requestBody"]["content"]["application/json"]["schema"].get(
        "description"
    )
    assert set(track["requestBody"]["content"]["application/json"]["examples"]) == {
        "search_no_qr",
        "spotify_qr_auto",
        "apple_music_qr",
        "qq_music_qr",
        "custom",
    }
    assert set(album["requestBody"]["content"]["application/json"]["examples"]) == {
        "search_no_qr",
        "spotify_qr_auto",
        "netease_music_qr",
        "custom",
    }
    assert "未提供 `qr_platform` 时不显示" in track["description"]
    assert "未提供 `qr_platform` 时不显示" in album["description"]
    assert "封面取色二维码" in track["responses"]["200"]["description"]
    assert "封面取色二维码" in album["responses"]["200"]["description"]
    track_examples = track["requestBody"]["content"]["application/json"]["examples"]
    assert "qr_platform" not in track_examples["search_no_qr"]["value"]
    assert track_examples["spotify_qr_auto"]["value"]["qr_platform"] == "spotify"
    assert track_examples["apple_music_qr"]["value"]["qr_platform"] == "apple_music"
    assert track_examples["qq_music_qr"]["value"]["qr_platform"] == "qq_music"
    album_examples = album["requestBody"]["content"]["application/json"]["examples"]
    assert "qr_platform" not in album_examples["search_no_qr"]["value"]
    assert album_examples["spotify_qr_auto"]["value"]["qr_platform"] == "spotify"
    assert album_examples["netease_music_qr"]["value"]["qr_platform"] == "netease_music"
    platform_links = schema["components"]["schemas"]["PosterPlatformLinks"]
    assert set(platform_links["properties"]) == {
        "spotify",
        "apple_music",
        "qq_music",
        "netease_music",
    }
    assert set(
        schema["components"]["schemas"]["TrackPosterRequest"]["properties"][
            "qr_platform"
        ]["anyOf"][0]["enum"]
    ) == {"spotify", "apple_music", "qq_music", "netease_music"}
    track_schema = schema["components"]["schemas"]["TrackPosterRequest"]
    album_schema = schema["components"]["schemas"]["AlbumPosterRequest"]
    assert track_schema["example"]["query"] == "Summer Breeze Piper"
    assert album_schema["example"]["query"] == "Summer Breeze Piper"
    assert schema["components"]["schemas"]["TrackMetadataInput"]["properties"][
        "artists"
    ]["examples"] == [["Piper"]]
    assert schema["components"]["schemas"]["TrackMetadataInput"]["properties"][
        "duration"
    ]["examples"] == ["03:23"]
