import subprocess
import sys

import pytest

from BeatPrints.deez import AlbumMetadata, TrackMetadata
from beatprints_api.integrations.catalog import netease_music as netease_catalog
from beatprints_api.integrations.catalog import qq_music as qq_catalog
from beatprints_api.integrations.destinations import (
    netease_music,
    qq_music,
    spotify as spotify_destination,
)
from beatprints_api.integrations.destinations.registry import (
    destination_keys,
    get_destination_adapter,
)
from beatprints_api.integrations.catalog.registry import (
    catalog_adapters,
    get_catalog_adapter,
)
from beatprints_api.integrations.labels import registry as label_registry
from beatprints_api.integrations.labels.base import LabelResolver
from beatprints_api.models.destinations import PlatformLinkMatchData
from beatprints_api.exceptions import (
    UnsupportedCatalogSourceError,
    UnsupportedDestinationError,
)
from beatprints_api.integrations.destinations.base import DestinationAdapter
from beatprints_api.services import matching as matching_service


def album_metadata() -> AlbumMetadata:
    return AlbumMetadata(
        title="Summer Breeze",
        artists=["PIPER"],
        released="1983-01-01",
        tracks=[f"Track {index}" for index in range(10)],
        cover="https://example.com/cover.jpg",
        label="Yupiteru Records",
    )


def test_enabled_destinations_are_registered_independently() -> None:
    assert destination_keys() == (
        "spotify",
        "apple_music",
        "qq_music",
        "netease_music",
    )
    for key in destination_keys():
        adapter = get_destination_adapter(key)
        assert adapter.key == key
        assert adapter.search and adapter.resolve and adapter.scannable

    with pytest.raises(UnsupportedDestinationError):
        get_destination_adapter("disabled_destination")


