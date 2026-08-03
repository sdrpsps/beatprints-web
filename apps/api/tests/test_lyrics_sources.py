from beatprints_api.integrations.lyrics.registry import (
    default_lyrics_source,
    lyrics_sources,
)
from beatprints_api.services import lyrics


def test_lyrics_registry_exposes_independent_sources() -> None:
    assert [source.key for source in lyrics_sources()] == ["lrclib"]
    assert default_lyrics_source().key == "lrclib"
    assert lyrics.sources().model_dump() == {
        "sources": [
            {"key": "lrclib", "label": "LRCLIB", "default": True},
        ]
    }
