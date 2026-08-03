"""Independently registered source music catalogs."""

from beatprints_api.integrations.catalog.base import CatalogAdapter
from beatprints_api.integrations.catalog.registry import catalog_adapters, get_catalog_adapter

__all__ = ["CatalogAdapter", "catalog_adapters", "get_catalog_adapter"]
