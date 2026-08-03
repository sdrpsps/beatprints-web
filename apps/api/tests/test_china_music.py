import pytest

from BeatPrints.deez import AlbumMetadata, TrackMetadata
from beatprints_api.services.beatprints import DestinationAdapter

from beatprints_api.services import beatprints as beatprints_service
from beatprints_api import china_music


def album_metadata() -> AlbumMetadata:
    return AlbumMetadata(
        title="Summer Breeze",
        artists=["PIPER"],
        released="1983-01-01",
        tracks=[f"Track {index}" for index in range(10)],
        cover="https://example.com/cover.jpg",
        label="Yupiteru Records",
    )


def test_qq_cover_urls_are_upgraded_to_https() -> None:
    assert china_music._secure_url("http://y.gtimg.cn/cover.jpg") == "https://y.gtimg.cn/cover.jpg"


def test_catalog_year_supports_seconds_milliseconds_and_missing_values() -> None:
    assert china_music._year(1_590_249_600) == 2020
    assert china_music._year(1_590_249_600_000) == 2020
    assert china_music._year("2020-05-24") == 2020
    assert china_music._year(0) is None


def test_version_markers_do_not_match_inside_words() -> None:
    assert beatprints_service._catalog_title_parts("Olive")[1] == frozenset()
    assert beatprints_service._catalog_title_parts("Demons")[1] == frozenset()
    assert beatprints_service._catalog_title_parts("Song (Live)")[1] == frozenset({"live"})
    assert beatprints_service._catalog_title_parts("歌曲（现场版）")[1] == frozenset({"现场版"})


def test_artist_comparison_ignores_collaborator_order() -> None:
    score, state = beatprints_service._artist_comparison(
        ["Artist A", "Artist B"], ["Artist B", "Artist A"]
    )
    assert score == 1.0
    assert state == "matched"


def test_qq_link_parser_rejects_lookalike_host() -> None:
    assert china_music._id_from_url(
        "https://example.com/songDetail/track-id", "qq_music"
    ) is None


def test_netease_search_treats_malformed_result_as_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        china_music,
        "_get",
        lambda _url, **_params: {"result": "upstream returned no result object"},
    )

    assert china_music.netease_search("missing", "track") == []


def test_netease_search_uses_plain_catalog_endpoint(monkeypatch) -> None:
    seen: dict[str, str] = {}

    def get(url: str, **_params: object) -> dict:
        seen["url"] = url
        return {"result": {"songs": []}}

    monkeypatch.setattr(china_music, "_get", get)

    assert china_music.netease_search("KUN", "track") == []
    assert seen["url"] == "https://music.163.com/api/search/get"


