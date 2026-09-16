import cv2
import numpy as np
import pytest

from hanjan.grind.analyze import MIN_AREA_PX, GrindAnalysisError, _weighted_percentiles, analyze_grind
from hanjan.grind.synthetic import synthetic_grind_image


def area_weighted_d50(truth: np.ndarray) -> float:
    return _weighted_percentiles(truth, truth**2, (0.5,))[0]


def test_measures_known_particles_within_3_percent():
    diameters = np.random.default_rng(1).uniform(0.4, 1.2, size=600)
    img, truth = synthetic_grind_image(diameters, seed=1)

    result = analyze_grind(img, marker_mm=20.0)

    assert result.particle_count == len(truth)
    assert result.mm_per_px == pytest.approx(1 / 20, rel=0.01)
    assert result.d50_mm == pytest.approx(area_weighted_d50(truth), rel=0.03)
    assert result.count_d50_mm == pytest.approx(float(np.median(truth)), rel=0.03)
    assert result.clump_suspects == 0
    assert sum(b.count for b in result.histogram) == result.particle_count
    assert sum(b.area_share for b in result.histogram) == pytest.approx(1.0, abs=0.01)


def test_uneven_lighting_is_corrected():
    img, truth = synthetic_grind_image(np.full(400, 0.8), seed=2, lighting_gradient=0.45)

    result = analyze_grind(img, marker_mm=20.0)

    assert result.particle_count == len(truth)
    assert result.d50_mm == pytest.approx(float(np.median(truth)), rel=0.03)


def test_fines_below_detection_limit_are_not_counted_and_the_limit_is_reported():
    diameters = np.concatenate([np.full(300, 0.8), np.full(300, 0.1)])  # 0.1mm = 약 2px
    img, _ = synthetic_grind_image(diameters, seed=3)

    result = analyze_grind(img, marker_mm=20.0)

    assert result.particle_count == 300
    assert result.min_detectable_mm == pytest.approx(2 * np.sqrt(MIN_AREA_PX / np.pi) / 20, rel=0.02)


def test_missing_marker_is_an_error_not_a_guess():
    img = np.full((800, 800), 255, np.uint8)
    cv2.circle(img, (400, 400), 10, 40, -1)
    with pytest.raises(GrindAnalysisError, match="마커"):
        analyze_grind(img, marker_mm=20.0)


def test_explicit_scale_without_marker_and_few_particles_warning():
    img = np.full((800, 800), 255, np.uint8)
    for i in range(5):
        cv2.circle(img, (100 + i * 120, 400), 10, 40, -1)

    result = analyze_grind(img, mm_per_px=0.05)

    assert result.particle_count == 5
    assert any("분포가 흔들릴" in w for w in result.warnings)


def test_large_dark_object_is_excluded_with_warning():
    height, width = 2400, 3000
    coin_box = (width - 400, height - 400, width - 100, height - 100)
    img, _ = synthetic_grind_image(np.full(300, 0.8), seed=4, keep_clear=[coin_box])
    cv2.circle(img, (width - 250, height - 250), 40, 30, -1)  # 지름 약 4mm

    result = analyze_grind(img, marker_mm=20.0)

    assert result.particle_count == 300
    assert any("큰 어두운 물체" in w for w in result.warnings)


def test_touching_particles_are_flagged_as_clump():
    img = np.full((600, 600), 255, np.uint8)
    r = 12
    for cx, cy in [(300, 300), (300 + 2 * r, 300), (300, 300 + 2 * r)]:  # L자로 붙은 세 입자
        cv2.circle(img, (cx, cy), r, 40, -1)

    result = analyze_grind(img, mm_per_px=0.05)

    assert result.particle_count == 1
    assert result.clump_suspects == 1


def test_tilted_photo_warns():
    img, _ = synthetic_grind_image(np.full(300, 0.8), seed=5)
    h, w = img.shape
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    # 0.08 정도로는 마커 변 비율이 1.06이라 경고 기준(1.08)에 못 미친다 — 확실히 기울인다
    dst = np.float32([[w * 0.2, 0], [w * 0.8, 0], [w, h], [0, h]])
    tilted = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h), borderValue=255)

    result = analyze_grind(tilted, marker_mm=20.0)

    assert any("비스듬히" in warning for warning in result.warnings)
