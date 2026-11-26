from __future__ import annotations

import pytest

from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.image_processing import (
    ImageProcessingProfile,
    ImageTransformOptions,
    ReadingDirection,
)


def test_crop_and_spread_options_are_off_by_default_and_direction_is_rtl() -> None:
    profile = ImageProcessingProfile()
    options = ImageTransformOptions()

    assert profile.width == 600 and profile.height == 800
    margins = (
        profile.margin_left,
        profile.margin_top,
        profile.margin_right,
        profile.margin_bottom,
    )
    assert margins == (
        0,
        0,
        0,
        0,
    )
    assert options.crop_margins is False
    assert options.split_double_pages is False
    assert options.reading_direction is ReadingDirection.RIGHT_TO_LEFT


@pytest.mark.parametrize("margin", (-1, 41))
def test_margins_outside_supported_range_are_rejected(margin: int) -> None:
    with pytest.raises(DomainValidationError):
        ImageProcessingProfile(margin_left=margin)


def test_double_page_selection_requires_split_mode() -> None:
    with pytest.raises(DomainValidationError):
        ImageTransformOptions(double_page_paths=frozenset({"spread.png"}))
