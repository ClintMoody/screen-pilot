from PIL import Image
from screen_pilot.diff import screenshots_differ


def test_identical_images_no_diff():
    img = Image.new("RGB", (100, 100), color="red")
    assert screenshots_differ(img, img) is False


def test_different_images_detected():
    img1 = Image.new("RGB", (100, 100), color="red")
    img2 = Image.new("RGB", (100, 100), color="blue")
    assert screenshots_differ(img1, img2) is True


def test_small_diff_below_threshold():
    img1 = Image.new("RGB", (100, 100), color=(128, 128, 128))
    img2 = Image.new("RGB", (100, 100), color=(128, 128, 128))
    img2.putpixel((50, 50), (255, 0, 0))
    assert screenshots_differ(img1, img2, threshold=0.01) is False
