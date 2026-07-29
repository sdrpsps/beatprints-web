from PIL import Image

from beatprints_api.palette import extract_palette


def test_extract_palette_returns_six_luminance_sorted_colors() -> None:
    image = Image.new("RGB", (12, 12), "white")
    for x in range(6):
        color = (x * 40, x * 20, x * 10)
        for y in range(12):
            image.putpixel((x, y), color)

    palette = extract_palette(image)
    luminance = [
        0.2126 * red + 0.7152 * green + 0.0722 * blue for red, green, blue in palette
    ]

    assert len(palette) == 6
    assert luminance == sorted(luminance)
