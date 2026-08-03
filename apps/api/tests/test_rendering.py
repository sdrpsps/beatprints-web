from pathlib import Path

import httpx

from BeatPrints.deez import TrackMetadata
from beatprints_api.services import rendering


def test_download_cover_accepts_image_jpg_content_type(
    monkeypatch, tmp_path: Path
) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "image/jpg"},
                content=b"jpeg-content",
            )
        )
    )
    monkeypatch.setattr(rendering, "cover_client", client)
    monkeypatch.setattr(rendering, "_validate_cover_url", lambda _url: None)

    destination = tmp_path / "cover.jpg"
    rendering.download_cover("https://example.com/cover.jpg", destination)

    assert destination.read_bytes() == b"jpeg-content"


def test_rendering_prepares_empty_optional_catalog_text() -> None:
    metadata = TrackMetadata(
        title="Track",
        artists=[],
        album="Album",
        released="",
        duration="03:15",
        cover="https://example.com/cover.jpg",
        label="",
    )

    result = rendering._prepare_metadata_for_rendering(metadata)

    assert result.artists == [" "]
    assert result.released == " "
    assert result.label == " "


def test_right_aligned_text_measures_the_full_mixed_font_line(monkeypatch) -> None:
    calls: list[tuple[tuple[int, int], str, str | None]] = []
    monkeypatch.setattr(
        rendering.write, "text_width", lambda value, _fonts, _size: len(value) * 10
    )
    monkeypatch.setattr(
        rendering.write,
        "text",
        lambda _draw, position, value, *_args, **kwargs: calls.append(
            (position, value, kwargs.get("anchor"))
        ),
    )

    rendering._write_right_aligned_text(
        None,
        (100, 20),
        "2004-12-30\n永稻星娱乐",
        (0, 0, 0),
        {},
        60,
    )

    assert calls == [
        ((0, 20), "2004-12-30", "lt"),
        ((50, 88), "永稻星娱乐", "lt"),
    ]


def test_label_text_size_fits_the_reserved_right_side_width(monkeypatch) -> None:
    monkeypatch.setattr(
        rendering.write, "text_width", lambda value, _fonts, size: len(value) * size
    )

    size = rendering._fitted_text_size("Long label", {}, 60, 400)

    assert size == 40


def test_album_track_layout_keeps_every_track_when_titles_are_wide() -> None:
    tracks = [
        "我亲爱的偏执狂",
        "太聪明",
        "小步舞曲",
        "1234567",
        "随便说说",
        "躺在你的衣柜 (Guitar)",
        "A Practice",
        "吉他手",
        "黑眼圈",
        "就算全世界与我为敌",
        "小尘埃",
        "不应该",
        "躺在你的衣柜 (Piano)",
    ]

    layout = rendering._album_track_layout(tracks, indexing=True)

    assert [track for column in layout.columns for track in column] == [
        f"{number}. {track}" for number, track in enumerate(tracks, start=1)
    ]
    assert (
        sum(layout.widths) + layout.gap * (len(layout.widths) - 1)
        <= rendering.poster.s.MAX_WIDTH
    )
