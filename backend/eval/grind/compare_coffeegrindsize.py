"""같은 사진을 coffeegrindsize(Jonathan Gagné, MIT)로 잰 결과와 비교한다.

coffeegrindsize에서 입자 목록을 CSV로 내보낸 뒤, 지름(또는 면적) 열 이름과 단위를 지정한다.
내보내기 형식은 버전마다 다를 수 있어 열 이름을 코드에 고정하지 않았다.

    python -m eval.grind.compare_coffeegrindsize --image g.jpg --csv cgs.csv --column diameter --unit mm
"""

import argparse
import csv
from pathlib import Path

import numpy as np

from hanjan.grind.analyze import _weighted_percentiles, analyze_grind
from hanjan.images import decode_grayscale


def their_diameters_mm(path: Path, column: str, unit: str, kind: str, px_per_mm: float | None) -> np.ndarray:
    with path.open(encoding="utf-8", newline="") as f:
        values = np.array([float(row[column]) for row in csv.DictReader(f) if row.get(column)], dtype=np.float64)
    scale = {"mm": 1.0, "um": 1e-3, "px": 1.0 / px_per_mm if px_per_mm else None}[unit]
    if scale is None:
        raise SystemExit("--unit px에는 --px-per-mm가 필요하다")
    if kind == "area":
        return 2 * np.sqrt(values * scale**2 / np.pi)
    return values * scale


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--column", required=True)
    parser.add_argument("--unit", choices=["mm", "um", "px"], default="mm")
    parser.add_argument("--kind", choices=["diameter", "area"], default="diameter")
    parser.add_argument("--px-per-mm", type=float)
    parser.add_argument("--marker-mm", type=float, default=20.0)
    args = parser.parse_args()

    ours = analyze_grind(decode_grayscale(args.image.read_bytes()), marker_mm=args.marker_mm)
    theirs = their_diameters_mm(args.csv, args.column, args.unit, args.kind, args.px_per_mm)
    their_area_d50 = _weighted_percentiles(theirs, theirs**2, (0.5,))[0]
    their_count_d50 = float(np.median(theirs))

    rows = [
        ("입자 수", ours.particle_count, len(theirs)),
        ("D50 면적 기준(mm)", ours.d50_mm, their_area_d50),
        ("D50 개수 기준(mm)", ours.count_d50_mm, their_count_d50),
    ]
    print("| 지표 | hanjan | coffeegrindsize | 차이 |\n|---|---|---|---|")
    for name, a, b in rows:
        diff = f"{(a - b) / b:+.1%}" if b else "-"
        print(f"| {name} | {a:.4g} | {b:.4g} | {diff} |")


if __name__ == "__main__":
    main()
