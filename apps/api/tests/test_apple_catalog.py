"""Apple Music source normalization and exact-ID lookup regression coverage."""

import pytest

from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.catalog import apple_music
from beatprints_api.integrations.catalog.registry import get_catalog_adapter

TRACK = {"wrapperType": "track", "trackId": 12, "trackName": "Song", "artistName": "Artist",
         "collectionId": 34, "collectionName": "Album", "trackViewUrl": "https://music.apple.com/us/album/34?i=12",
         "artworkUrl100": "https://example.com/100x100bb.jpg", "releaseDate": "2024-01-02T00:00:00Z",
         "trackTimeMillis": 123000}
ALBUM = {"wrapperType": "collection", "collectionId": 34, "collectionName": "Album", "artistName": "Artist",
         "collectionViewUrl": "https://music.apple.com/us/album/34", "artworkUrl100": "https://example.com/100x100bb.jpg",
         "releaseDate": "2024-01-02T00:00:00Z", "trackCount": 1}


def test_search_normalizes_both_types_and_preserves_identity(monkeypatch):
    calls = []
    def get(url, **params):
        calls.append((url, params))
        return [TRACK, ALBUM, {}]
    monkeypatch.setattr(apple_music, "_get", get)
    track = get_catalog_adapter("apple_music").search("Song", "track", 5)[0]
    album = apple_music.search("Album", "album", 5)[0]
    assert (track["provider"], track["id"], track["album"]["id"], track["duration"]) == ("apple_music", "12", "34", "02:03")
    assert (album["id"], album["track_count"], album["release_year"]) == ("34", 1, 2024)
    assert "600x600" in track["cover_url"]
    assert calls[0][1]["entity"] == "song" and calls[1][1]["entity"] == "album"


def test_current_metadata_uses_selected_id_and_album_tracks(monkeypatch):
    calls = []
    def get(url, **params):
        calls.append(params)
        return [ALBUM, TRACK] if params["id"] == "34" else [TRACK]
    monkeypatch.setattr(apple_music, "_get", get)
    track = apple_music.track_metadata("12")
    album = apple_music.album_metadata("34")
    assert (track.title, track.album, track.link) == ("Song", "Album", TRACK["trackViewUrl"])
    assert album.tracks == ["Song"]
    assert calls == [{"id": "12"}, {"id": "34", "entity": "song", "limit": 200}]
    with pytest.raises(UpstreamError):
        apple_music.track_metadata("missing")
