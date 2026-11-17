"""Apple Music web catalog integration and exact-ID regression coverage.

The small US/CN responses are recorded public catalog data from 2026-11-17.
No account credentials or live network are used by these tests.
"""

import base64
import copy
import json
import time
from pathlib import Path

import httpx
import pytest

from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.integrations.apple_music_client import AppleMusicClient
from beatprints_api.integrations.catalog import apple_music
from beatprints_api.integrations.destinations import apple_music as destination
from beatprints_api.integrations.region import current_region, use_region
from beatprints_api.services import matching

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "apple_music_web_catalog.json").read_text()
)


def fake_jwt(issuer="AMPWebPlay", expires=None):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    return f'{encode({"alg": "ES256"})}.{encode({"iss": issuer, "exp": expires or time.time() + 3600})}.signature'


@pytest.fixture
def apple_http(monkeypatch):
    """Exercise the real transport against recorded responses without internet."""
    calls = []
    token = fake_jwt()

    def handler(request):
        calls.append(request)
        assert request.url.host in {"music.apple.com", "amp-api.music.apple.com"}
        assert "music-user-token" not in request.headers
        if request.url.host == "music.apple.com":
            assert "authorization" not in request.headers
            if request.url.path == "/":
                return httpx.Response(
                    200, text='<script src="/assets/index~fixture.js"></script>'
                )
            return httpx.Response(200, text=f'let token="{token}";')

        assert request.headers["authorization"] == f"Bearer {token}"
        assert request.headers["origin"] == "https://music.apple.com"
        parts = request.url.path.split("/")
        region = parts[3].upper()
        resource = parts[4]
        data = FIXTURE[region]
        if resource == "search":
            assert request.url.params["types"] == "songs,albums"
            return httpx.Response(
                200,
                json={
                    "results": {
                        "songs": {"data": data["track_search"]},
                        "albums": {"data": data["album_search"]},
                    }
                },
            )
        if resource == "songs" and len(parts) == 5:
            return httpx.Response(200, json={"data": [data["track"]]})
        if resource in ("songs", "albums") and len(parts) == 6:
            row = data["track" if resource == "songs" else "album"]
            return (
                httpx.Response(200, json={"data": [row]})
                if row["id"] == parts[5]
                else httpx.Response(404)
            )
        return httpx.Response(500)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AppleMusicClient(http)
    monkeypatch.setattr(apple_music, "apple_music_client", client)
    monkeypatch.setattr(destination, "apple_music_client", client)
    yield calls
    http.close()


@pytest.mark.parametrize(
    ("region", "track_id", "track_title", "album_id", "album_title", "label"),
    [
        (
            "US",
            "1721464906",
            "Sunny Day",
            "1721464893",
            "Yeh, Hwei-Mei",
            "Universal Music Taiwan (JVR)",
        ),
        (
            "CN",
            "535824738",
            "晴天",
            "535824731",
            "叶惠美",
            "JVR MUSIC INTERNATIONAL LTD.",
        ),
    ],
)
def test_source_search_and_current_metadata_preserve_selected_identity(
    apple_http, region, track_id, track_title, album_id, album_title, label
):
    with use_region(region):
        tracks = apple_music.search("晴天", "track", 2)
        albums = apple_music.search("晴天", "album", 2)
        track = apple_music.track_metadata(tracks[0]["id"])
        album = apple_music.album_metadata(albums[0]["id"])
    assert (tracks[0]["provider"], tracks[0]["id"], tracks[0]["album"]["id"]) == (
        "apple_music",
        track_id,
        album_id,
    )
    assert (albums[0]["id"], albums[0]["track_count"]) == (album_id, 11)
    assert (track.title, track.album, track.label, track.isrc) == (
        track_title,
        album_title,
        label,
        "TWK970300503",
    )
    assert (album.title, album.label, len(album.tracks)) == (album_title, label, 11)
    assert "600x600" in track.cover and track.link == tracks[0]["link"]
    requests = [r for r in apple_http if r.url.host == "amp-api.music.apple.com"]
    assert all(
        r.url.path.startswith(f"/v1/catalog/{region.lower()}/") for r in requests
    )
    assert any(r.url.path.endswith(f"/songs/{track_id}") for r in requests)
    assert any(r.url.path.endswith(f"/albums/{album_id}") for r in requests)


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_destination_search_and_manual_resolution_use_current_metadata(
    apple_http, item_type
):
    with use_region("US"):
        candidates = destination.search("晴天", item_type)
        selected = candidates[0]
        resolved = destination.resolve(selected["url"])
    assert resolved.title == selected["title"]
    assert resolved.artists == ["Jay Chou"]
    assert resolved.type == item_type
    assert (resolved.album if item_type == "track" else resolved.track_count) == (
        "Yeh, Hwei-Mei" if item_type == "track" else 11
    )
    resource = "songs" if item_type == "track" else "albums"
    assert any(
        f"/{resource}/{selected['platform_id']}" in r.url.path for r in apple_http
    )


