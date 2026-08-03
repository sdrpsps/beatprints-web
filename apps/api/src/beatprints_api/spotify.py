"""Compatibility imports for code that has not yet migrated to integrations."""

from beatprints_api.integrations.catalog.spotify import (
    SpotifyClient,
    SpotifyError,
    SpotifyNotConfiguredError,
    spotify_client,
)
from beatprints_api.integrations.destinations.spotify_code import SpotifyCodeClient, spotify_code_client

__all__ = [
    "SpotifyClient", "SpotifyCodeClient", "SpotifyError", "SpotifyNotConfiguredError",
    "spotify_client", "spotify_code_client",
]
