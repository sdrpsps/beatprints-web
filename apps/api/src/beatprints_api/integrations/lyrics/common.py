"""Shared matching and LRC normalization for lyrics source adapters."""

import re
import unicodedata

from BeatPrints import deez

_TIMESTAMP = re.compile(r"\[\d{1,3}:\d{2}(?:[.:]\d{1,3})?\]")
_METADATA = re.compile(r"^\[[A-Za-z]{1,12}:.*\]\s*$")
_TRAILING_PARENS = re.compile(r"\s*[（(][^()（）]*[）)]\s*$")
_TITLE_SEPARATOR = re.compile(r"\s+[-–—]\s+")
_VERSION_MARKERS = (
    "live",
    "remix",
    "remaster",
    "remastered",
    "acoustic",
    "instrumental",
    "karaoke",
    "radio edit",
    "demo",
    "现场版",
    "現場版",
    "重制版",
    "重製版",
    "伴奏",
    "纯音乐",
    "純音樂",
    "混音",
)


def normalized(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(character for character in text if character.isalnum())


def duration_seconds(value: object) -> int | None:
    try:
        minutes, seconds = str(value).split(":", maxsplit=1)
        return int(minutes) * 60 + int(seconds)
    except TypeError, ValueError:
        return None


def _versions(value: object) -> frozenset[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return frozenset(
        marker
        for marker in _VERSION_MARKERS
        if (
            marker in text
            if any(ord(character) > 127 for character in marker)
            else re.search(rf"(?<![a-z]){re.escape(marker)}(?![a-z])", text)
        )
    )


def _title_aliases(value: object) -> frozenset[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    base = _TRAILING_PARENS.sub("", text).strip()
    return frozenset(
        alias
        for variant in (text, base)
        for part in _TITLE_SEPARATOR.split(variant)
        if (alias := normalized(part))
    )


def search_title_variants(value: object) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    base = _TRAILING_PARENS.sub("", text).strip()
    variants: list[str] = []
    for candidate in (text, *_TITLE_SEPARATOR.split(text), base):
        candidate = candidate.strip()
        if candidate and candidate not in variants:
            variants.append(candidate)
    return tuple(variants)


def titles_match(left: object, right: object) -> bool:
    return bool(_title_aliases(left) & _title_aliases(right)) and _versions(
        left
    ) == _versions(right)


def _artists_match(source: list[str], candidate: list[str]) -> bool:
    source_names = {normalized(value) for value in source if normalized(value)}
    candidate_names = {normalized(value) for value in candidate if normalized(value)}
    return bool(source_names & candidate_names)


def confident_track_match(
    metadata: deez.TrackMetadata,
    *,
    title: object,
    artists: list[str],
    album: object,
    candidate_duration_seconds: int | None,
    tolerance_seconds: int = 3,
) -> bool:
    target_duration = duration_seconds(metadata.duration)
    if target_duration is None or candidate_duration_seconds is None:
        return False
    if abs(target_duration - candidate_duration_seconds) > tolerance_seconds:
        return False
    if not titles_match(metadata.title, title):
        return False
    return _artists_match(metadata.artists, artists) or titles_match(
        metadata.album, album
    )


def lrc_lines(value: object) -> tuple[str, ...]:
    lines: list[str] = []
    for raw_line in str(value or "").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("{") or _METADATA.fullmatch(stripped):
            continue
        line = _TIMESTAMP.sub("", stripped).strip()
        if line and (not lines or line != lines[-1]):
            lines.append(line)
    return tuple(lines)


def instrumental_text(value: object) -> bool:
    text = normalized(value)
    return text in {"instrumental", "纯音乐", "純音樂", "nolyric", "nolyrics"}