def test_cross_region_track_matching_uses_isrc_and_keeps_source_identity(apple_http):
    result = matching.platform_match_options(
        "apple_music",
        "535824738",
        "track",
        "apple_music",
        source_region="CN",
        destination_region="US",
    )
    assert result.match is not None
    assert result.match.title == "Sunny Day" and "1721464906" in str(result.match.url)
    requests = [r for r in apple_http if r.url.host == "amp-api.music.apple.com"]
    assert any(r.url.path.endswith("/cn/songs/535824738") for r in requests)
    assert any(
        r.url.path.endswith("/us/songs")
        and r.url.params.get("filter[isrc]") == "TWK970300503"
        for r in requests
    )


def test_cross_region_album_remains_a_manual_candidate(apple_http):
    result = matching.platform_match_options(
        "apple_music",
        "535824731",
        "album",
        "apple_music",
        source_region="CN",
        destination_region="US",
    )
    assert result.match is None
    assert any("1721464893" in str(item.url) for item in result.candidates)


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_missing_same_platform_item_is_explicit_no_match(apple_http, item_type):
    with use_region("US"), pytest.raises(PlatformLinkNoMatchError):
        destination.adapter.resolve_source("apple_music", "123456789", item_type)


@pytest.mark.parametrize(
    "url",
    [
        "https://other.example/us/album/123",
        "https://music.apple.com/us/artist/example/123",
        "https://music.apple.com/us/album/example/not-an-id",
        "https://music.apple.com.evil.example/us/album/123",
    ],
)
def test_manual_link_rejects_non_catalog_or_non_apple_urls(apple_http, url):
    with pytest.raises(PlatformLinkNoMatchError):
        destination.resolve(url)
    assert not apple_http


@pytest.mark.parametrize(
    ("copyright_text", "expected"),
    [
        ("℗ 2003 JVR MUSIC INTERNATIONAL LTD.", "JVR MUSIC INTERNATIONAL LTD."),
        ("(P) 2018 JYP Entertainment Company", "JYP Entertainment Company"),
        (
            "℗ 2023 Artist under exclusive license to Label",
            "Artist under exclusive license to Label",
        ),
        ("℗ 2023", ""),
        ("© 2023 Publisher", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_album_label_prefers_record_label_and_uses_only_phonographic_copyright(
    copyright_text, expected
):
    row = {"attributes": {"copyright": copyright_text}}
    assert AppleMusicClient.album_label(row) == expected
    row["attributes"]["recordLabel"] = " Actual Label "
    assert AppleMusicClient.album_label(row) == "Actual Label"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(" twk970300503 ", "TWK970300503"), ("not an isrc", None), (None, None)],
)
def test_recording_identifier_is_normalized_and_validated(value, expected):
    row = copy.deepcopy(FIXTURE["CN"]["track"])
    row["attributes"]["isrc"] = value
    assert AppleMusicClient.normalize(row, "track")["isrc"] == expected


def test_track_label_request_failure_does_not_prevent_generation(monkeypatch):
    song = copy.deepcopy(FIXTURE["CN"]["track"])
    calls = []

    def item(identifier, item_type, **_kwargs):
        calls.append((identifier, item_type, current_region()))
        if item_type == "track":
            return song
        raise UpstreamError("album unavailable")

    monkeypatch.setattr(apple_music.apple_music_client, "item", item)
    with use_region("CN"):
        metadata = apple_music.track_metadata(song["id"])
    assert metadata.title == "晴天" and metadata.label == ""
    assert calls == [("535824738", "track", "CN"), ("535824731", "album", "CN")]


def test_track_does_not_guess_an_unrelated_album_for_label(monkeypatch):
    song = copy.deepcopy(FIXTURE["CN"]["track"])
    song["attributes"]["url"] = "https://music.apple.com/cn/song/535824738"
    song["relationships"]["albums"]["data"][0]["attributes"][
        "name"
    ] = "A different album"
    calls = []
    monkeypatch.setattr(
        apple_music.apple_music_client,
        "item",
        lambda identifier, kind, **_: calls.append((identifier, kind)) or song,
    )
    metadata = apple_music.track_metadata(song["id"])
    assert metadata.label == "" and calls == [("535824738", "track")]


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_partial_invalid_search_data_is_skipped_and_all_invalid_fails(
    monkeypatch, item_type
):
    valid = FIXTURE["US"]["track_search" if item_type == "track" else "album_search"][0]
    monkeypatch.setattr(
        apple_music.apple_music_client, "search", lambda *_: [{"id": "bad"}, valid]
    )
    assert apple_music.search("x", item_type, 5)[0]["id"] == valid["id"]
    monkeypatch.setattr(
        apple_music.apple_music_client, "search", lambda *_: [{"id": "bad"}]
    )
    with pytest.raises(UpstreamError, match="incomplete"):
        apple_music.search("x", item_type, 5)
    with pytest.raises(UpstreamError, match="incomplete"):
        destination.search("x", item_type)
