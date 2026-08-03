"""Enabled QR destinations.

Each adapter registers itself when imported below. To temporarily disable a
destination, comment out its single import; catalog matching, link resolution,
and poster rendering will all stop exposing it together.
"""

from beatprints_api.integrations.destinations.base import DestinationAdapter
from beatprints_api.exceptions import UnsupportedDestinationError

_adapters: dict[str, DestinationAdapter] = {}


def register(adapter: DestinationAdapter) -> DestinationAdapter:
    if adapter.key in _adapters:
        raise RuntimeError(f"Destination adapter already registered: {adapter.key}")
    _adapters[adapter.key] = adapter
    return adapter


# The imports below are the complete enabled-destination list.
from beatprints_api.integrations.destinations import spotify as _spotify  # noqa: E402, F401
from beatprints_api.integrations.destinations import apple_music as _apple_music  # noqa: E402, F401
from beatprints_api.integrations.destinations import qq_music as _qq_music  # noqa: E402, F401
from beatprints_api.integrations.destinations import netease_music as _netease_music  # noqa: E402, F401


def get_destination_adapter(key: str) -> DestinationAdapter:
    try:
        return _adapters[key]
    except KeyError as exc:
        raise UnsupportedDestinationError(f"Unsupported QR destination: {key}") from exc


def destination_keys() -> tuple[str, ...]:
    return tuple(_adapters)
