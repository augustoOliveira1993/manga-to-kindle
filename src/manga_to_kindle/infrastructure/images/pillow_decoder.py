"""Decodificação Pillow com limites antes da carga completa de pixels."""

from __future__ import annotations

import warnings
from io import BytesIO

from PIL import Image, ImageChops, ImageOps

from manga_to_kindle.domain.image_processing import (
    MAX_IMAGE_PIXELS,
    ImageContentRejected,
    ImageInspection,
    ImageLimitExceeded,
    ImageProcessingProfile,
    ImageTransformOptions,
    ReadingDirection,
)


class PillowImageDecoder:
    def inspect(self, data: bytes, expected_format: str) -> ImageInspection:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    actual_format = image.format or ""
                    if actual_format != expected_format:
                        raise ImageContentRejected(
                            "A extensão e o conteúdo real da imagem não correspondem."
                        )
                    width, height = image.size
                    _ensure_dimensions(width, height)
                    if getattr(image, "n_frames", 1) != 1:
                        raise ImageContentRejected("Imagens animadas não são aceitas nesta etapa.")
                    image.verify()
                with Image.open(BytesIO(data)) as image:
                    image.load()
            return ImageInspection(actual_format, width, height)
        except (ImageContentRejected, ImageLimitExceeded):
            raise
        except Image.DecompressionBombError:
            raise ImageLimitExceeded("A imagem excede o limite de pixels.") from None
        except (OSError, ValueError, SyntaxError, Warning):
            raise ImageContentRejected(
                "A imagem está corrompida ou não pode ser decodificada."
            ) from None

    def transform(
        self,
        data: bytes,
        profile: ImageProcessingProfile,
        options: ImageTransformOptions,
        *,
        is_double_page: bool,
    ) -> tuple[bytes, ...]:
        self.inspect(data, _format_for_bytes(data))
        try:
            with Image.open(BytesIO(data)) as source:
                oriented = ImageOps.exif_transpose(source)
                base = _to_grayscale(oriented)
                if options.crop_margins:
                    base = _crop_light_margins(base)
                panels = _split_panels(base, options.reading_direction) if (
                    options.split_double_pages and is_double_page
                ) else (base,)
                return tuple(_render_panel(panel, profile) for panel in panels)
        except ImageContentRejected:
            raise
        except (OSError, ValueError, SyntaxError):
            raise ImageContentRejected(
                "A imagem não pôde ser preparada para o perfil Kindle."
            ) from None

    def preview(
        self,
        data: bytes,
        profile: ImageProcessingProfile,
        options: ImageTransformOptions,
        *,
        is_double_page: bool,
    ) -> tuple[bytes, ...]:
        transformed = self.transform(
            data,
            profile,
            options,
            is_double_page=is_double_page,
        )
        previews: list[bytes] = []
        for item in transformed:
            with Image.open(BytesIO(item)) as image:
                thumb = image.copy()
                thumb.thumbnail((150, 200), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                thumb.save(buffer, format="PNG", optimize=False)
                previews.append(buffer.getvalue())
        return tuple(previews)


def _ensure_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise ImageLimitExceeded("A imagem excede o limite de 50 megapixels.")


def _format_for_bytes(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "WEBP"
    raise ImageContentRejected("O conteúdo não possui assinatura JPEG, PNG ou WEBP válida.")


def _to_grayscale(image: Image.Image) -> Image.Image:
    if "A" in image.getbands() or image.mode in {"P", "PA"}:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        image = background.convert("RGB")
    elif image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    return image.convert("L")


def _crop_light_margins(image: Image.Image) -> Image.Image:
    difference = ImageChops.difference(image, Image.new("L", image.size, 255))
    mask = difference.point(lambda value: 255 if value > 12 else 0)
    bounds = mask.getbbox()
    return image.crop(bounds) if bounds is not None else image.copy()


def _split_panels(
    image: Image.Image,
    direction: ReadingDirection,
) -> tuple[Image.Image, Image.Image]:
    midpoint = image.width // 2
    left = image.crop((0, 0, midpoint, image.height))
    right = image.crop((midpoint, 0, image.width, image.height))
    if direction is ReadingDirection.RIGHT_TO_LEFT:
        return right, left
    return left, right


def _render_panel(image: Image.Image, profile: ImageProcessingProfile) -> bytes:
    available_width = profile.width - profile.margin_left - profile.margin_right
    available_height = profile.height - profile.margin_top - profile.margin_bottom
    resized = ImageOps.contain(
        image,
        (available_width, available_height),
        method=Image.Resampling.LANCZOS,
    )
    canvas = Image.new("L", (profile.width, profile.height), 255)
    x = profile.margin_left + (available_width - resized.width) // 2
    y = profile.margin_top + (available_height - resized.height) // 2
    canvas.paste(resized, (x, y))
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=False, compress_level=6)
    return output.getvalue()
