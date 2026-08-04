"""Spotify-backed label enrichment for catalog entries missing label metadata."""

from urllib.parse import urlparse

from BeatPrints import deez
from beatprints_api.integrations.spotify_client import spotify_client
from beatprints_api.integrations.labels.base import LabelResolver
from beatprints_api.integrations.labels.registry import register


def _track_id(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) == 2 and parts[0] == "track" and len(parts[1]) == 22:
        return parts[1]
    return None


def resolve_track(metadata: deez.TrackMetadata) -> str | None:
    """Return a label only after the shared matcher confidently confirms a track."""

    from beatprints_api.services import matching

    options = matching.platform_match_options(
        "label_enrichment",
        "metadata",
        "track",
        "spotify",
        source_metadata_fn=lambda _provider, _catalog_id, _type: metadata,
        source_isrc_fn=lambda _provider, _catalog_id, _metadata: None,
    )
    if options.match is None:
        return None
    catalog_id = _track_id(str(options.match.url))
    if catalog_id is None:
        return None
    label = str(spotify_client.track_metadata(catalog_id).get("label") or "").strip()
    return label or None


resolver = register(
    LabelResolver(
        key="spotify",
        configured=lambda: spotify_client.configured,
        resolve_track=resolve_track,
    )
)
