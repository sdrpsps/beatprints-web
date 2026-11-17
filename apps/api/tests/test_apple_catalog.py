"""Apple Music source normalization and exact-ID lookup regression coverage."""

import pytest

from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.catalog import apple_music
from beatprints_api.integrations.catalog.registry import get_catalog_adapter

TRACK = {
    "wrapperType": "track",
    "trackId": 12,
    "trackName": "Song",
    "artistName": "Artist",
    "collectionId": 34,
    "collectionName": "Album",
    "trackViewUrl": "https://music.apple.com/us/album/34?i=12",
    "artworkUrl100": "https://example.com/100x100bb.jpg",
    "releaseDate": "2024-01-02T00:00:00Z",
    "trackTimeMillis": 123000,
}
ALBUM = {
    "wrapperType": "collection",
    "collectionId": 34,
    "collectionName": "Album",
    "artistName": "Artist",
    "collectionViewUrl": "https://music.apple.com/us/album/34",
    "artworkUrl100": "https://example.com/100x100bb.jpg",
    "releaseDate": "2024-01-02T00:00:00Z",
    "trackCount": 1,
}


def test_search_normalizes_both_types_and_preserves_identity(monkeypatch):
    calls = []

    def get(url, **params):
        calls.append((url, params))
        return [TRACK, ALBUM, {}]

    monkeypatch.setattr(apple_music, "_get", get)
    track = get_catalog_adapter("apple_music").search("Song", "track", 5)[0]
    album = apple_music.search("Album", "album", 5)[0]
    assert (
        track["provider"],
        track["id"],
        track["album"]["id"],
        track["duration"],
    ) == ("apple_music", "12", "34", "02:03")
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
    assert (track.title, track.album, track.link) == (
        "Song",
        "Album",
        TRACK["trackViewUrl"],
    )
    assert album.tracks == ["Song"]
    assert calls == [{"id": "12"}, {"id": "34", "entity": "song", "limit": 200}]
    with pytest.raises(UpstreamError):
        apple_music.track_metadata("missing")


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_public_catalog_fallback_keeps_storefront_and_ranked_ids(
    monkeypatch, item_type
):
    import json
    from beatprints_api.integrations import apple_music_public
    from beatprints_api.integrations.destinations import apple_music as destination
    from beatprints_api.integrations.region import current_region, use_region

    kind = "song" if item_type == "track" else "album"
    ids = ["12", "13"] if item_type == "track" else ["34", "35"]
    rows = (
        [TRACK, {**TRACK, "trackId": 13, "trackName": "Other"}]
        if item_type == "track"
        else [ALBUM, {**ALBUM, "collectionId": 35, "collectionName": "Other"}]
    )
    items = [
        {
            "contentDescriptor": {
                "kind": kind,
                "identifiers": {"storeAdamID": identifier},
            }
        }
        for identifier in ids
    ]
    items.insert(
        1,
        {
            "contentDescriptor": {
                "kind": "artist",
                "identifiers": {"storeAdamID": "999"},
            }
        },
    )
    html = (
        '<script type="application/json" id="serialized-server-data">'
        + json.dumps(
            {
                "data": [
                    {
                        "intent": {
                            "$kind": "SearchResultsPageIntent",
                            "storefront": "cn",
                            "term": "周杰伦 晴天",
                        },
                        "data": {"sections": [{"items": items}]},
                    }
                ]
            }
        )
        + "</script>"
    )
    seen = []

    class Response:
        text = html

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": list(reversed(rows))}

    def get(url, **kwargs):
        seen.append((url, kwargs.get("params")))
        return Response()

    monkeypatch.setattr(apple_music_public.httpx, "get", get)
    monkeypatch.setattr(
        apple_music,
        "_get",
        lambda url, **kwargs: (
            [] if url == apple_music.SEARCH_URL else list(reversed(rows))
        ),
    )

    def destination_get(url, **kwargs):
        seen.append((url, kwargs.get("params")))
        response = Response()
        if url == destination.SEARCH_URL:
            response.json = lambda: {"results": []}
        return response

    monkeypatch.setattr(destination.http_client, "get", destination_get)
    with use_region("CN"):
        source = apple_music.search("周杰伦 晴天", item_type, 2)
        candidates = destination.search("周杰伦 晴天", item_type)
        assert current_region() == "CN"
    assert [item["id"] for item in source] == ids
    assert [str(item["platform_id"]) for item in candidates] == ids
    assert all("/cn/search" in url for url, _ in seen if "music.apple.com" in url)
    assert any(params == {"id": ",".join(ids), "country": "CN"} for _, params in seen)


