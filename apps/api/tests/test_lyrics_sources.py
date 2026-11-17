import json
from pathlib import Path

import httpx
import pytest
from BeatPrints.deez import TrackMetadata

from beatprints_api.exceptions import (
    LyricsNotFoundError,
    UnsupportedLyricsSourceError,
    UpstreamError,
)
from beatprints_api.integrations.lyrics import netease, qq_music
from beatprints_api.integrations.clients import netease_music as netease_client_module
from beatprints_api.integrations.clients import qq_music as qq_client_module
from beatprints_api.integrations.lyrics.base import (
    LyricsSourceAdapter,
    LyricsSourceResult,
)
from beatprints_api.integrations.lyrics.common import (
    confident_track_match,
    lrc_lines,
    search_title_variants,
)
from beatprints_api.integrations.lyrics.registry import (
    default_lyrics_source,
    get_lyrics_source,
    lyrics_sources,
)

FIXTURES = Path(__file__).parent / "fixtures" / "lyrics"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def metadata() -> TrackMetadata:
    return TrackMetadata(
        title="Fixture Song - Song",
        artists=["Fixture Artist"],
        album="Fixture Album (Album)",
        released="2026-01-01",
        duration="03:15",
        cover="https://example.com/cover.jpg",
        label="Fixture Records",
    )


def test_lyrics_registry_exposes_independent_sources() -> None:
    assert [source.key for source in lyrics_sources()] == [
        "qq_music",
        "netease",
        "lrclib",
    ]
    assert default_lyrics_source().key == "qq_music"

    with pytest.raises(UnsupportedLyricsSourceError):
        get_lyrics_source("disabled-source")


def test_registry_rejects_duplicate_keys(monkeypatch) -> None:
    from beatprints_api.integrations.lyrics import registry

    monkeypatch.setattr(registry, "_adapters", {})
    monkeypatch.setattr(registry, "_default_key", None)
    adapter = LyricsSourceAdapter(
        key="fixture",
        label="Fixture",
        fetch=lambda _metadata: LyricsSourceResult(False, ()),
    )

    registry.register(adapter, default=True)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(adapter)


def test_matching_rejects_version_conflicts_and_accepts_localized_artists() -> None:
    track = metadata()
    assert confident_track_match(
        track,
        title="Fixture Song",
        artists=["本地艺人"],
        album="Fixture Album",
        candidate_duration_seconds=195,
    )
    assert not confident_track_match(
        track,
        title="Fixture Song (Live)",
        artists=["Fixture Artist"],
        album="Fixture Album",
        candidate_duration_seconds=195,
    )
    assert not confident_track_match(
        track,
        title="Fixture Song",
        artists=["Fixture Artist"],
        album="Fixture Album",
        candidate_duration_seconds=215,
    )
    assert search_title_variants("Fixture Song - Song") == (
        "Fixture Song - Song",
        "Fixture Song",
        "Song",
    )


def test_lrc_normalization_removes_metadata_timestamps_and_duplicates() -> None:
    assert lrc_lines(
        "[ar:Artist]\n[by:]\n[sign:]\n[qq:]\n"
        "[00:01.00][00:02.00]Line one\n[00:03.00]Line one\n"
        '{"t":0}\n[00:04.00][Chorus] Line two'
    ) == ("Line one", "[Chorus] Line two")


def test_netease_fetches_confident_original_recording(monkeypatch) -> None:
    requests: list[tuple[str, dict[str, object]]] = []

    def get_json(url: str, **params: object) -> dict:
        requests.append((url, params))
        return fixture(
            "netease_search.json"
            if url == netease_client_module.SEARCH_URL
            else "netease_lyrics.json"
        )

    monkeypatch.setattr(netease.netease_music_client, "_get", get_json)

    assert netease.fetch(metadata()) == LyricsSourceResult(
        instrumental=False,
        lines=(
            "First fixture line",
            "Second fixture line",
            "Third fixture line",
            "Fourth fixture line",
        ),
    )
    assert requests[1][1]["id"] == 102


def test_netease_reports_instrumental_and_no_match(monkeypatch) -> None:
    monkeypatch.setattr(
        netease.netease_music_client,
        "_get",
        lambda url, **_params: (
            fixture("netease_search.json")
            if url == netease_client_module.SEARCH_URL
            else {"pureMusic": True, "code": 200}
        ),
    )
    assert netease.fetch(metadata()) == LyricsSourceResult(instrumental=True, lines=())

    monkeypatch.setattr(
        netease.netease_music_client,
        "_get",
        lambda _url, **_params: {"result": {"songs": []}, "code": 200},
    )
    with pytest.raises(LyricsNotFoundError, match="confident"):
        netease.fetch(metadata())


def test_qq_music_fetches_confident_original_recording(monkeypatch) -> None:
    requests: list[tuple[str, dict[str, object]]] = []

    def get_json(url: str, **params: object) -> dict:
        requests.append((url, params))
        return fixture(
            "qq_music_search.json"
            if url == qq_client_module.SEARCH_URL
            else "qq_music_lyrics.json"
        )

    monkeypatch.setattr(qq_music.qq_music_client, "_get", get_json)

    assert qq_music.fetch(metadata()) == LyricsSourceResult(
        instrumental=False,
        lines=(
            "First fixture line",
            "Second fixture line",
            "Third fixture line",
            "Fourth fixture line",
        ),
    )
    assert requests[1][1]["songmid"] == "studio-mid"
    assert requests[1][1]["nobase64"] == 1


