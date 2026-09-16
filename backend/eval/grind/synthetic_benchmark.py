"""합성 이미지로 입도 측정의 검출률·오차를 잰다.

결과는 '합성 이미지 기준 측정치'다. 실제 가루는 원이 아니고 겹치고 그림자가 져서 더 나쁘다.
실제 사진의 정확도는 compare_coffeegrindsize.py로 따로 잰다.

    cd backend && python -m eval.grind.synthetic_benchmark
"""

import numpy as np

from hanjan.grind.analyze import GrindAnalysisError, analyze_grind
from hanjan.grind.synthetic import synthetic_grind_image

SIZES_MM = (0.15, 0.2, 0.3, 0.5, 0.8, 1.2)
CONDITIONS = {
    "기본": {},
    "조명 얼룩 45%": {"lighting_gradient": 0.45},
    "노이즈 σ=8": {"noise_sigma": 8.0},
}
PARTICLES = 300


def run(px_per_mm: float = 20.0) -> str:
    lines = [
        f"# 합성 이미지 입도 측정 ({px_per_mm:g} px/mm, 크기당 입자 {PARTICLES}개)",
        "",
        "| 조건 | 지름(mm) | 검출률 | D50 상대 오차 |",
        "|---|---|---|---|",
    ]
    for condition, kwargs in CONDITIONS.items():
        for size in SIZES_MM:
            img, truth = synthetic_grind_image(
                np.full(PARTICLES, size), px_per_mm=px_per_mm, seed=int(size * 1000), **kwargs
            )
            try:
                r = analyze_grind(img, marker_mm=20.0)
                detected = r.particle_count / len(truth)
                truth_median = float(np.median(truth))
                error = f"{(r.count_d50_mm - truth_median) / truth_median:+.1%}"
            except GrindAnalysisError as e:
                detected, error = 0.0, f"실패: {e}"
            lines.append(f"| {condition} | {size} | {detected:.0%} | {error} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(run())
