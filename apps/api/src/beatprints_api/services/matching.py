import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher

from beatprints_api.integrations.destinations import DestinationAdapter, get_destination_adapter
from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.models.destinations import (
    PlatformLinkMatchData,
    PlatformMatchOptionsData,
)
from beatprints_api.models.poster import (
    AlbumPosterRequest,
    TrackPosterRequest,
)
from beatprints_api.models.catalog import LyricsPreviewData
from beatprints_api.services import catalog as catalog_service
from beatprints_api.services import lyrics as lyrics_service

from BeatPrints import deez



def _match_text(value: object) -> str:
    """Normalize catalog text while retaining non-Latin artist and title characters."""

    return "".join(
        character for character in str(value or "").casefold() if character.isalnum()
    )


def _text_similarity(left: object, right: object) -> float:
    normalized_left = _match_text(left)
    normalized_right = _match_text(right)
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left == normalized_right:
        return 1.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _metadata_artists(metadata: deez.TrackMetadata | deez.AlbumMetadata) -> str:
    return " ".join(str(artist) for artist in metadata.artists)


def _duration_seconds(value: str) -> int | None:
    try:
        minutes, seconds = value.split(":", maxsplit=1)
        return int(minutes) * 60 + int(seconds)
    except (AttributeError, ValueError):
        return None


def _release_year(value: object) -> int | None:
    try:
        return date.fromisoformat(str(value)[:10]).year
    except ValueError:
        try:
            return int(str(value)[:4])
        except ValueError:
            return None


def _track_metadata(request: TrackPosterRequest) -> deez.TrackMetadata:
    return catalog_service.track_metadata(request)


def _album_metadata(request: AlbumPosterRequest) -> deez.AlbumMetadata:
    return catalog_service.album_metadata(request)


_VERSION_MARKERS = {
    "live", "remaster", "remastered", "acoustic", "instrumental",
    "karaoke", "radio edit", "demo", "mono", "stereo", "deluxe",
    "extended", "现场版", "現場版", "重制版", "重製版", "伴奏",
    "纯音乐", "純音樂", "原声", "原聲", "混音", "豪华版", "豪華版",
}
_VERSION_SUFFIX = re.compile(r"(?:^|[\s\[(（【\-–—])(?P<value>[^\])）】]+)(?=$|[\s\])）】])")


def _catalog_title_parts(
    value: object,
) -> tuple[frozenset[str], frozenset[str]]:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    version_regions = [match.group("value") for match in _VERSION_SUFFIX.finditer(text)]
    versions = frozenset(
        marker
        for marker in _VERSION_MARKERS
        if any(
            marker in region
            if any(ord(character) > 127 for character in marker)
            else re.search(rf"(?<![a-z]){re.escape(marker)}(?![a-z])", region)
            for region in version_regions
        )
    )
    base = re.sub(r"\s*[（(][^()（）]*[）)]\s*$", "", text).strip()
    aliases = {
        normalized
        for variant in (text, base)
        for part in re.split(r"\s+[-–—]\s+", variant)
        if (normalized := _match_text(part))
    }
    return frozenset(aliases), versions


def _catalog_title_similarity(left: object, right: object) -> float:
    left_aliases, left_versions = _catalog_title_parts(left)
    right_aliases, right_versions = _catalog_title_parts(right)
    if not left_aliases or not right_aliases or left_versions != right_versions:
        return 0.0
    return max(
        _text_similarity(left_alias, right_alias)
        for left_alias in left_aliases
        for right_alias in right_aliases
    )


def _artist_match_state(source: str, candidate: str) -> str:
    if _text_similarity(source, candidate) >= 0.88:
        return "matched"

    def latin_only(value: str) -> bool:
        letters = [character for character in value if character.isalpha()]
        return bool(letters) and all("LATIN" in unicodedata.name(character, "") for character in letters)

    return "mismatched" if latin_only(source) and latin_only(candidate) else "unknown"


def _artist_comparison(
    source_artists: list[str], candidate_artists: list[str]
) -> tuple[float, str]:
    pair_scores = [
        _text_similarity(source, candidate)
        for source in source_artists
        for candidate in candidate_artists
    ]
    score = max(pair_scores, default=0.0)
    if score >= 0.88:
        return score, "matched"
    return score, _artist_match_state(
        " ".join(source_artists), " ".join(candidate_artists)
    )


def _candidate_title_similarity(left: object, right: object) -> tuple[float, bool]:
    left_aliases, left_versions = _catalog_title_parts(left)
    right_aliases, right_versions = _catalog_title_parts(right)
    if not left_aliases or not right_aliases:
        return 0.0, False
    similarity = max(
        _text_similarity(left_alias, right_alias)
        for left_alias in left_aliases
        for right_alias in right_aliases
    )
    return similarity, left_versions != right_versions


