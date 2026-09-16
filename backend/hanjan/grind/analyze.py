"""분쇄 입도 측정 — 흰 종이 위 원두 가루 사진에서 입자 크기 분포를 잰다.

AI를 쓰지 않는다. LLM에게 몇 mm인지 물으면 숫자를 지어내기 때문이다.
방식은 coffeegrindsize(Jonathan Gagné, MIT)와 같은 계열이다: 밝은 배경의 어두운 입자를 찾아 투영 면적을 지름으로 환산한다.
다른 점: 기준 길이를 손으로 찍는 대신 인쇄한 ArUco 마커로 자동 환산한다.

한계는 결과에 그대로 드러낸다.
- 픽셀 몇 개보다 작은 미분은 검출할 수 없다 → min_detectable_mm
- 서로 붙은 입자는 큰 입자 하나로 셀 수 있다 → clump_suspects
- 입자가 적으면 분포가 흔들린다 → warnings
"""

import math
from dataclasses import dataclass

import cv2
import numpy as np

MARKER_DICTIONARY = cv2.aruco.DICT_4X4_50
MARKER_ID = 0
MIN_AREA_PX = 12  # 이보다 작은 점은 센서 노이즈·먼지와 구분할 수 없다
MAX_PARTICLE_MM = 3.0  # 이보다 큰 어두운 물체(동전·그림자 등)는 입자로 보지 않는다
FEW_PARTICLES = 300
BIN_MM = 0.1


class GrindAnalysisError(ValueError):
    pass


@dataclass(frozen=True)
class HistogramBin:
    lo_mm: float
    hi_mm: float
    count: int
    area_share: float


@dataclass(frozen=True)
class GrindAnalysis:
    particle_count: int
    mm_per_px: float
    # 투영 면적 가중 백분위 (주 지표 — coffeegrindsize도 표면적 기준이 가장 정확하다고 본다)
    d10_mm: float
    d50_mm: float
    d90_mm: float
    # 개수 기준 백분위 (보조)
    count_d10_mm: float
    count_d50_mm: float
    count_d90_mm: float
    min_detectable_mm: float
    clump_suspects: int
    histogram: list[HistogramBin]
    warnings: list[str]


def _detector() -> "cv2.aruco.ArucoDetector":
    dictionary = cv2.aruco.getPredefinedDictionary(MARKER_DICTIONARY)
    return cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())


def locate_marker(gray: np.ndarray) -> np.ndarray:
    corners, ids, _ = _detector().detectMarkers(gray)
    if ids is None or len(ids) == 0:
        raise GrindAnalysisError("기준 마커를 찾지 못했어요. 마커 전체가 사진에 보이게, 흔들리지 않게 찍어 주세요")
    flat = ids.flatten().tolist()
    idx = flat.index(MARKER_ID) if MARKER_ID in flat else 0
    return corners[idx].reshape(4, 2).astype(np.float64)