def test_destination_registry_does_not_load_catalog_adapters() -> None:
    script = """
import sys
from beatprints_api.integrations.destinations.registry import destination_keys

assert "spotify" in destination_keys()
assert "beatprints_api.integrations.catalog.registry" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", script], check=True)


def test_empty_track_label_uses_a_registered_resolver(monkeypatch) -> None:
    metadata = TrackMetadata(
        title="Track",
        artists=["Artist"],
        album="Album",
        released="2025-01-01",
        duration="03:15",
        cover="https://example.com/cover.jpg",
        label="",
    )
    resolver = LabelResolver(
        key="fixture",
        configured=lambda: True,
        resolve_track=lambda _metadata: "Fixture Records",
    )
    monkeypatch.setattr(label_registry, "label_resolvers", lambda: (resolver,))

    result = matching_service.catalog_service._enrich_missing_track_label(metadata)

    assert result.label == "Fixture Records"


def test_source_catalogs_are_registered_independently() -> None:
    assert [adapter.key for adapter in catalog_adapters()] == [
        "qq_music",
        "netease_music",
        "spotify",
    ]
    for adapter in catalog_adapters():
        assert adapter.search and adapter.track_metadata and adapter.album_metadata
        assert get_catalog_adapter(adapter.key) is adapter

    with pytest.raises(UnsupportedCatalogSourceError):
        get_catalog_adapter("deezer")


@pytest.mark.parametrize(
    ("adapter", "provider"),
    [
        (spotify_destination.adapter, "spotify"),
        (qq_music.adapter, "qq_music"),
        (netease_music.adapter, "netease_music"),
    ],
)
def test_destination_plugins_reuse_only_their_own_catalog_links(
    adapter, provider: str
) -> None:
    assert adapter.reuses_source_link(provider)
    assert not adapter.reuses_source_link("another_source")


@pytest.mark.parametrize(
    ("destination", "provider"),
    [
        (qq_music, "qq_music"),
        (netease_music, "netease_music"),
    ],
)
def test_same_source_destination_resolves_its_canonical_link(
    monkeypatch, destination, provider: str
) -> None:
    expected = PlatformLinkMatchData(
        url="https://example.com/track/current",
        title="Current Track",
        artists=["Current Artist"],
        type="track",
    )
    seen: list[str] = []

    def resolve(url: str) -> PlatformLinkMatchData:
        seen.append(url)
        return expected

    monkeypatch.setattr(destination, "resolve", resolve)

    result = matching_service.platform_match_options(
        provider, "catalog-id", "track", destination.adapter.key
    )

    assert result.match == expected
    assert result.candidates == [expected]
    assert seen


@pytest.mark.parametrize(
    ("adapter", "expected_url"),
    [
        (qq_catalog, qq_catalog.SEARCH_URL),
        (netease_catalog, netease_catalog.SEARCH_URL),
    ],
)
def test_catalog_sources_normalize_track_search_results(
    monkeypatch, adapter, expected_url
) -> None:
    seen: list[str] = []

    def get(url: str, **_params: object) -> dict:
        seen.append(url)
        if adapter is qq_catalog:
            return {
                "data": {
                    "song": {
                        "list": [
                            {
                                "songmid": "qq-track",
                                "songname": "QQ Track",
                                "singer": [{"name": "QQ Artist"}],
                                "albummid": "qq-album",
                                "albumname": "QQ Album",
                                "interval": 195,
                                "pubtime": "2020-05-24",
                            }
                        ]
                    }
                }
            }
        if url == netease_catalog.TRACK_URL:
            return {
                "songs": [
                    {
                        "id": 163001,
                        "name": "NetEase Track",
                        "artists": [{"name": "NetEase Artist"}],
                        "duration": 195000,
                        "album": {
                            "id": 163002,
                            "name": "NetEase Album",
                            "picUrl": "https://example.com/cover.jpg",
                            "publishTime": 1_590_249_600_000,
                        },
                    }
                ]
            }
        return {
            "result": {
                "songs": [
                    {
                        "id": 163001,
                        "name": "NetEase Track",
                        "artists": [{"name": "NetEase Artist"}],
                        "duration": 195000,
                        "album": {
                            "id": 163002,
                            "name": "NetEase Album",
                            "picUrl": "https://example.com/cover.jpg",
                            "publishTime": 1_590_249_600_000,
                        },
                    }
                ]
            }
        }

    monkeypatch.setattr(adapter, "_get", get)

    result = adapter.search("track", "track", 5)

    assert seen[0] == expected_url
    if adapter is netease_catalog:
        assert seen[1] == netease_catalog.TRACK_URL
    assert result[0]["provider"] == adapter.adapter.key
    assert result[0]["duration"] == "03:15"
    assert result[0]["album"]["title"].endswith("Album")


def test_qq_catalog_normalizes_current_track_metadata(monkeypatch) -> None:
    def get(url: str, **_params: object) -> dict:
        if url == qq_catalog.ALBUM_URL:
            return {"data": {"company": "QQ Records"}}
        return {
            "data": [
                {
                    "mid": "qq-track",
                    "title": "QQ Track",
                    "singer": [{"name": "QQ Artist"}],
                    "album": {"mid": "qq-album", "name": "QQ Album"},
                    "interval": 195,
                    "time_public": "2020-05-24",
                }
            ]
        }

    monkeypatch.setattr(
        qq_catalog,
        "_get",
        get,
    )

    metadata = qq_catalog.track_metadata("qq-track")

    assert metadata.title == "QQ Track"
    assert metadata.album == "QQ Album"
    assert metadata.label == "QQ Records"
    assert metadata.link.endswith("/qq-track")


def test_qq_catalog_reads_current_album_track_names(monkeypatch) -> None:
    monkeypatch.setattr(
        qq_catalog,
        "_get",
        lambda _url, **_params: {
            "data": {
                "mid": "qq-album",
                "name": "QQ Album",
                "singername": "QQ Artist",
                "company_new": {"name": "QQ Records"},
                "aDate": "2020-05-24",
                "list": [{"songname": "First Track"}, {"songname": "Second Track"}],
            }
        },
    )

    metadata = qq_catalog.album_metadata("qq-album")

    assert metadata.artists == ["QQ Artist"]
    assert metadata.tracks == ["First Track", "Second Track"]
    assert metadata.label == "QQ Records"


def test_netease_catalog_reads_track_label_from_its_album(monkeypatch) -> None:
    monkeypatch.setattr(
        netease_catalog,
        "_get",
        lambda _url, **_params: {
            "songs": [
                {
                    "id": 163001,
                    "name": "NetEase Track",
                    "artists": [{"name": "NetEase Artist"}],
                    "duration": 195000,
                    "album": {
                        "id": 163002,
                        "name": "NetEase Album",
                        "picUrl": "https://example.com/cover.jpg",
                        "publishTime": 1_590_249_600_000,
                        "company": "NetEase Records",
                    },
                }
            ]
        },
    )

    metadata = netease_catalog.track_metadata("163001")

    assert metadata.label == "NetEase Records"


def test_qq_cover_urls_are_upgraded_to_https() -> None:
    assert (
        qq_music._secure_url("http://y.gtimg.cn/cover.jpg")
        == "https://y.gtimg.cn/cover.jpg"
    )


def test_catalog_year_supports_seconds_milliseconds_and_missing_values() -> None:
    assert qq_music._year(1_590_249_600) == 2020
    assert qq_music._year(1_590_249_600_000) == 2020
    assert qq_music._year("2020-05-24") == 2020
    assert qq_music._year(0) is None


def test_version_markers_do_not_match_inside_words() -> None:
    assert matching_service._catalog_title_parts("Olive")[1] == frozenset()
    assert matching_service._catalog_title_parts("Demons")[1] == frozenset()
    assert matching_service._catalog_title_parts("Song (Live)")[1] == frozenset(
        {"live"}
    )
    assert matching_service._catalog_title_parts("歌曲（现场版）")[1] == frozenset(
        {"现场版"}
    )


def test_artist_comparison_ignores_collaborator_order() -> None:
    score, state = matching_service._artist_comparison(
        ["Artist A", "Artist B"], ["Artist B", "Artist A"]
    )
    assert score == 1.0
    assert state == "matched"


def test_qq_link_parser_rejects_lookalike_host() -> None:
    assert qq_music._id_from_url("https://example.com/songDetail/track-id") is None


def test_netease_search_treats_malformed_result_as_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        netease_music,
        "_get",
        lambda _url, **_params: {"result": "upstream returned no result object"},
    )

    assert netease_music.search("missing", "track") == []


def test_netease_search_uses_plain_catalog_endpoint(monkeypatch) -> None:
    seen: dict[str, str] = {}

    def get(url: str, **_params: object) -> dict:
        seen["url"] = url
        return {"result": {"songs": []}}

    monkeypatch.setattr(netease_music, "_get", get)

    assert netease_music.search("KUN", "track") == []
    assert seen["url"] == "https://music.163.com/api/search/get"


def test_qq_album_resolve_returns_current_artist_and_total(monkeypatch) -> None:
    monkeypatch.setattr(
        qq_music,
        "_get",
        lambda _url, **_params: {
            "data": {
                "name": "サマー・ブリーズ",
                "singername": "パイパー",
                "aDate": "1983-05-01",
                "total_song_num": 10,
                "list": [{"title": "Track"}],
            }
        },
    )

    result = qq_music.resolve("https://y.qq.com/n/ryqq/albumDetail/002GS7yr33XVbv")

    assert result.artists == ["パイパー"]
    assert result.track_count == 10


@pytest.mark.parametrize("platform", ["qq_music", "netease_music"])
def test_localized_album_is_found_by_title_fallback(monkeypatch, platform: str) -> None:
    candidate = {
        "title": (
            "SUMMER BREEZE (サマー・ブリーズ)"
            if platform == "qq_music"
            else "SUMMER BREEZE"
        ),
        "artists": ["パイパー" if platform == "qq_music" else "パイパー"],
        "release_year": 1983,
        "track_count": 10,
        "cover_url": "https://example.com/cover.jpg",
        "url": "https://example.com/album/1",
    }
    monkeypatch.setattr(
        matching_service, "_album_metadata", lambda _request: album_metadata()
    )
    monkeypatch.setattr(
        matching_service,
        "_destination_adapter",
        lambda _platform: DestinationAdapter(
            search=lambda query, item_type: (
                [dict(candidate, type=item_type)]
                if query in {"Summer Breeze", "PIPER"}
                else []
            ),
            resolve=lambda _url: None,
        ),
    )

    result = matching_service.platform_match_options(
        "spotify", "album-id", "album", platform
    )
    match = result.match

    assert match is not None
    assert match.title.startswith("SUMMER BREEZE")
    assert match.release_year == 1983


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"release_year": 1984}, False),
        ({"track_count": 9}, False),
        ({"title": "Summer Breeze (Live)"}, False),
        ({"artists": ["Tobu"]}, False),
    ],
)
def test_album_match_rejects_conflicting_release_evidence(
    changes: dict, expected: bool
) -> None:
    candidate = {
        "title": "SUMMER BREEZE",
        "artists": ["パイパー"],
        "release_year": 1983,
        "track_count": 10,
        **changes,
    }

    assert (
        not matching_service._has_hard_conflict(album_metadata(), candidate, "album")
    ) is expected


def test_localized_track_requires_duration_year_and_album() -> None:
    metadata = TrackMetadata(
        title="Summer Breeze",
        artists=["PIPER"],
        album="Summer Breeze",
        released="1983-01-01",
        duration="04:20",
        cover="https://example.com/cover.jpg",
        label="Yupiteru Records",
    )
    candidate = {
        "title": "SUMMER BREEZE",
        "artists": ["パイパー"],
        "album": "SUMMER BREEZE",
        "release_year": 1983,
        "duration_seconds": 260,
    }

    assert not matching_service._has_hard_conflict(metadata, candidate, "track")
    assert matching_service._has_hard_conflict(
        metadata, {**candidate, "duration_seconds": 280}, "track"
    )


def test_bilingual_track_matches_localized_catalog_candidate() -> None:
    metadata = TrackMetadata(
        title="情人 - Lover",
        artists=["KUN"],
        album="情人 (Lover)",
        released="2020-05-24",
        duration="03:15",
        cover="https://example.com/cover.jpg",
        label="",
    )
    candidate = {
        "title": "情人",
        "artists": ["蔡徐坤"],
        "album": "情人",
        "release_year": 2020,
        "duration_seconds": 195,
    }

    assert not matching_service._has_hard_conflict(metadata, candidate, "track")


def test_cross_script_artist_search_prefers_original_over_same_name_cover(
    monkeypatch,
) -> None:
    metadata = TrackMetadata(
        title="情人 - Lover",
        artists=["KUN"],
        album="情人 (Lover)",
        released="2020-05-24",
        duration="03:15",
        cover="https://example.com/cover.jpg",
        label="",
    )
    cover = {
        "title": "情人",
        "artists": ["野生三十"],
        "album": "情人 (Be My Lover)",
        "release_year": 2020,
        "duration_seconds": 195,
        "url": "https://example.com/cover",
    }
    original = {
        "title": "情人",
        "artists": ["蔡徐坤"],
        "album": "情人",
        "release_year": 2020,
        "duration_seconds": 195,
        "url": "https://example.com/original",
    }
    monkeypatch.setattr(
        matching_service, "_track_metadata", lambda _request: metadata
    )
    monkeypatch.setattr(
        matching_service,
        "_destination_adapter",
        lambda _platform: DestinationAdapter(
            search=lambda query, item_type: (
                [dict(original, type=item_type)]
                if query == "KUN"
                else [dict(cover, type=item_type)]
            ),
            resolve=lambda _url: None,
        ),
    )

    result = matching_service.platform_match_options(
        "spotify", "track-id", "track", "netease_music"
    )
    match = result.match

    assert match is not None
    assert str(match.url) == original["url"]
    assert match.artists == ["蔡徐坤"]


@pytest.mark.parametrize(
    "platform",
    ["spotify", "apple_music", "qq_music", "netease_music"],
)
def test_candidate_search_ranks_artist_result_above_same_name_cover(
    monkeypatch,
    platform: str,
) -> None:
    metadata = TrackMetadata(
        title="情人 - Lover",
        artists=["KUN"],
        album="情人 (Lover)",
        released="2020-05-24",
        duration="03:15",
        cover="https://example.com/cover.jpg",
        label="",
    )
    cover = {
        "title": "情人",
        "artists": ["野生三十"],
        "album": "情人 (Be My Lover)",
        "release_year": 2020,
        "duration_seconds": 195,
        "url": "https://example.com/cover",
        "type": "track",
    }
    original = {
        "title": "情人",
        "artists": ["蔡徐坤"],
        "album": "情人",
        "release_year": 2020,
        "duration_seconds": 195,
        "url": "https://example.com/original",
        "type": "track",
    }
    monkeypatch.setattr(
        matching_service, "_track_metadata", lambda _request: metadata
    )
    monkeypatch.setattr(
        matching_service,
        "_destination_adapter",
        lambda _platform: DestinationAdapter(
            search=lambda query, _item_type: [original] if query == "KUN" else [cover],
            resolve=lambda _url: None,
        ),
    )
    monkeypatch.setattr(matching_service, "_source_isrc", lambda *_args: None)

    matches = matching_service.platform_match_options(
        "deezer", "track-id", "track", platform
    ).candidates

    assert str(matches[0].url) == original["url"]
    assert {str(match.url) for match in matches} == {
        original["url"],
        cover["url"],
    }


def test_album_candidates_rank_exact_track_count_first(monkeypatch) -> None:
    matching = {
        "title": "Summer Breeze",
        "artists": ["PIPER"],
        "release_year": 1983,
        "track_count": 10,
        "url": "https://example.com/matching",
        "type": "album",
    }
    short_edition = {
        **matching,
        "track_count": 8,
        "url": "https://example.com/short",
    }
    monkeypatch.setattr(
        matching_service, "_album_metadata", lambda _request: album_metadata()
    )
    monkeypatch.setattr(
        matching_service,
        "_destination_adapter",
        lambda _platform: DestinationAdapter(
            search=lambda _query, _item_type: [short_edition, matching],
            resolve=lambda _url: None,
        ),
    )

    matches = matching_service.platform_match_options(
        "deezer", "album-id", "album", "apple_music"
    ).candidates

    assert str(matches[0].url) == matching["url"]


def test_album_candidates_include_catalog_title_suffix_without_auto_matching(
    monkeypatch,
) -> None:
    metadata = AlbumMetadata(
        title="Groupies吉他手",
        artists=["陈绮贞"],
        released="2002-08-01",
        tracks=[f"Track {index}" for index in range(13)],
        cover="https://example.com/cover.jpg",
        label="",
    )
    candidate = {
        "title": "吉他手",
        "artists": ["Cheer Chen"],
        "release_year": 2002,
        "track_count": 13,
        "url": "https://open.spotify.com/album/35QdFULbzmzRWMeH7bHGQR",
        "type": "album",
    }
    monkeypatch.setattr(
        matching_service, "_album_metadata", lambda _request: metadata
    )
    monkeypatch.setattr(
        matching_service,
        "_destination_adapter",
        lambda _platform: DestinationAdapter(
            search=lambda _query, _item_type: [candidate], resolve=lambda _url: None
        ),
    )

    result = matching_service.platform_match_options(
        "netease_music", "21302", "album", "spotify"
    )

    assert result.match is None
    assert [str(match.url) for match in result.candidates] == [candidate["url"]]


def test_candidate_search_skips_empty_artist_queries(monkeypatch) -> None:
    metadata = AlbumMetadata(
        title="Groupies 吉他手",
        artists=[],
        released="2002-08-05",
        tracks=[f"Track {index}" for index in range(13)],
        cover="https://example.com/cover.jpg",
        label="",
    )
    queries: list[str] = []
    monkeypatch.setattr(
        matching_service, "_album_metadata", lambda _request: metadata
    )
    monkeypatch.setattr(
        matching_service,
        "_destination_adapter",
        lambda _platform: DestinationAdapter(
            search=lambda query, _item_type: queries.append(query) or [],
            resolve=lambda _url: None,
        ),
    )

    matching_service.platform_match_options(
        "qq_music", "000zebjW3TlPWh", "album", "spotify"
    )

    assert queries == ["Groupies 吉他手"]


def test_close_top_candidates_require_user_confirmation(monkeypatch) -> None:
    first = {
        "title": "Summer Breeze",
        "artists": ["PIPER"],
        "release_year": 1983,
        "track_count": 10,
        "url": "https://example.com/first",
        "type": "album",
    }
    second = {**first, "url": "https://example.com/second"}
    monkeypatch.setattr(
        matching_service, "_album_metadata", lambda _request: album_metadata()
    )
    monkeypatch.setattr(
        matching_service,
        "_destination_adapter",
        lambda _platform: DestinationAdapter(
            search=lambda _query, _item_type: [first, second], resolve=lambda _url: None
        ),
    )

    result = matching_service.platform_match_options(
        "deezer", "album-id", "album", "apple_music"
    )

    assert result.match is None
    assert len(result.candidates) == 2


def test_exact_isrc_overrides_localized_display_text(monkeypatch) -> None:
    metadata = TrackMetadata(
        title="Localized source title",
        artists=["Source Artist"],
        album="Source Album",
        released="2020-01-01",
        duration="03:15",
        cover="https://example.com/cover.jpg",
        label="",
    )
    candidate = {
        "title": "完全不同的显示名称",
        "artists": ["本地艺人名"],
        "album": "本地专辑名",
        "duration_seconds": 195,
        "isrc": "US-EXAMPLE-01",
        "url": "https://example.com/exact",
        "type": "track",
    }
    monkeypatch.setattr(
        matching_service, "_track_metadata", lambda _request: metadata
    )
    monkeypatch.setattr(
        matching_service, "_source_isrc", lambda *_args: "US-EXAMPLE-01"
    )
    monkeypatch.setattr(
        matching_service,
        "_destination_adapter",
        lambda _platform: DestinationAdapter(
            search=lambda query, _item_type: (
                [candidate] if query.startswith("isrc:") else []
            ),
            resolve=lambda _url: None,
            supports_isrc=True,
        ),
    )

    result = matching_service.platform_match_options(
        "deezer", "track-id", "track", "spotify"
    )

    assert result.match is not None
    assert str(result.match.url) == candidate["url"]