def _candidate_search_title_similarity(left: object, right: object) -> float:
    """Broaden candidate discovery without changing automatic confirmation."""

    similarity, version_conflict = _candidate_title_similarity(left, right)
    if version_conflict:
        return similarity
    left_aliases, _left_versions = _catalog_title_parts(left)
    right_aliases, _right_versions = _catalog_title_parts(right)
    contains_equivalent_title = any(
        min(len(left_alias), len(right_alias)) >= 3
        and (left_alias in right_alias or right_alias in left_alias)
        for left_alias in left_aliases
        for right_alias in right_aliases
    )
    return max(similarity, 0.6 if contains_equivalent_title else 0.0)


def _candidate_score(
    metadata: deez.TrackMetadata | deez.AlbumMetadata,
    candidate: dict,
    item_type: str,
    origins: set[str],
) -> float | None:
    _, version_conflict = _candidate_title_similarity(
        metadata.title, candidate.get("title")
    )
    title_score = _candidate_search_title_similarity(
        metadata.title, candidate.get("title")
    )
    if title_score < 0.45:
        return None

    source_artists = [str(artist) for artist in metadata.artists]
    candidate_artists = [str(artist) for artist in candidate.get("artists") or []]
    artist_score, artist_state = _artist_comparison(
        source_artists, candidate_artists
    )
    if artist_state == "unknown":
        artist_score = 0.45
    if "artist" in origins:
        artist_score = min(1.0, artist_score + 0.20)

    source_year = _release_year(metadata.released)
    candidate_year = candidate.get("release_year")
    year_score = (
        0.5
        if not source_year or not candidate_year
        else float(source_year == candidate_year)
    )
    score = title_score * 0.50 + artist_score * 0.24 + year_score * 0.08

    if item_type == "track":
        album_score, _album_version_conflict = _candidate_title_similarity(
            metadata.album, candidate.get("album")
        )
        source_duration = _duration_seconds(metadata.duration)
        candidate_duration = candidate.get("duration_seconds")
        duration_score = (
            0.5
            if not source_duration or not candidate_duration
            else (
                1.0 if abs(source_duration - candidate_duration) <= 2
                else 0.8 if abs(source_duration - candidate_duration) <= 5
                else 0.35 if abs(source_duration - candidate_duration) <= 15
                else 0.0
            )
        )
        score += album_score * 0.08 + duration_score * 0.10
        if _album_version_conflict:
            score -= 0.05
    else:
        source_count = len(metadata.tracks)
        candidate_count = candidate.get("track_count")
        count_score = (
            0.5
            if not source_count or not candidate_count
            else float(source_count == candidate_count)
        )
        score += count_score * 0.12

    if version_conflict:
        score -= 0.25
    if source_year and candidate_year and source_year != candidate_year:
        score -= 0.10 if item_type == "track" else 0.20
    return score


def _source_metadata(provider: str, catalog_id: int | str, item_type: str):
    return (
        _track_metadata(TrackPosterRequest(provider=provider, catalog_id=catalog_id))
        if item_type == "track"
        else _album_metadata(AlbumPosterRequest(provider=provider, catalog_id=catalog_id))
    )


def _destination_adapter(platform: str) -> DestinationAdapter:
    """Compatibility seam for the shared engine and its isolated tests."""

    return get_destination_adapter(platform)


def _source_isrc(
    provider: str, catalog_id: int | str, metadata: deez.TrackMetadata
) -> str | None:
    return catalog_service.source_isrc(provider, catalog_id, metadata)


def _matching_queries(metadata, item_type: str, isrc: str | None) -> list[tuple[str, str]]:
    title = str(metadata.title).strip()
    artist = _metadata_artists(metadata).strip()
    queries: list[tuple[str, str]] = []
    if item_type == "track" and isrc:
        queries.append(("isrc", f"isrc:{isrc}"))
    seen_queries: set[str] = set()
    for origin, query in (
        ("combined", " ".join(part for part in (title, artist) if part)),
        ("title", title),
        ("artist", artist),
    ):
        if query and query not in seen_queries:
            queries.append((origin, query))
            seen_queries.add(query)
    return queries


def _collect_destination_candidates(
    adapter: DestinationAdapter, metadata, item_type: str, isrc: str | None
) -> list[tuple[dict, set[str]]]:
    candidates: dict[str, dict] = {}
    origins: dict[str, set[str]] = {}
    for origin, query in _matching_queries(
        metadata, item_type, isrc if adapter.supports_isrc else None
    ):
        for candidate in adapter.search(query, item_type):
            url = str(candidate.get("url") or "")
            if not url:
                continue
            identity = str(candidate.get("platform_id") or url)
            candidates.setdefault(identity, candidate)
            origins.setdefault(identity, set()).add(origin)
    return [
        (candidate, origins[identity])
        for identity, candidate in candidates.items()
    ]