def test_qq_music_reports_instrumental_and_no_match(monkeypatch) -> None:
    search = fixture("qq_music_search.json")
    monkeypatch.setattr(
        qq_music.qq_music_client,
        "_get",
        lambda url, **_params: (
            search
            if url == qq_client_module.SEARCH_URL
            else {"retcode": 0, "code": 0, "lyric": "[00:01.00]纯音乐"}
        ),
    )
    assert qq_music.fetch(metadata()) == LyricsSourceResult(instrumental=True, lines=())

    monkeypatch.setattr(
        qq_music.qq_music_client,
        "_get",
        lambda _url, **_params: {"code": 0, "data": {"song": {"list": []}}},
    )
    with pytest.raises(LyricsNotFoundError, match="confident"):
        qq_music.fetch(metadata())


@pytest.mark.parametrize("provider", [netease, qq_music])
def test_provider_network_failures_are_not_reported_as_no_match(
    monkeypatch, provider
) -> None:
    def fail(*_args, **_kwargs):
        raise httpx.ConnectError("offline")

    client = (
        provider.netease_music_client
        if provider is netease
        else provider.qq_music_client
    )
    monkeypatch.setattr(client.http, "get", fail)

    with pytest.raises(UpstreamError, match="request failed") as exc_info:
        provider.fetch(metadata())
    assert not isinstance(exc_info.value, LyricsNotFoundError)


@pytest.mark.parametrize("count", [0, 1, 3, 4, 5, 8])
def test_default_lyric_selection_uses_first_four_or_reports_too_few(
    monkeypatch, count
) -> None:
    from beatprints_api.models.poster import TrackPosterRequest
    from beatprints_api.services import lyrics as lyrics_service

    lines = tuple(f"Line {index}" for index in range(1, count + 1))
    source = LyricsSourceAdapter(
        key="fixture",
        label="Fixture",
        fetch=lambda _metadata: LyricsSourceResult(False, lines),
    )
    monkeypatch.setattr(lyrics_service, "default_lyrics_source", lambda: source)
    request = TrackPosterRequest(provider="spotify", catalog_id="track-id")

    if count < 4:
        with pytest.raises(UpstreamError, match="Fewer than four"):
            lyrics_service.select(metadata(), request)
    else:
        assert lyrics_service.select(metadata(), request) == "\n".join(lines[:4])


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("1-4", "Line 1\nLine 2\nLine 3\nLine 4"),
        ("3-6", "Line 3\nLine 4\nLine 5\nLine 6"),
    ],
)
def test_explicit_lyric_ranges_select_exactly_four_lines(
    monkeypatch, selection, expected
) -> None:
    from beatprints_api.models.poster import TrackPosterRequest
    from beatprints_api.services import lyrics as lyrics_service

    source = LyricsSourceAdapter(
        key="fixture",
        label="Fixture",
        fetch=lambda _metadata: LyricsSourceResult(
            False, tuple(f"Line {index}" for index in range(1, 8))
        ),
    )
    monkeypatch.setattr(lyrics_service, "default_lyrics_source", lambda: source)
    request = TrackPosterRequest(
        provider="spotify", catalog_id="track-id", lyrics_range=selection
    )
    assert lyrics_service.select(metadata(), request) == expected


@pytest.mark.parametrize("selection", ["1-3", "1-5", "6-9", "4-2"])
def test_invalid_lyric_ranges_do_not_fall_back_to_first_four(
    monkeypatch, selection
) -> None:
    from beatprints_api.models.poster import TrackPosterRequest
    from beatprints_api.services import lyrics as lyrics_service

    source = LyricsSourceAdapter(
        key="fixture",
        label="Fixture",
        fetch=lambda _metadata: LyricsSourceResult(
            False, tuple(f"Line {index}" for index in range(1, 8))
        ),
    )
    monkeypatch.setattr(lyrics_service, "default_lyrics_source", lambda: source)
    request = TrackPosterRequest(
        provider="spotify", catalog_id="track-id", lyrics_range=selection
    )
    with pytest.raises(UpstreamError):
        lyrics_service.select(metadata(), request)


@pytest.mark.parametrize("text", ["", "  One\nTwo  "])
def test_explicit_lyrics_take_precedence_without_fetch(monkeypatch, text) -> None:
    from beatprints_api.models.poster import TrackPosterRequest
    from beatprints_api.services import lyrics as lyrics_service

    def unexpected_source():
        pytest.fail("explicit lyrics must not access a source")

    monkeypatch.setattr(lyrics_service, "default_lyrics_source", unexpected_source)
    request = TrackPosterRequest(
        provider="spotify", catalog_id="track-id", lyrics=text, lyrics_range="1-4"
    )
    assert lyrics_service.select(metadata(), request) == text.strip()


def test_instrumental_selection_uses_custom_text(monkeypatch) -> None:
    from beatprints_api.models.poster import TrackPosterRequest
    from beatprints_api.services import lyrics as lyrics_service

    source = LyricsSourceAdapter(
        key="fixture",
        label="Fixture",
        fetch=lambda _metadata: LyricsSourceResult(True, ()),
    )
    monkeypatch.setattr(lyrics_service, "default_lyrics_source", lambda: source)
    request = TrackPosterRequest(
        provider="spotify", catalog_id="track-id", instrumental_text="  Instrumental  "
    )
    assert lyrics_service.select(metadata(), request) == "Instrumental"
