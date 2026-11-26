from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw
from tests.image_support import FIXTURES

from manga_to_kindle.domain.image_processing import (
    ImageProcessingProfile,
    ImageTransformOptions,
    ReadingDirection,
)
from manga_to_kindle.infrastructure.images.pillow_decoder import PillowImageDecoder


def test_profile_derivative_is_600_by_800_grayscale_and_keeps_ratio() -> None:
    source = Image.new("RGB", (400, 200), "white")
    ImageDraw.Draw(source).rectangle((0, 0, 399, 199), fill="#111111")
    data = _encode(source, "PNG")
    decoder = PillowImageDecoder()

    output = decoder.transform(
        data,
        ImageProcessingProfile(),
        ImageTransformOptions(),
        is_double_page=False,
    )

    with Image.open(BytesIO(output[0])) as result:
        assert result.size == (600, 800)
        assert result.mode == "L"
        assert result.getpixel((300, 300)) < 40
        assert result.getpixel((300, 150)) == 255


def test_exif_orientation_is_applied_to_derivative_only() -> None:
    source = Image.new("RGB", (100, 200), "white")
    ImageDraw.Draw(source).rectangle((0, 0, 19, 19), fill="#111111")
    exif = Image.Exif()
    exif[274] = 6
    output_buffer = BytesIO()
    source.save(output_buffer, format="JPEG", exif=exif)
    original = output_buffer.getvalue()
    decoder = PillowImageDecoder()

    output = decoder.transform(
        original,
        ImageProcessingProfile(),
        ImageTransformOptions(),
        is_double_page=False,
    )

    with Image.open(BytesIO(output[0])) as result:
        bbox = result.point(lambda value: 255 if value < 80 else 0).getbbox()
        assert bbox is not None
        assert (bbox[0] + bbox[2]) / 2 > 450


def test_transparency_is_composited_on_white_before_grayscale() -> None:
    original = (FIXTURES / "transparente.png").read_bytes()
    decoder = PillowImageDecoder()
    output = decoder.transform(
        original,
        ImageProcessingProfile(),
        ImageTransformOptions(),
        is_double_page=False,
    )

    with Image.open(BytesIO(output[0])) as result:
        assert result.mode == "L"
        assert result.getpixel((0, 0)) == 255
        assert 80 < result.getpixel((300, 400)) < 230


def test_crop_is_opt_in_and_spread_order_follows_reading_direction() -> None:
    source = Image.new("RGB", (240, 400), "white")
    ImageDraw.Draw(source).rectangle((30, 50, 210, 350), fill="#222222")
    data = _encode(source, "PNG")
    decoder = PillowImageDecoder()
    profile = ImageProcessingProfile()
    uncropped = decoder.transform(data, profile, ImageTransformOptions(), is_double_page=False)[0]
    cropped = decoder.transform(
        data,
        profile,
        ImageTransformOptions(crop_margins=True),
        is_double_page=False,
    )[0]
    spread = (FIXTURES / "dupla.png").read_bytes()
    rtl = decoder.transform(
        spread,
        profile,
        ImageTransformOptions(
            split_double_pages=True,
            reading_direction=ReadingDirection.RIGHT_TO_LEFT,
            double_page_paths=frozenset({"dupla.png"}),
        ),
        is_double_page=True,
    )
    ltr = decoder.transform(
        spread,
        profile,
        ImageTransformOptions(
            split_double_pages=True,
            reading_direction=ReadingDirection.LEFT_TO_RIGHT,
            double_page_paths=frozenset({"dupla.png"}),
        ),
        is_double_page=True,
    )

    with Image.open(BytesIO(uncropped)) as before, Image.open(BytesIO(cropped)) as after:
        before_bounds = before.point(lambda value: 255 if value < 200 else 0).getbbox()
        after_bounds = after.point(lambda value: 255 if value < 200 else 0).getbbox()
        assert before_bounds is not None and after_bounds is not None
        assert after_bounds[0] < before_bounds[0]
        assert after_bounds[2] > before_bounds[2]
    with Image.open(BytesIO(rtl[0])) as right_first, Image.open(BytesIO(ltr[0])) as left_first:
        assert len(rtl) == len(ltr) == 2
        assert right_first.getpixel((300, 400)) > left_first.getpixel((300, 400))
    assert data == _encode(source, "PNG")


def test_margin_values_are_preserved_in_output_frame() -> None:
    profile = ImageProcessingProfile(
        margin_left=40,
        margin_top=20,
        margin_right=10,
        margin_bottom=30,
    )
    source = Image.new("RGB", (100, 200), "black")
    output = PillowImageDecoder().transform(
        _encode(source, "PNG"),
        profile,
        ImageTransformOptions(),
        is_double_page=False,
    )[0]

    with Image.open(BytesIO(output)) as result:
        assert result.size == (600, 800)
        assert result.getpixel((0, 0)) == 255
        assert result.getpixel((300, 400)) == 0


def _encode(image: Image.Image, image_format: str) -> bytes:
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()