def _background(gray: np.ndarray, mm_per_px: float) -> np.ndarray:
    """조명 얼룩 보정용 배경 밝기. 입자보다 큰 커널의 닫힘 연산으로 어두운 입자를 지운다.
    큰 사진에서 큰 커널은 느리므로 축소해서 계산하고 다시 키운다."""
    kernel_px = max(15, int(MAX_PARTICLE_MM * 1.5 / mm_per_px))
    scale = min(1.0, 31 / kernel_px)
    small = gray if scale == 1.0 else cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    k = max(3, int(kernel_px * scale) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    closed = cv2.morphologyEx(small, cv2.MORPH_CLOSE, kernel)
    closed = cv2.GaussianBlur(closed, (0, 0), k / 3)
    if scale != 1.0:
        closed = cv2.resize(closed, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_LINEAR)
    return closed


def _is_clump(mask: np.ndarray) -> bool:
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    contour = max(contours, key=cv2.contourArea)
    hull_area = cv2.contourArea(cv2.convexHull(contour))
    return hull_area > 0 and cv2.contourArea(contour) / hull_area < 0.8


def _weighted_percentiles(values: np.ndarray, weights: np.ndarray, qs: tuple[float, ...]) -> list[float]:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cum = np.cumsum(w)
    cum = cum / cum[-1]
    return [float(np.interp(q, cum, v)) for q in qs]


def analyze_grind(
    gray: np.ndarray,
    *,
    marker_mm: float | None = None,
    mm_per_px: float | None = None,
    darkness_ratio: float = 0.7,
) -> GrindAnalysis:
    if gray.ndim != 2 or gray.dtype != np.uint8:
        raise ValueError("8비트 흑백 이미지가 필요하다")
    warnings: list[str] = []
    exclude = np.zeros(gray.shape, dtype=np.uint8)

    if mm_per_px is None:
        if not marker_mm or marker_mm <= 0:
            raise GrindAnalysisError("마커 한 변 길이(mm)나 mm_per_px 중 하나가 필요해요")
        corners = locate_marker(gray)
        sides = np.linalg.norm(corners - np.roll(corners, -1, axis=0), axis=1)
        if sides.max() / sides.min() > 1.08:
            warnings.append("마커가 비스듬히 찍혔어요. 카메라를 종이와 평행하게 들면 오차가 줄어요")
        mm_per_px = marker_mm / float(sides.mean())
        center = corners.mean(axis=0)
        quiet_zone = center + (corners - center) * 1.8  # 마커와 흰 여백은 입자에서 뺀다
        cv2.fillConvexPoly(exclude, np.round(quiet_zone).astype(np.int32), 255)
    elif mm_per_px <= 0:
        raise GrindAnalysisError("mm_per_px는 0보다 커야 해요")

    background = _background(gray, mm_per_px).astype(np.float32)
    ratio = gray.astype(np.float32) / np.maximum(background, 1.0)
    binary = (ratio < darkness_ratio).astype(np.uint8)
    binary[exclude > 0] = 0

    n, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    height, width = gray.shape
    areas: list[int] = []
    clumps = 0
    too_big = 0
    for i in range(1, n):
        x, y, bw, bh, area = (int(v) for v in stats[i])
        if area < MIN_AREA_PX:
            continue
        if x == 0 or y == 0 or x + bw >= width or y + bh >= height:
            continue  # 사진 가장자리에 걸린 입자는 잘려 있다
        if 2 * math.sqrt(area / math.pi) * mm_per_px > MAX_PARTICLE_MM:
            too_big += 1
            continue
        areas.append(area)
        if area >= MIN_AREA_PX * 8 and _is_clump(labels[y : y + bh, x : x + bw] == i):
            clumps += 1

    if not areas:
        raise GrindAnalysisError("입자를 찾지 못했어요. 흰 종이 위에 가루를 넓게 흩어서 찍어 주세요")

    a = np.array(areas, dtype=np.float64)
    diameters = 2 * np.sqrt(a / np.pi) * mm_per_px
    area_mm2 = a * mm_per_px**2
    d10, d50, d90 = _weighted_percentiles(diameters, area_mm2, (0.1, 0.5, 0.9))
    c10, c50, c90 = (float(v) for v in np.percentile(diameters, [10, 50, 90]))
    min_detectable = 2 * math.sqrt(MIN_AREA_PX / math.pi) * mm_per_px

    top = min(MAX_PARTICLE_MM, math.ceil(float(diameters.max()) / BIN_MM) * BIN_MM)
    edges = np.arange(0.0, top + BIN_MM / 2, BIN_MM)
    if len(edges) < 2:
        edges = np.array([0.0, BIN_MM])
    idx = np.clip(np.digitize(diameters, edges) - 1, 0, len(edges) - 2)
    counts = np.bincount(idx, minlength=len(edges) - 1)
    area_by_bin = np.bincount(idx, weights=area_mm2, minlength=len(edges) - 1)
    total_area = float(area_mm2.sum())
    histogram = [
        HistogramBin(
            lo_mm=round(float(edges[i]), 2),
            hi_mm=round(float(edges[i + 1]), 2),
            count=int(counts[i]),
            area_share=round(float(area_by_bin[i]) / total_area, 4),
        )
        for i in range(len(edges) - 1)
    ]

    if len(areas) < FEW_PARTICLES:
        warnings.append(f"입자가 {len(areas)}개뿐이라 분포가 흔들릴 수 있어요. 가루를 더 뿌리거나 여러 장을 재 주세요")
    if clumps > 0.05 * len(areas):
        warnings.append(f"뭉친 입자로 보이는 것이 {clumps}개예요. 가루를 더 넓게 흩어 주세요")
    if too_big:
        warnings.append(f"{MAX_PARTICLE_MM:.0f}mm보다 큰 어두운 물체 {too_big}개는 입자에서 뺐어요")
    if min_detectable > 0.2:
        warnings.append(
            f"이 해상도로는 약 {min_detectable:.2f}mm보다 작은 미분을 잡지 못해요. 더 가까이서 찍어 주세요"
        )

    return GrindAnalysis(
        particle_count=len(areas),
        mm_per_px=round(float(mm_per_px), 6),
        d10_mm=round(d10, 4),
        d50_mm=round(d50, 4),
        d90_mm=round(d90, 4),
        count_d10_mm=round(c10, 4),
        count_d50_mm=round(c50, 4),
        count_d90_mm=round(c90, 4),
        min_detectable_mm=round(min_detectable, 4),
        clump_suspects=clumps,
        histogram=histogram,
        warnings=warnings,
    )