def _has_hard_conflict(metadata, candidate: dict, item_type: str) -> bool:
    title_score, version_conflict = _candidate_title_similarity(
        metadata.title, candidate.get("title")
    )
    if title_score < 0.88 or version_conflict:
        return True
    _artist_score, artist_state = _artist_comparison(
        [str(artist) for artist in metadata.artists],
        [str(artist) for artist in candidate.get("artists") or []],
    )
    if artist_state == "mismatched":
        return True
    source_year = _release_year(metadata.released)
    candidate_year = candidate.get("release_year")
    if item_type == "album":
        source_count = len(metadata.tracks)
        candidate_count = candidate.get("track_count")
        return bool(
            source_year and candidate_year and source_year != candidate_year
            or source_count and candidate_count and source_count != candidate_count
        )
    source_duration = _duration_seconds(metadata.duration)
    candidate_duration = candidate.get("duration_seconds")
    return bool(
        source_duration
        and candidate_duration
        and abs(source_duration - candidate_duration) > 15
    )


def _can_confirm(
    metadata,
    ranked: list[tuple[float, dict, set[str]]],
    item_type: str,
    isrc: str | None,
) -> dict | None:
    if not ranked:
        return None
    score, candidate, origins = ranked[0]
    if isrc and candidate.get("isrc") == isrc:
        return candidate
    if _has_hard_conflict(metadata, candidate, item_type):
        return None
    _artist_score, artist_state = _artist_comparison(
        [str(artist) for artist in metadata.artists],
        [str(artist) for artist in candidate.get("artists") or []],
    )
    if artist_state == "mismatched":
        return None
    if artist_state == "unknown" and "artist" not in origins:
        return None
    threshold = 0.84
    if score < threshold:
        return None
    if len(ranked) > 1 and score - ranked[1][0] < 0.04:
        return None
    return candidate


def platform_match_options(
    provider: str,
    catalog_id: int | str,
    item_type: str,
    platform: str,
    limit: int = 8,
    *,
    source_metadata_fn=None,
    destination_adapter_fn=None,
    source_isrc_fn=None,
) -> PlatformMatchOptionsData:
    """Run one shared matching pipeline for every QR destination."""

    destination_adapter_fn = destination_adapter_fn or _destination_adapter
    source_metadata_fn = source_metadata_fn or _source_metadata
    source_isrc_fn = source_isrc_fn or _source_isrc
    adapter = destination_adapter_fn(platform)
    direct_match = (
        adapter.resolve_source(provider, catalog_id, item_type)
        if adapter.resolve_source is not None
        else None
    )
    if direct_match is not None:
        match = direct_match
        return PlatformMatchOptionsData(match=match, candidates=[match])

    metadata = source_metadata_fn(provider, catalog_id, item_type)
    isrc = (
        source_isrc_fn(provider, catalog_id, metadata)
        if item_type == "track" and adapter.supports_isrc
        else None
    )
    collected = _collect_destination_candidates(adapter, metadata, item_type, isrc)
    ranked: list[tuple[float, dict, set[str]]] = []
    for candidate, origins in collected:
        exact_isrc = bool(isrc and candidate.get("isrc") == isrc)
        score = (
            2.0
            if exact_isrc
            else _candidate_score(metadata, candidate, item_type, origins)
        )
        if score is not None:
            ranked.append((score, candidate, origins))
    ranked.sort(key=lambda item: item[0], reverse=True)
    confirmed = _can_confirm(metadata, ranked, item_type, isrc)
    return PlatformMatchOptionsData(
        match=(
            PlatformLinkMatchData.model_validate(confirmed) if confirmed is not None else None
        ),
        candidates=[
            PlatformLinkMatchData.model_validate(candidate)
            for _score, candidate, _origins in ranked[:limit]
        ],
    )


def resolve_platform_url(platform: str, url: str):
    return _destination_adapter(platform).resolve(url)


def clear_metadata_cache() -> None:
    catalog_service.clear_metadata_cache()


def preview_lyrics(
    provider: str, catalog_id: int | str, source: str | None = None
) -> LyricsPreviewData:
    request = TrackPosterRequest(provider=provider, catalog_id=catalog_id)
    metadata = _track_metadata(request)
    return lyrics_service.preview(provider, catalog_id, metadata, source)


def _select_lyrics(metadata: deez.TrackMetadata, request: TrackPosterRequest) -> str:
    return lyrics_service.select(metadata, request)
