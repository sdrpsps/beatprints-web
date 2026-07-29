import sys
import types

from PIL import Image


def install_pylette_compatibility_module() -> None:
    """Let BeatPrints import without Pylette's heavyweight runtime dependencies."""

    if "Pylette" in sys.modules:
        return

    module = types.ModuleType("Pylette")

    def extract_colors(*_args, **_kwargs):
        raise RuntimeError("BeatPrints palette extraction was not replaced")

    module.extract_colors = extract_colors
    sys.modules["Pylette"] = module


def extract_palette(image: Image.Image, size: int = 6) -> list[tuple[int, int, int]]:
    """Extract a luminance-sorted palette using Pillow's median-cut quantizer."""

    sample = image.convert("RGB")
    sample.thumbnail((256, 256), Image.Resampling.LANCZOS)
    quantized = sample.quantize(colors=size, method=Image.Quantize.MEDIANCUT)
    raw_palette = quantized.getpalette() or []
    counts = quantized.getcolors(maxcolors=size) or []
    colors = [
        tuple(raw_palette[index * 3 : index * 3 + 3])
        for _count, index in sorted(counts, reverse=True)
    ]
    if not colors:
        colors = [(0, 0, 0)]
    colors.extend([colors[-1]] * (size - len(colors)))
    return sorted(
        colors[:size],
        key=lambda color: 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2],
    )