def test_public_album_tracklist_is_used_when_lookup_omits_tracks(monkeypatch):
    from beatprints_api.integrations import apple_music_public

    calls = []
    monkeypatch.setattr(apple_music, "_get", lambda *_args, **_kwargs: [ALBUM])
    monkeypatch.setattr(
        apple_music_public,
        "_sections",
        lambda path: calls.append(path)
        or [
            {"id": "track-list - 34", "items": [{"title": "One"}, {"title": "Two"}]},
            {"id": "track-list - 999", "items": [{"title": "Wrong album"}]},
        ],
    )
    album = apple_music.album_metadata("34")
    assert album.tracks == ["One", "Two"]
    assert calls == ["album/34"]


def test_public_catalog_invalid_page_is_an_error_not_empty(monkeypatch):
    from beatprints_api.integrations import apple_music_public

    class Response:
        text = "<html>unexpected page</html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        apple_music_public.httpx, "get", lambda *_args, **_kwargs: Response()
    )
    with pytest.raises(UpstreamError):
        apple_music_public.search_rows("Song", "track", 5, lambda _ids: [])


def test_china_sunny_day_search_resolves_exact_selected_recording(monkeypatch):
    from beatprints_api.integrations import apple_music_public
    from beatprints_api.integrations.region import use_region

    row = {
        **TRACK,
        "trackId": 535824738,
        "collectionId": 535824731,
        "trackName": "晴天",
        "collectionName": "叶惠美",
        "artistName": "周杰伦",
        "trackViewUrl": "https://music.apple.com/cn/album/535824731?i=535824738",
    }
    seen = []

    def get(url, **params):
        seen.append((url, params))
        return [] if url == apple_music.SEARCH_URL else [row]

    monkeypatch.setattr(apple_music, "_get", get)
    monkeypatch.setattr(
        apple_music_public,
        "_sections",
        lambda path, params=None: [
            {
                "items": [
                    {
                        "contentDescriptor": {
                            "kind": "song",
                            "identifiers": {"storeAdamID": "535824738"},
                        }
                    }
                ]
            }
        ],
    )
    with use_region("CN"):
        results = apple_music.search("周杰伦 晴天", "track", 5)
        selected = results[0]
        metadata = apple_music.track_metadata(selected["id"])
    assert (
        selected["provider"],
        selected["id"],
        selected["title"],
        selected["artists"],
    ) == ("apple_music", "535824738", "晴天", ["周杰伦"])
    assert metadata.title == "晴天" and metadata.album == "叶惠美"
    assert seen[-1] == (apple_music.LOOKUP_URL, {"id": "535824738"})


