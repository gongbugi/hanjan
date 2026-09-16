"""합성 입도 사진 — 지름을 아는 원을 그려서 측정 파이프라인의 오차를 잰다 (테스트·eval 공용).

실제 가루는 원이 아니고 겹치고 그림자가 진다. 여기서 재는 것은 '환산·검출 로직의 오차'까지이고,
실제 사진의 정확도는 eval/grind에서 coffeegrindsize 결과와 비교해 따로 잰다.
"""

import cv2
import numpy as np

from hanjan.grind.analyze import MARKER_DICTIONARY, MARKER_ID

Box = tuple[int, int, int, int]  # x0, y0, x1, y1


def _drawn_area(radius: int) -> int:
    canvas = np.zeros((2 * radius + 3, 2 * radius + 3), dtype=np.uint8)
    cv2.circle(canvas, (radius + 1, radius + 1), radius, 255, -1, lineType=cv2.LINE_8)
    return int(np.count_nonzero(canvas))


def synthetic_grind_image(
    diameters_mm,
    *,
    px_per_mm: float = 20.0,
    marker_mm: float = 20.0,
    size: tuple[int, int] = (2400, 3000),
    seed: int = 0,
    lighting_gradient: float = 0.0,
    particle_gray: int = 40,
    noise_sigma: float = 0.0,
    keep_clear: list[Box] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """(흑백 이미지, 실제로 그려진 픽셀 면적으로 환산한 지름 mm 배열)."""
    rng = np.random.default_rng(seed)
    height, width = size
    img = np.full((height, width), 255, dtype=np.uint8)

    marker_px = round(marker_mm * px_per_mm)
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(MARKER_DICTIONARY), MARKER_ID, marker_px
    )
    mx = my = marker_px
    img[my : my + marker_px, mx : mx + marker_px] = marker
    blocked: list[Box] = [(0, 0, mx + 2 * marker_px, my + 2 * marker_px), *(keep_clear or [])]

    diameters_px = np.asarray(diameters_mm, dtype=np.float64) * px_per_mm
    cell = int(np.ceil(max(diameters_px.max(), 4) * 2.5))
    cells = [
        (x, y)
        for y in range(cell, height - 2 * cell, cell)
        for x in range(cell, width - 2 * cell, cell)
        if not any(x < b[2] and x + cell > b[0] and y < b[3] and y + cell > b[1] for b in blocked)
    ]
    if len(cells) < len(diameters_px):
        raise ValueError(f"입자 {len(diameters_px)}개를 놓을 칸이 {len(cells)}개뿐이다 — 사진을 키울 것")
    order = rng.permutation(len(cells))

    truth = []
    for d_px, cell_idx in zip(diameters_px, order, strict=False):
        radius = max(0, int(round((d_px - 1) / 2)))
        x, y = cells[cell_idx]
        slack = max(0, (cell - (2 * radius + 1)) // 2 - 2)
        cx = x + cell // 2 + int(rng.integers(-slack, slack + 1))
        cy = y + cell // 2 + int(rng.integers(-slack, slack + 1))
        cv2.circle(img, (cx, cy), radius, particle_gray, -1, lineType=cv2.LINE_8)
        truth.append(2 * np.sqrt(_drawn_area(radius) / np.pi) / px_per_mm)

    out = img.astype(np.float32)
    if lighting_gradient:
        out *= np.linspace(1.0 - lighting_gradient, 1.0, width, dtype=np.float32)[None, :]
    if noise_sigma:
        out += rng.normal(0, noise_sigma, out.shape).astype(np.float32)
    return np.clip(out, 0, 255).astype(np.uint8), np.array(truth)
