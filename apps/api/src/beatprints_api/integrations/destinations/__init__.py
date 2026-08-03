"""Independently registered poster QR destinations."""

from beatprints_api.integrations.destinations.base import DestinationAdapter
from beatprints_api.integrations.destinations.registry import destination_keys, get_destination_adapter

__all__ = ["DestinationAdapter", "destination_keys", "get_destination_adapter"]
