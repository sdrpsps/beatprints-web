"""Independently registered poster QR destinations."""

from beatprints_api.destinations.base import DestinationAdapter
from beatprints_api.destinations.registry import destination_keys, get_destination_adapter

__all__ = ["DestinationAdapter", "destination_keys", "get_destination_adapter"]
