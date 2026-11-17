"""Regional choices stay isolated across source, destination and requests."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from BeatPrints import deez

from beatprints_api.integrations.region import current_region, use_region
from beatprints_api.integrations.catalog import apple_music
from beatprints_api.integrations.destinations import apple_music as apple_destination
from beatprints_api.integrations.spotify_client import SpotifyClient
from beatprints_api.main import app
from beatprints_api.models import TrackPosterRequest, AlbumPosterRequest
from beatprints_api.services import catalog


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_spotify_search_uses_request_region(monkeypatch, item_type):
    client = SpotifyClient("id", "secret")
    seen = []

    def get(path, params=None):
        seen.append(params["market"])
        return {"tracks" if item_type == "track" else "albums": {"items": []}}

    monkeypatch.setattr(client, "_get", get)
    with use_region("JP"):
        client.search("test", item_type, 5)
    client.search("test", item_type, 5)
    assert seen == ["JP", "US"]


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_apple_search_and_resolve_use_request_region(monkeypatch, item_type):
    seen = []
    row = {
        "type": "songs" if item_type == "track" else "albums",
        "id": "12",
        "attributes": {
            "name": "Song" if item_type == "track" else "Album",
            "albumName": "Album",
            "artistName": "Artist",
            "url": (
                "https://music.apple.com/jp/album/12?i=12"
                if item_type == "track"
                else "https://music.apple.com/jp/album/12"
            ),
            "artwork": {"url": "https://example.com/{w}x{h}.jpg"},
        },
    }

    def search(_query, _kind, _limit):
        seen.append(current_region())
        return [row]

    def item(_identifier, _kind, **_kwargs):
        seen.append(current_region())
        return row

    client = apple_music.apple_music_client
    monkeypatch.setattr(client, "search", search)
    monkeypatch.setattr(client, "item", item)
    with use_region("JP"):
        apple_music.search("Song", item_type, 5)
        apple_destination.search("Song", item_type)
        apple_destination.resolve(row["attributes"]["url"])
    assert seen == ["JP", "JP", "JP"]


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_source_metadata_cache_is_partitioned_by_region(monkeypatch, item_type):
    seen = []

    def metadata(_id):
        seen.append(current_region())
        if item_type == "track":
            return deez.TrackMetadata(
                title=seen[-1],
                artists=[],
                album="a",
                released="2024",
                duration="1:00",
                cover="x",
                label="label",
            )
        return deez.AlbumMetadata(
            title=seen[-1],
            artists=[],
            released="2024",
            tracks=["x"],
            cover="x",
            label="label",
        )

    monkeypatch.setattr(
        catalog,
        "get_catalog_adapter",
        lambda _: SimpleNamespace(track_metadata=metadata, album_metadata=metadata),
    )
    catalog.clear_metadata_cache()
    request = (TrackPosterRequest if item_type == "track" else AlbumPosterRequest)(
        provider="spotify", catalog_id="1"
    )
    get = catalog.track_metadata if item_type == "track" else catalog.album_metadata
    for region in ("JP", "US", "JP"):
        with use_region(region):
            assert get(request).title == region
    assert seen == ["JP", "US"]
    catalog.clear_metadata_cache()


def test_invalid_region_is_rejected():
    response = TestClient(app).get(
        "/v1/search", params={"query": "a", "provider": "spotify", "region": "japan"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_matching_scopes_source_and_destination_separately(item_type):
    from beatprints_api.integrations.destinations.base import DestinationAdapter
    from beatprints_api.services.matching import platform_match_options

    seen = []

    def source(provider, catalog_id, kind):
        seen.append(("source", current_region(), provider, catalog_id, kind))
        if kind == "track":
            return deez.TrackMetadata(
                title="Song",
                artists=["Artist"],
                album="Album",
                released="2024",
                duration="01:00",
                cover="x",
                label="x",
            )
        return deez.AlbumMetadata(
            title="Album",
            artists=["Artist"],
            released="2024",
            tracks=["Song"],
            cover="x",
            label="x",
        )

    def search(query, kind):
        seen.append(("destination", current_region()))
        return []

    adapter = DestinationAdapter(search=search, resolve=lambda url: None)
    result = platform_match_options(
        "qq_music",
        "exact-id",
        item_type,
        "spotify",
        source_region="JP",
        destination_region="GB",
        source_metadata_fn=source,
        destination_adapter_fn=lambda _: adapter,
    )
    assert result.match is None
    assert seen[0] == ("source", "JP", "qq_music", "exact-id", item_type)
    assert all(entry == ("destination", "GB") for entry in seen[1:])


@pytest.mark.parametrize(
    "provider", ["apple_music", "spotify", "qq_music", "netease_music"]
)
@pytest.mark.parametrize("item_type", ["track", "album"])
def test_missing_direct_match_still_returns_ranked_candidates(
    monkeypatch, provider, item_type
):
    from beatprints_api.exceptions import PlatformLinkNoMatchError
    from beatprints_api.integrations.destinations import (
        apple_music,
        netease_music,
        qq_music,
        spotify,
    )
    from beatprints_api.integrations.destinations.registry import (
        get_destination_adapter,
    )
    from beatprints_api.services import matching

    seen = []

    def no_direct_match(url):
        seen.append(("direct", current_region(), url))
        raise PlatformLinkNoMatchError("No item in the selected region")

    def source_metadata(source, catalog_id, kind):
        seen.append(("source", current_region(), source, catalog_id, kind))
        if kind == "track":
            return deez.TrackMetadata(
                title="Song",
                artists=["Artist"],
                album="Album",
                released="2024",
                duration="01:00",
                cover="x",
                label="x",
            )
        return deez.AlbumMetadata(
            title="Album",
            artists=["Artist"],
            released="2024",
            tracks=["Song"],
            cover="x",
            label="x",
        )

    def search(_query, kind):
        seen.append(("search", current_region()))
        return [
            {
                "url": "https://example.com/candidate",
                "title": "Song" if kind == "track" else "Album",
                "artists": ["Someone else"],
                "type": kind,
            }
        ]

    modules = {
        "apple_music": apple_music,
        "spotify": spotify,
        "qq_music": qq_music,
        "netease_music": netease_music,
    }
    monkeypatch.setattr(modules[provider], "resolve", no_direct_match)
    adapter = replace(get_destination_adapter(provider), search=search)
    monkeypatch.setattr(matching, "_destination_adapter", lambda _: adapter)
    monkeypatch.setattr(matching, "_source_metadata", source_metadata)
    monkeypatch.setattr(matching, "_source_isrc", lambda *_: None)
    response = TestClient(app).get(
        f"/v1/platform-links/{provider}/options",
        params={
            "provider": provider,
            "catalog_id": "exact-id",
            "type": item_type,
            "source_region": "US",
            "destination_region": "JP",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"].get("match") is None
    assert [item["url"] for item in response.json()["data"]["candidates"]] == [
        "https://example.com/candidate"
    ]
    assert seen[0][:2] == ("direct", "JP")
    assert "exact-id" in seen[0][2]
    assert seen[1] == ("source", "US", provider, "exact-id", item_type)
    assert all(item == ("search", "JP") for item in seen[2:])


def test_direct_match_upstream_failures_are_not_hidden(monkeypatch):
    from beatprints_api.exceptions import UpstreamError
    from beatprints_api.integrations.destinations.base import DestinationAdapter
    from beatprints_api.services import matching

    def unavailable(*_args):
        raise UpstreamError("destination unavailable")

    adapter = DestinationAdapter(
        search=lambda *_: [], resolve=lambda _: None, resolve_source=unavailable
    )
    monkeypatch.setattr(matching, "_destination_adapter", lambda _: adapter)
    response = TestClient(app).get(
        "/v1/platform-links/apple_music/options",
        params={"provider": "apple_music", "catalog_id": "1", "type": "track"},
    )
    assert response.status_code == 502


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_render_resolves_reused_source_in_destination_region(monkeypatch, item_type):
    from beatprints_api.integrations.destinations.base import DestinationAdapter
    from beatprints_api.models import PlatformLinkMatchData
    from beatprints_api.services import rendering

    seen = []

    def resolve_source(provider, catalog_id, kind):
        seen.append((provider, catalog_id, kind, current_region()))
        return PlatformLinkMatchData(
            url="https://example.com/jp", title="Title", artists=[], type=kind
        )

    adapter = DestinationAdapter(
        search=lambda *_: [], resolve=lambda _: None, resolve_source=resolve_source
    )
    monkeypatch.setattr(rendering, "get_destination_adapter", lambda _: adapter)
    assert rendering.selected_platform_link(
        None, "test", "test", "https://example.com/us", "JP", "123", item_type
    ) == (adapter, "https://example.com/jp")
    assert seen == [("test", "123", item_type, "JP")]


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_spotify_metadata_uses_request_region(monkeypatch, item_type):
    client = SpotifyClient("id", "secret")
    seen = []
    album = {
        "name": "Album",
        "artists": [{"name": "Artist"}],
        "release_date": "2024",
        "tracks": {"items": []},
        "images": [{"url": "https://example.com/cover"}],
        "external_urls": {"spotify": "https://open.spotify.com/album/1"},
    }

    def get(path, params=None):
        seen.append(params["market"])
        if path.startswith("/tracks/"):
            return {
                "name": "Song",
                "artists": [{"name": "Artist"}],
                "album": {"id": "1"},
                "duration_ms": 60000,
                "external_urls": {"spotify": "https://open.spotify.com/track/1"},
            }
        return album

    monkeypatch.setattr(client, "_get", get)
    with use_region("GB"):
        (client.track_metadata if item_type == "track" else client.album_metadata)("1")
    assert seen and all(region == "GB" for region in seen)


def test_capabilities_expose_distinct_enabled_platform_regions():
    response = TestClient(app).get("/v1/capabilities")
    assert response.status_code == 200
    data = response.json()["data"]
    for role in ("catalogs", "destinations"):
        adapters = {item["key"]: item for item in data[role]}
        apple = adapters["apple_music"]["regions"]
        spotify = adapters["spotify"]["regions"]
        assert len(apple) == len(set(apple)) and len(spotify) == len(set(spotify))
        assert all(
            len(code) == 2 and code.isascii() and code.isupper()
            for code in apple + spotify
        )
        assert {"US", "JP", "CN", "MM"} <= set(apple)
        assert {"US", "JP", "GB"} <= set(spotify)
        assert "AQ" not in apple and "AQ" not in spotify
        assert "CN" not in spotify and "MM" not in spotify
        assert (
            not adapters["qq_music"]["supports_regions"]
            and not adapters["qq_music"]["regions"]
        )
    assert {item["key"]: item["regions"] for item in data["catalogs"]}[
        "apple_music"
    ] == {item["key"]: item["regions"] for item in data["destinations"]}["apple_music"]
    assert {item["key"]: item["regions"] for item in data["catalogs"]}["spotify"] == {
        item["key"]: item["regions"] for item in data["destinations"]
    }["spotify"]
