"""Stable service facade for poster generation and catalog matching.

Focused modules own catalog access, lyrics, rendering, and destination matching.
This facade keeps route imports stable while avoiding a second business-logic
layer.
"""

from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.integrations.destinations import DestinationAdapter
from beatprints_api.services import catalog as catalog_service
from beatprints_api.services import lyrics as lyrics_service
from beatprints_api.services import matching as matching_service
from beatprints_api.services import posters as posters_service
from beatprints_api.services import rendering as rendering_service

PosterResult = rendering_service.PosterResult

search_catalog = catalog_service.search_catalog
clear_metadata_cache = catalog_service.clear_metadata_cache
preview_lyrics = matching_service.preview_lyrics
resolve_platform_url = matching_service.resolve_platform_url
generate_track = posters_service.generate_track
generate_album = posters_service.generate_album

# Temporary internal compatibility seams. New code imports the owning module.
_track_metadata = matching_service._track_metadata
_album_metadata = matching_service._album_metadata
_source_isrc = matching_service._source_isrc
_destination_adapter = matching_service._destination_adapter
_catalog_title_parts = matching_service._catalog_title_parts
_artist_comparison = matching_service._artist_comparison
_has_hard_conflict = matching_service._has_hard_conflict
_select_lyrics = lyrics_service.select
_renderable_lyrics = rendering_service._renderable_lyrics
_selected_platform_link = rendering_service.selected_platform_link
_provider_rendering = rendering_service.provider_rendering
_cover_qr_color = rendering_service.cover_qr_color
_contrast_with_white = rendering_service._contrast_with_white
write = rendering_service.write
beatprints_image = rendering_service.beatprints_image


def _source_metadata(provider: str, catalog_id: int | str, item_type: str):
    return (
        _track_metadata(matching_service.TrackPosterRequest(provider=provider, catalog_id=catalog_id))
        if item_type == "track"
        else _album_metadata(matching_service.AlbumPosterRequest(provider=provider, catalog_id=catalog_id))
    )


def platform_match_options(
    provider: str, catalog_id: int | str, item_type: str, platform: str, limit: int = 8
):
    return matching_service.platform_match_options(
        provider, catalog_id, item_type, platform, limit,
        source_metadata_fn=_source_metadata,
        destination_adapter_fn=_destination_adapter,
        source_isrc_fn=_source_isrc,
    )