@pytest.mark.parametrize("item_type", ["track", "album"])
@pytest.mark.parametrize(
    "intent",
    [
        {"$kind": "BrowsePageIntent", "storefront": "cn"},
        {
            "$kind": "SearchResultsPageIntent",
            "storefront": "cn",
            "term": "what is love",
        },
        {"$kind": "SearchResultsPageIntent", "storefront": "kr", "term": "dynamite"},
    ],
)
def test_public_search_rejects_wrong_page_storefront_or_term(
    monkeypatch, item_type, intent
):
    import json
    from beatprints_api.integrations import apple_music_public
    from beatprints_api.integrations.region import use_region

    body = {
        "data": [
            {
                "intent": intent,
                "data": {
                    "sections": [
                        {
                            "items": [
                                {
                                    "contentDescriptor": {
                                        "kind": (
                                            "song" if item_type == "track" else "album"
                                        ),
                                        "identifiers": {"storeAdamID": "12"},
                                    }
                                }
                            ]
                        }
                    ]
                },
            }
        ]
    }

    class Response:
        text = '<script id="serialized-server-data">' + json.dumps(body) + "</script>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        apple_music_public.httpx, "get", lambda *_args, **_kwargs: Response()
    )

    def unexpected_lookup(_ids):
        pytest.fail("Unrelated page data must never be looked up as search results")

    with (
        use_region("KR"),
        pytest.raises(UpstreamError, match="unavailable for the selected region"),
    ):
        apple_music_public.search_rows("what is love", item_type, 5, unexpected_lookup)


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_catalog_falls_back_to_public_page_after_itunes_search_error(
    monkeypatch, item_type
):
    from beatprints_api.integrations import apple_music_public
    from beatprints_api.integrations.region import current_region, use_region

    expected_row = TRACK if item_type == "track" else ALBUM
    selected_id = str(
        expected_row["trackId" if item_type == "track" else "collectionId"]
    )
    calls = []

    def get(url, **params):
        calls.append((url, current_region(), params))
        if url == apple_music.SEARCH_URL:
            raise UpstreamError("iTunes search timed out")
        return [expected_row]

    def fallback(query, kind, limit, lookup):
        calls.append(
            ("public", current_region(), {"query": query, "kind": kind, "limit": limit})
        )
        return lookup(selected_id)

    monkeypatch.setattr(apple_music, "_get", get)
    monkeypatch.setattr(apple_music_public, "search_rows", fallback)
    with use_region("KR"):
        results = apple_music.search("what is love", item_type, 5)
    assert [item["id"] for item in results] == [selected_id]
    assert [call[1] for call in calls] == ["KR", "KR", "KR"]
    assert calls[1][2]["query"] == "what is love"


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_destination_falls_back_to_public_page_after_itunes_search_error(
    monkeypatch, item_type
):
    import httpx
    from beatprints_api.integrations import apple_music_public
    from beatprints_api.integrations.destinations import apple_music as destination
    from beatprints_api.integrations.region import current_region, use_region

    row = TRACK if item_type == "track" else ALBUM
    selected_id = str(row["trackId" if item_type == "track" else "collectionId"])
    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [row]}

    def get(url, **params):
        calls.append((url, current_region(), params))
        if url == destination.SEARCH_URL:
            raise httpx.ConnectTimeout("search unavailable")
        return Response()

    def fallback(query, kind, limit, lookup):
        calls.append(
            ("public", current_region(), {"query": query, "kind": kind, "limit": limit})
        )
        return lookup(selected_id)

    monkeypatch.setattr(destination.http_client, "get", get)
    monkeypatch.setattr(apple_music_public, "search_rows", fallback)
    with use_region("KR"):
        results = destination.search("what is love", item_type)
    assert [str(item["platform_id"]) for item in results] == [selected_id]
    assert [call[1] for call in calls] == ["KR", "KR", "KR"]
    assert calls[-1][2]["params"] == {"id": selected_id, "country": "KR"}


def test_search_failure_and_invalid_webpage_remain_an_error(monkeypatch):
    from beatprints_api.integrations import apple_music_public

    monkeypatch.setattr(
        apple_music,
        "_get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(UpstreamError("search failed")),
    )

    def unavailable(*_args, **_kwargs):
        raise UpstreamError(
            "Apple Music search returned a different storefront or query"
        )

    monkeypatch.setattr(apple_music_public, "search_rows", unavailable)
    with pytest.raises(UpstreamError, match="different storefront or query"):
        apple_music.search("what is love", "track", 5)


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_public_search_reports_error_when_ids_cannot_be_resolved(
    monkeypatch, item_type
):
    from beatprints_api.integrations import apple_music_public

    kind = "song" if item_type == "track" else "album"
    monkeypatch.setattr(
        apple_music_public,
        "_sections",
        lambda *_args: [
            {
                "items": [
                    {
                        "contentDescriptor": {
                            "kind": kind,
                            "identifiers": {"storeAdamID": "123"},
                        }
                    }
                ]
            }
        ],
    )
    with pytest.raises(UpstreamError, match="unavailable for the selected region"):
        apple_music_public.search_rows("what is love", item_type, 8, lambda _ids: [])


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_public_search_preserves_genuine_empty_results(monkeypatch, item_type):
    from beatprints_api.integrations import apple_music_public

    monkeypatch.setattr(apple_music_public, "_sections", lambda *_args: [])

    def unexpected_lookup(_ids):
        pytest.fail("No result IDs should require a lookup")

    assert (
        apple_music_public.search_rows(
            "unmatched title", item_type, 8, unexpected_lookup
        )
        == []
    )


@pytest.mark.parametrize("item_type", ["track", "album"])
def test_public_search_keeps_resolvable_results_when_some_ids_are_missing(
    monkeypatch, item_type
):
    from beatprints_api.integrations import apple_music_public

    kind = "song" if item_type == "track" else "album"
    row = TRACK if item_type == "track" else ALBUM
    identifier = str(row["trackId" if item_type == "track" else "collectionId"])
    monkeypatch.setattr(
        apple_music_public,
        "_sections",
        lambda *_args: [
            {
                "items": [
                    {
                        "contentDescriptor": {
                            "kind": kind,
                            "identifiers": {"storeAdamID": value},
                        }
                    }
                    for value in ["999", identifier]
                ]
            }
        ],
    )
    assert apple_music_public.search_rows(
        "what is love", item_type, 8, lambda _ids: [row]
    ) == [row]
