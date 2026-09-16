import io

import numpy as np
import pytest
from fastapi import HTTPException
from PIL import Image

from hanjan.images import decode_grayscale, prepare_for_llm


def jpeg_with_exif(width=3000, height=2000) -> bytes:
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: 90도 회전해서 보여야 함
    exif[0x010F] = "PhoneMaker"  # Make
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_llm_image_is_rotated_downscaled_and_metadata_free():
    out = Image.open(io.BytesIO(prepare_for_llm(jpeg_with_exif())))
    assert max(out.size) == 1600
    assert out.size[1] > out.size[0]
    assert len(out.getexif()) == 0


def test_grind_image_keeps_full_resolution():
    gray = decode_grayscale(jpeg_with_exif())
    assert gray.shape == (3000, 2000)
    assert gray.dtype == np.uint8


def test_non_image_is_rejected():
    with pytest.raises(HTTPException) as e:
        prepare_for_llm(b"not an image")
    assert e.value.status_code == 415
