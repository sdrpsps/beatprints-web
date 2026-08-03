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
            if url == netease.SEARCH_URL
            else "netease_lyrics.json"
        )

    monkeypatch.setattr(netease, "_get_json", get_json)

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
        netease,
        "_get_json",
        lambda url, **_params: (
            fixture("netease_search.json")
            if url == netease.SEARCH_URL
            else {"pureMusic": True, "code": 200}
        ),
    )
    assert netease.fetch(metadata()) == LyricsSourceResult(instrumental=True, lines=())

    monkeypatch.setattr(
        netease,
        "_get_json",
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
            if url == qq_music.SEARCH_URL
            else "qq_music_lyrics.json"
        )

    monkeypatch.setattr(qq_music, "_get_json", get_json)

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
        qq_music,
        "_get_json",
        lambda url, **_params: (
            search
            if url == qq_music.SEARCH_URL
            else {"retcode": 0, "code": 0, "lyric": "[00:01.00]纯音乐"}
        ),
    )
    assert qq_music.fetch(metadata()) == LyricsSourceResult(
        instrumental=True, lines=()
    )

    monkeypatch.setattr(
        qq_music,
        "_get_json",
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

    monkeypatch.setattr(provider.httpx, "get", fail)

    with pytest.raises(UpstreamError, match="request failed") as exc_info:
        provider._get_json("https://example.com")
    assert not isinstance(exc_info.value, LyricsNotFoundError)
