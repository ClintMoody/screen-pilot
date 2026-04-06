"""Screenshot diffing for action verification."""

from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch


def screenshots_differ(
    before: Image.Image,
    after: Image.Image,
    threshold: float = 0.005,
) -> bool:
    if before.size != after.size:
        return True
    total_pixels = before.size[0] * before.size[1]
    diff_pixels = pixelmatch(before, after, includeAA=True)
    diff_ratio = diff_pixels / total_pixels
    return diff_ratio > threshold
