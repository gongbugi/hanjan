import io

import numpy as np
from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError


def read_upload(file: UploadFile, max_mb: int) -> bytes:
    limit = max_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"사진은 {max_mb}MB 이하만 받아요")
    if not data:
        raise HTTPException(400, "빈 파일이에요")
    return data


def _open(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as e:
        # 아이폰 HEIC는 Pillow 기본 설치로 못 읽는다. 브라우저 파일 선택은 대개 JPEG로 바꿔 올린다
        raise HTTPException(415, "사진 형식을 읽을 수 없어요 (JPEG·PNG·WebP)") from e
    return ImageOps.exif_transpose(img)


def prepare_for_llm(data: bytes, max_side: int = 1600) -> bytes:
    """회전 보정 → 긴 변 축소 → JPEG로 새로 저장. 새로 저장하면 EXIF(GPS 위치 등)가 따라가지 않는다."""
    img = _open(data).convert("RGB")
    img.thumbnail((max_side, max_side))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


def decode_grayscale(data: bytes) -> np.ndarray:
    """입도 측정용. 절대 축소하지 않는다 — 축소하면 작은 입자가 사라져 미분 검출 한계가 나빠진다."""
    return np.array(_open(data).convert("L"), dtype=np.uint8)
