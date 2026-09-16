"""그라인더 클릭 ↔ 입도(D50) 표.

제조사 스펙이 없는 그라인더라 이 표가 유일한 기준이다.
환산은 측정한 범위 안에서만 한다 — 범위 밖을 외삽하면 근거 없는 숫자가 된다.
"""

from collections import defaultdict
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class Point:
    clicks: int
    d50_mm: float


@dataclass(frozen=True)
class CalibrationRow:
    clicks: int
    n: int
    d50_median_mm: float
    d50_min_mm: float
    d50_max_mm: float


@dataclass(frozen=True)
class Calibration:
    rows: list[CalibrationRow]
    # 클릭이 늘면 입도가 줄지 않아야 한다. 아니면 영점이 틀어졌거나 측정이 흔들린 것
    monotonic: bool


@dataclass(frozen=True)
class ClickSuggestion:
    clicks: int | None
    reason: str


def build_calibration(points: list[Point]) -> Calibration:
    grouped: dict[int, list[float]] = defaultdict(list)
    for p in points:
        grouped[p.clicks].append(p.d50_mm)
    rows = [
        CalibrationRow(
            clicks=clicks,
            n=len(values),
            d50_median_mm=round(median(values), 4),
            d50_min_mm=round(min(values), 4),
            d50_max_mm=round(max(values), 4),
        )
        for clicks, values in sorted(grouped.items())
    ]
    monotonic = all(a.d50_median_mm <= b.d50_median_mm for a, b in zip(rows, rows[1:], strict=False))
    return Calibration(rows=rows, monotonic=monotonic)


def suggest_clicks(cal: Calibration, target_d50_mm: float) -> ClickSuggestion:
    rows = cal.rows
    if len(rows) < 2:
        return ClickSuggestion(None, "서로 다른 클릭으로 2번 이상 측정해야 환산할 수 있어요")
    if not cal.monotonic:
        return ClickSuggestion(None, "클릭을 늘려도 입도가 커지지 않는 구간이 있어 환산하지 않았어요")
    lo, hi = rows[0], rows[-1]
    if target_d50_mm < lo.d50_median_mm or target_d50_mm > hi.d50_median_mm:
        return ClickSuggestion(
            None,
            f"측정 범위({lo.d50_median_mm:.2f}~{hi.d50_median_mm:.2f}mm) 밖이라 환산하지 않았어요",
        )
    for a, b in zip(rows, rows[1:], strict=False):
        if a.d50_median_mm <= target_d50_mm <= b.d50_median_mm:
            span = b.d50_median_mm - a.d50_median_mm
            if span == 0:
                return ClickSuggestion(a.clicks, f"{a.clicks}클릭 측정값과 같아요")
            frac = (target_d50_mm - a.d50_median_mm) / span
            clicks = round(a.clicks + frac * (b.clicks - a.clicks))
            return ClickSuggestion(
                clicks,
                f"{a.clicks}클릭(D50 {a.d50_median_mm:.2f}mm)과 {b.clicks}클릭"
                f"(D50 {b.d50_median_mm:.2f}mm) 사이를 보간했어요",
            )
    return ClickSuggestion(None, "환산 구간을 찾지 못했어요")  # 도달하지 않음
