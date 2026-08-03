"""Shared poster-theme QR drawing helpers for destination adapters."""

from pathlib import Path

import qrcode
from PIL import Image, ImageChops, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_M

from BeatPrints import image as beatprints_image
from BeatPrints import write


def empty_scannable(_theme: str = "Light") -> Image.Image:
    return Image.new("RGBA", beatprints_image.s.SCANCODE, (0, 0, 0, 0))


def qr_font(size: int) -> ImageFont.FreeTypeFont:
    font_paths = write.font("Regular")
    path = next(
        (path for path in font_paths if "NotoSansSC" in path),
        next(iter(font_paths)),
    )
    return ImageFont.truetype(path, size)


def fallback_scannable(label: str, link: str, color: tuple[int, int, int]):
    """Render a readable generic QR for a destination without custom artwork."""

    def render(_theme: str = "Light") -> Image.Image:
        width, height = beatprints_image.s.SCANCODE
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(link)
        qr.make(fit=True)
        code = qr.make_image(fill_color=color, back_color="white").convert("RGBA")
        qr_size = 112
        code = code.resize((qr_size, qr_size), Image.Resampling.NEAREST)
        canvas.alpha_composite(code, (0, (height - qr_size) // 2))
        draw.text(
            (136, height // 2),
            label,
            fill=color + (255,),
            font=qr_font(28),
            anchor="lm",
        )
        return canvas

    return render


def platform_icon(path: Path, color: tuple[int, int, int], size: int) -> Image.Image:
    try:
        with Image.open(path) as source:
            rgba = source.convert("RGBA")
            alpha = rgba.getchannel("A")
            ink = ImageChops.invert(rgba.convert("L"))
            mask = ImageChops.multiply(alpha, ink)
    except OSError as exc:
        raise RuntimeError(f"Platform symbol asset is unavailable: {path.name}") from exc
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    icon = Image.new("RGBA", (size, size), color + (0,))
    icon.putalpha(mask)
    return icon


def transparent_qr(
    qr: qrcode.QRCode, color: tuple[int, int, int], target_size: int
) -> Image.Image:
    """Draw a transparent, poster-friendly dot QR with stable finder patterns."""

    modules = qr.get_matrix()
    module_count = len(modules)
    scale = 4
    size = target_size * scale
    module_size = size / module_count
    code = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(code)
    border = qr.border
    last_finder_start = module_count - border - 7

    def in_finder(x: int, y: int) -> bool:
        return (
            (border <= x < border + 7 and border <= y < border + 7)
            or (last_finder_start <= x < last_finder_start + 7 and border <= y < border + 7)
            or (border <= x < border + 7 and last_finder_start <= y < last_finder_start + 7)
        )

    for y, row in enumerate(modules):
        for x, enabled in enumerate(row):
            if enabled:
                left = round(x * module_size)
                top = round(y * module_size)
                right = round((x + 1) * module_size)
                bottom = round((y + 1) * module_size)
                if not in_finder(x, y):
                    inset = round(module_size * 0.12)
                    draw.ellipse(
                        (left + inset, top + inset, right - inset - 1, bottom - inset - 1),
                        fill=color + (255,),
                    )
    finder_radius = round(module_size * 0.3)
    for x, y in ((border, border), (last_finder_start, border), (border, last_finder_start)):
        left = round(x * module_size)
        top = round(y * module_size)
        right = round((x + 7) * module_size) - 1
        bottom = round((y + 7) * module_size) - 1
        draw.rounded_rectangle((left, top, right, bottom), radius=finder_radius, fill=color + (255,))
        inner_left = round((x + 1) * module_size)
        inner_top = round((y + 1) * module_size)
        inner_right = round((x + 6) * module_size) - 1
        inner_bottom = round((y + 6) * module_size) - 1
        draw.rounded_rectangle(
            (inner_left, inner_top, inner_right, inner_bottom),
            radius=round(module_size * 0.2),
            fill=(0, 0, 0, 0),
        )
        center_left = round((x + 2) * module_size)
        center_top = round((y + 2) * module_size)
        center_right = round((x + 5) * module_size) - 1
        center_bottom = round((y + 5) * module_size) - 1
        draw.rounded_rectangle(
            (center_left, center_top, center_right, center_bottom),
            radius=round(module_size * 0.2),
            fill=color + (255,),
        )
    return code.resize((target_size, target_size), Image.Resampling.LANCZOS)


def icon_qr_scannable(
    link: str,
    icon_path: Path,
    *,
    error_correction: int = ERROR_CORRECT_M,
):
    """Render a destination icon and dot QR using the shared poster theme color."""

    def render(theme: str = "Light") -> Image.Image:
        width, height = beatprints_image.s.SCANCODE
        color = beatprints_image.t.THEMES[theme]
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        qr = qrcode.QRCode(
            version=None,
            error_correction=error_correction,
            box_size=4,
            border=2,
        )
        qr.add_data(link)
        qr.make(fit=True)
        code = transparent_qr(qr, color, 112)
        icon = platform_icon(icon_path, color, 74)
        canvas.alpha_composite(icon, (0, (height - 74) // 2))
        canvas.alpha_composite(code, (98, (height - 112) // 2))
        return canvas

    return render
