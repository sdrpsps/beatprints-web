"""Generate sunflower codes with the local kuima service."""

import atexit
import base64
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageChops, ImageOps

from beatprints_api.config import settings
from beatprints_api.exceptions import IntegrationNotConfiguredError, UpstreamError


class KuimaClient:
    def __init__(self) -> None:
        self.http = httpx.Client(timeout=httpx.Timeout(15.0, connect=3.0), trust_env=False)
        atexit.register(self.http.close)

    def image(
        self, link: str, icon_path: Path, color: tuple[int, int, int],
        *, version: str | None = None, mask: int | None = None, margin: int = 0,
    ) -> Image.Image:
        if not settings.wechat_qr_base_url:
            raise IntegrationNotConfiguredError("WeChat QR service is not configured")
        try:
            with Image.open(icon_path) as icon:
                rgba = icon.convert("RGBA")
                logo_mask = ImageChops.multiply(ImageOps.invert(rgba.convert("L")), rgba.getchannel("A"))
                if not logo_mask.getbbox():
                    logo_mask = rgba.getchannel("A")
                logo = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
                logo.putalpha(logo_mask)
                buffer = BytesIO()
                logo.save(buffer, format="PNG")
            params = {"text": link, "format": "png", "size": 480,
                      "logo": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(),
                      "badge": "none", "fillBadge": True, "margin": margin}
            if version is not None:
                params["version"] = version
            if mask is not None:
                params["mask"] = mask
            response = self.http.post(
                f"{settings.wechat_qr_base_url}/api/encode",
                json=params,
            )
            response.raise_for_status()
            if response.headers.get("content-type", "").split(";", 1)[0] != "image/png":
                raise UpstreamError("Kuima service returned an unexpected image type")
            if len(response.content) > 2 * 1024 * 1024:
                raise UpstreamError("Kuima service returned an oversized image")
            with Image.open(BytesIO(response.content)) as result:
                expected_size = 480 + 2 * margin
                if result.format != "PNG" or result.size != (expected_size, expected_size):
                    raise UpstreamError("Kuima service returned an invalid image")
                ink = ImageOps.invert(result.convert("L"))
            image = Image.new("RGBA", ink.size, color + (0,))
            image.putalpha(ink)
            return image
        except httpx.HTTPStatusError as exc:
            raise UpstreamError(f"Kuima generation failed (HTTP {exc.response.status_code})") from exc
        except (httpx.RequestError, OSError) as exc:
            raise UpstreamError("Could not generate Kuima code") from exc


kuima_client = KuimaClient()
