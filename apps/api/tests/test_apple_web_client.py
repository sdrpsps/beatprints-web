"""Anonymous web-token lifecycle, Apple Music transport and pagination."""

import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.clients.apple_music import (
    AppleMusicClient,
    AppleMusicNotFound,
    _web_token,
)
from beatprints_api.integrations.region import use_region


def token(issuer="AMPWebPlay", expires=None):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    return f'{encode({"alg": "ES256"})}.{encode({"iss": issuer, "exp": expires or time.time() + 3600})}.signature'


def test_public_token_is_cached_and_refreshed_after_unauthorized_response():
    first, second = token(expires=time.time() + 3600), token(expires=time.time() + 7200)
    calls = []
    count = {"bundle": 0}

    def handler(request):
        calls.append(request)
        if request.url.host == "music.apple.com":
            assert "authorization" not in request.headers
            if request.url.path == "/":
                return httpx.Response(
                    200, text='<script src="/assets/index~test.js"></script>'
                )
            count["bundle"] += 1
            return httpx.Response(
                200, text=f'var t="{first if count["bundle"] == 1 else second}"'
            )
        assert request.url.host == "amp-api.music.apple.com"
        assert request.headers["origin"] == "https://music.apple.com"
        assert "music-user-token" not in request.headers
        if request.headers["authorization"] == f"Bearer {first}":
            return httpx.Response(401)
        assert request.headers["authorization"] == f"Bearer {second}"
        return httpx.Response(200, json={"results": {}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = AppleMusicClient(http)
        assert client.search("晴天", "track", 5) == []
        assert client.search("晴天", "album", 5) == []
    assert count["bundle"] == 2
    assert len([r for r in calls if r.url.host == "amp-api.music.apple.com"]) == 3


def test_concurrent_requests_share_token_fetch():
    current_token = token()
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.host == "music.apple.com":
            if request.url.path == "/":
                return httpx.Response(
                    200, text='<script src="/assets/index~test.js"></script>'
                )
            time.sleep(0.01)
            return httpx.Response(200, text=current_token)
        return httpx.Response(200, json={"results": {}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = AppleMusicClient(http)
        with ThreadPoolExecutor(max_workers=6) as executor:
            assert (
                list(
                    executor.map(lambda _: client.search("test", "track", 3), range(6))
                )
                == [[]] * 6
            )
    assert calls.count("/") == 1 and calls.count("/assets/index~test.js") == 1


def test_web_token_parser_selects_current_web_player_token():
    invalid_issuer = token(issuer="other")
    expired = token(expires=time.time() - 30)
    active = token()
    assert _web_token(f"{invalid_issuer} {expired} {active}")[0] == active
    assert _web_token(f"{invalid_issuer} {expired} eyJbad.eyJbad.signature") is None


def test_near_expiry_token_is_refreshed_before_the_request():
    old = token(expires=time.time() + 120)
    fresh = token(expires=time.time() + 3600)
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.host == "music.apple.com":
            if request.url.path == "/":
                return httpx.Response(
                    200, text='<script src="/assets/index~test.js"></script>'
                )
            return httpx.Response(200, text=fresh)
        assert request.headers["authorization"] == f"Bearer {fresh}"
        return httpx.Response(200, json={"results": {}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = AppleMusicClient(http)
        client._token, client._expires_at = old, time.time() + 30
        assert client.search("test", "track", 5) == []
    assert len(requests) == 3


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failure_refreshes_once_then_reports_failure(status):
    current_token = token()
    attempts = []

    def handler(request):
        if request.url.host == "music.apple.com":
            if request.url.path == "/":
                return httpx.Response(
                    200, text='<script src="/assets/index~test.js"></script>'
                )
            return httpx.Response(200, text=current_token)
        attempts.append(request)
        return httpx.Response(status)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(UpstreamError) as error:
            AppleMusicClient(http).search("test", "track", 5)
    assert len(attempts) == 2
    assert current_token not in str(error.value)


def test_missing_token_and_untrusted_script_do_not_leave_apple_hosts():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(
            200, text='<script src="https://example.invalid/index~evil.js"></script>'
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(UpstreamError, match="token is unavailable"):
            AppleMusicClient(http).search("test", "track", 5)
    assert calls == ["https://music.apple.com/"]


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"results": None},
        {"results": {"songs": {}}},
        {"results": {"songs": {"data": [None]}}},
    ],
)
def test_invalid_search_response_is_not_reported_as_empty(monkeypatch, response):
    client = AppleMusicClient()
    monkeypatch.setattr(client, "_request", lambda *_args, **_kwargs: response)
    with pytest.raises(UpstreamError, match="invalid response"):
        client.search("test", "track", 5)
    client.http.close()


def test_catalog_item_rejects_wrong_id_type_and_missing_items(monkeypatch):
    client = AppleMusicClient()
    monkeypatch.setattr(
        client,
        "_request",
        lambda *_args, **_kwargs: {"data": [{"id": "other", "type": "songs"}]},
    )
    with pytest.raises(UpstreamError, match="different item"):
        client.item("123", "track")
    monkeypatch.setattr(client, "_request", lambda *_args, **_kwargs: {"data": []})
    with pytest.raises(AppleMusicNotFound):
        client.item("123", "track")
    with pytest.raises(AppleMusicNotFound):
        client.item("../123", "track")
    client.http.close()


def test_album_track_pagination_retrieves_every_page_in_order(monkeypatch):
    client = AppleMusicClient()
    calls = []
    album = {
        "id": "34",
        "relationships": {
            "tracks": {
                "data": [{"attributes": {"name": "One"}}],
                "next": "/v1/catalog/us/albums/34/tracks?offset=1&limit=1",
            }
        },
    }

    def request(path, params):
        calls.append((path, params))
        return {"data": [{"attributes": {"name": "Two"}}]}

    monkeypatch.setattr(client, "_request", request)
    with use_region("US"):
        assert client.album_tracks(album) == ["One", "Two"]
    assert calls == [("/v1/catalog/us/albums/34/tracks", {"offset": "1", "limit": "1"})]
    client.http.close()


@pytest.mark.parametrize(
    "next_url",
    [
        "https://evil.example/v1/catalog/us/albums/34/tracks?offset=1",
        "/v1/catalog/cn/albums/34/tracks?offset=1",
        "/v1/catalog/us/albums/99/tracks?offset=1",
    ],
)
def test_album_pagination_rejects_untrusted_or_wrong_album_paths(monkeypatch, next_url):
    client = AppleMusicClient()
    monkeypatch.setattr(
        client,
        "_request",
        lambda *_args: pytest.fail("Must not fetch a different album or host"),
    )
    album = {"id": "34", "relationships": {"tracks": {"data": [], "next": next_url}}}
    with use_region("US"), pytest.raises(UpstreamError, match="pagination"):
        client.album_tracks(album)
    client.http.close()


def test_isrc_filter_is_exact_and_invalid_codes_do_not_trigger_requests(monkeypatch):
    client = AppleMusicClient()
    calls = []
    monkeypatch.setattr(
        client,
        "_request",
        lambda path, params: calls.append((path, params)) or {"data": []},
    )
    with use_region("CN"):
        assert client.search_isrc("invalid") == []
        assert client.search_isrc("twk970300503") == []
    assert calls == [
        ("/v1/catalog/cn/songs", {"filter[isrc]": "TWK970300503", "limit": 10})
    ]
    client.http.close()
