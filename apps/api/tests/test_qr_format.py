from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError

from beatprints_api.models.poster import TrackPosterRequest
from beatprints_api.services import rendering


@pytest.mark.parametrize('mode,expected', [('standard', 'standard'), ('wechat', 'wechat')])
def test_platform_uses_requested_format(mode, expected):
    seen = []
    def renderer(name):
        def make(_link):
            seen.append(name)
            return lambda _theme: Image.new('RGBA', (1, 1))
        return make
    adapter = SimpleNamespace(label='Test', standard_scannable=renderer('standard'), scannable=renderer('wechat'))
    with rendering.provider_rendering(None, (adapter, 'https://example.com'), (0, 0, 0), mode):
        rendering.beatprints_image.scannable('Light')
    assert seen == [expected]


def test_destination_with_native_code_keeps_it_for_both_formats():
    seen = []
    def native(_link):
        seen.append('native')
        return lambda _theme: Image.new('RGBA', (1, 1))
    adapter = SimpleNamespace(label='Native', standard_scannable=None, scannable=native)
    for mode in ('standard', 'wechat'):
        with rendering.provider_rendering(None, (adapter, 'https://example.com'), (0, 0, 0), mode):
            rendering.beatprints_image.scannable('Light')
    assert seen == ['native', 'native']


def test_unknown_qr_format_is_rejected():
    with pytest.raises(ValidationError):
        TrackPosterRequest(provider='deezer', catalog_id=1, qr_format='unknown')
