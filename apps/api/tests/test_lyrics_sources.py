from BeatPrints.deez import TrackMetadata
import pytest

from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.lyrics import lrcapi
from beatprints_api.integrations.lyrics.registry import (
    default_lyrics_source,
    lyrics_sources,
)
from beatprints_api.services import lyrics


def metadata() -> TrackMetadata:
    return TrackMetadata(
        title="A Bright Song",
        artists=["The Artist"],
        album="A Bright Album",
        released="2024-01-01",
        duration="03:30",
        cover="https://example.com/cover.jpg",
        label="Example Records",
    )


def test_lyrics_registry_exposes_independent_sources() -> None:
    assert [source.key for source in lyrics_sources()] == ["lrcapi", "lrclib"]
    assert default_lyrics_source().key == "lrclib"
    assert lyrics.sources().model_dump() == {
        "sources": [
            {"key": "lrcapi", "label": "LrcApi", "default": False},
            {"key": "lrclib", "label": "LRCLIB", "default": True},
        ]
    }


def test_lrcapi_normalizes_timestamped_lines_after_a_strict_match(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return [
                {
                    "title": "A Bright Song",
                    "artist": "The Artist",
                    "lrc": "[ar:The Artist]\n[00:01.20]First line\n[00:04.00][00:05.00]Second line",
                }
            ]

    monkeypatch.setattr(lrcapi._http, "get", lambda *_args, **_kwargs: Response())

    result = lrcapi.fetch(metadata())

    assert result.instrumental is False
    assert result.lines == ("First line", "Second line")


def test_lrcapi_rejects_a_same_title_by_another_artist(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return [
                {
                    "title": "A Bright Song",
                    "artist": "Another Artist",
                    "lrc": "[00:01.00]Unrelated line",
                }
            ]

    monkeypatch.setattr(lrcapi._http, "get", lambda *_args, **_kwargs: Response())

    with pytest.raises(UpstreamError, match="No confident lyrics result"):
        lrcapi.fetch(metadata())
