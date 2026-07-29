import pytest

from beatprints_api.models import TrackPosterRequest
from beatprints_api.services import beatprints as beatprints_service
from beatprints_api.spotify import SpotifyClient, SpotifyNotConfiguredError


def test_spotify_requires_credentials() -> None:
    client = SpotifyClient(client_id=None, client_secret=None, market="US")

    with pytest.raises(SpotifyNotConfiguredError):
        client.search("SUMMER BREEZE", "track", 5)


def test_spotify_formats_track_search_result() -> None:
    item = {
        "id": "spotify-track-id",
        "name": "Summer Breeze",
        "artists": [{"name": "The Isley Brothers"}],
        "album": {
            "id": "spotify-album-id",
            "name": "3 + 3",
            "release_date": "1973-08-07",
            "release_date_precision": "day",
            "images": [{"url": "https://i.scdn.co/image/example"}],
        },
        "duration_ms": 372000,
        "explicit": False,
        "external_ids": {"isrc": "USSM17300508"},
        "external_urls": {"spotify": "https://open.spotify.com/track/spotify-track-id"},
    }

    result = SpotifyClient._format_track(item)

    assert result["provider"] == "spotify"
    assert result["id"] == "spotify-track-id"
    assert result["release_date"] == "1973-08-07"
    assert result["release_year"] == 1973
    assert result["release_date_precision"] == "day"
    assert result["duration_seconds"] == 372
    assert result["duration"] == "06:12"
    assert result["isrc"] == "USSM17300508"


def test_spotify_catalog_id_can_supply_poster_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        beatprints_service.spotify_client,
        "track_metadata",
        lambda track_id: {
            "title": "Summer Breeze",
            "artists": ["The Isley Brothers"],
            "album": "3 + 3",
            "released": "1973-08-07",
            "duration": "06:12",
            "cover": "https://i.scdn.co/image/example",
            "label": "Epic",
            "link": f"https://open.spotify.com/track/{track_id}",
        },
    )
    request = TrackPosterRequest(
        provider="spotify",
        catalog_id="spotify-track-id",
        lyrics="one\ntwo\nthree\nfour",
    )

    metadata = beatprints_service._track_metadata(request)

    assert metadata.title == "Summer Breeze"
    assert metadata.album == "3 + 3"
    assert metadata.cover == "https://i.scdn.co/image/example"