def test_qq_album_resolve_returns_current_artist_and_total(monkeypatch) -> None:
    monkeypatch.setattr(
        china_music,
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

    result = china_music.qq_resolve(
        "https://y.qq.com/n/ryqq/albumDetail/002GS7yr33XVbv"
    )

    assert result["artists"] == ["パイパー"]
    assert result["track_count"] == 10


@pytest.mark.parametrize("platform", ["qq_music", "netease_music"])
def test_localized_album_is_found_by_title_fallback(monkeypatch, platform: str) -> None:
    candidate = {
        "title": "SUMMER BREEZE (サマー・ブリーズ)" if platform == "qq_music" else "SUMMER BREEZE",
        "artists": ["パイパー" if platform == "qq_music" else "パイパー"],
        "release_year": 1983,
        "track_count": 10,
        "cover_url": "https://example.com/cover.jpg",
        "url": "https://example.com/album/1",
    }
    search = beatprints_service.china_music.qq_search if platform == "qq_music" else beatprints_service.china_music.netease_search
    monkeypatch.setattr(beatprints_service, "_album_metadata", lambda _request: album_metadata())
    monkeypatch.setattr(
        beatprints_service.china_music,
        "qq_search" if platform == "qq_music" else "netease_search",
        lambda query, _item_type: (
            [candidate] if query in {"Summer Breeze", "PIPER"} else []
        ),
    )

    result = beatprints_service.platform_match_options(
        "spotify", "album-id", "album", platform
    )
    match = result.match

    assert match is not None
    assert match.title.startswith("SUMMER BREEZE")
    assert match.release_year == 1983
    assert search is not None


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"release_year": 1984}, False),
        ({"track_count": 9}, False),
        ({"title": "Summer Breeze (Live)"}, False),
        ({"artists": ["Tobu"]}, False),
    ],
)
def test_album_match_rejects_conflicting_release_evidence(changes: dict, expected: bool) -> None:
    candidate = {
        "title": "SUMMER BREEZE",
        "artists": ["パイパー"],
        "release_year": 1983,
        "track_count": 10,
        **changes,
    }

    assert (
        not beatprints_service._has_hard_conflict(
            album_metadata(), candidate, "album"
        )
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

    assert not beatprints_service._has_hard_conflict(metadata, candidate, "track")
    assert beatprints_service._has_hard_conflict(
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

    assert not beatprints_service._has_hard_conflict(metadata, candidate, "track")


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
        beatprints_service, "_track_metadata", lambda _request: metadata
    )
    monkeypatch.setattr(
        beatprints_service.china_music,
        "netease_search",
        lambda query, _item_type: [original] if query == "KUN" else [cover],
    )

    result = beatprints_service.platform_match_options(
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
        beatprints_service, "_track_metadata", lambda _request: metadata
    )
    monkeypatch.setattr(beatprints_service, "_destination_adapter", lambda _platform: DestinationAdapter(search=lambda query, _item_type: [original] if query == "KUN" else [cover], resolve=lambda _url: None))
    monkeypatch.setattr(beatprints_service, "_source_isrc", lambda *_args: None)

    matches = beatprints_service.platform_match_options(
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
        beatprints_service, "_album_metadata", lambda _request: album_metadata()
    )
    monkeypatch.setattr(beatprints_service, "_destination_adapter", lambda _platform: DestinationAdapter(search=lambda _query, _item_type: [short_edition, matching], resolve=lambda _url: None))

    matches = beatprints_service.platform_match_options(
        "deezer", "album-id", "album", "apple_music"
    ).candidates

    assert str(matches[0].url) == matching["url"]


def test_close_top_candidates_require_user_confirmation(monkeypatch) -> None:
    first = {
        "title": "Summer Breeze", "artists": ["PIPER"],
        "release_year": 1983, "track_count": 10,
        "url": "https://example.com/first", "type": "album",
    }
    second = {**first, "url": "https://example.com/second"}
    monkeypatch.setattr(
        beatprints_service, "_album_metadata", lambda _request: album_metadata()
    )
    monkeypatch.setattr(beatprints_service, "_destination_adapter", lambda _platform: DestinationAdapter(search=lambda _query, _item_type: [first, second], resolve=lambda _url: None))

    result = beatprints_service.platform_match_options(
        "deezer", "album-id", "album", "apple_music"
    )

    assert result.match is None
    assert len(result.candidates) == 2


def test_exact_isrc_overrides_localized_display_text(monkeypatch) -> None:
    metadata = TrackMetadata(
        title="Localized source title", artists=["Source Artist"],
        album="Source Album", released="2020-01-01", duration="03:15",
        cover="https://example.com/cover.jpg", label="",
    )
    candidate = {
        "title": "完全不同的显示名称", "artists": ["本地艺人名"],
        "album": "本地专辑名", "duration_seconds": 195,
        "isrc": "US-EXAMPLE-01", "url": "https://example.com/exact",
        "type": "track",
    }
    monkeypatch.setattr(beatprints_service, "_track_metadata", lambda _request: metadata)
    monkeypatch.setattr(
        beatprints_service, "_source_isrc", lambda *_args: "US-EXAMPLE-01"
    )
    monkeypatch.setattr(beatprints_service, "_destination_adapter", lambda _platform: DestinationAdapter(search=lambda query, _item_type: [candidate] if query.startswith("isrc:") else [], resolve=lambda _url: None, supports_isrc=True))

    result = beatprints_service.platform_match_options(
        "deezer", "track-id", "track", "spotify"
    )

    assert result.match is not None
    assert str(result.match.url) == candidate["url"]
