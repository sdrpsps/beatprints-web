"""BeatPrints HTTP API."""

from beatprints_api.palette import install_pylette_compatibility_module

# BeatPrints imports Pylette at module import time. The production image removes
# that heavyweight dependency, so the compatibility module must be available
# before any integration imports BeatPrints.
install_pylette_compatibility_module()
