"""입도 측정용 기준 마커 PNG를 만든다.

인쇄는 반드시 '실제 크기(100%)'로 한다. '페이지에 맞춤'이면 크기가 바뀌어 모든 측정값이 같은 비율로 틀어진다.
인쇄한 뒤 자로 마커의 검은 사각형 한 변을 재서 그 값을 HANJAN_GRIND_MARKER_MM에 넣는다 (20mm로 뽑았다고 20mm가 아니다).
"""

import argparse

import cv2
import numpy as np
from PIL import Image

from hanjan.grind.analyze import MARKER_DICTIONARY, MARKER_ID


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mm", type=float, default=20.0, help="마커 한 변 길이(mm)")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--out", default="hanjan-marker.png")
    args = parser.parse_args()

    px_per_mm = args.dpi / 25.4
    side = round(args.mm * px_per_mm)
    marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(MARKER_DICTIONARY), MARKER_ID, side)

    margin = side  # 흰 여백(quiet zone)이 없으면 검출이 불안정하다
    ruler_mm = 50
    ruler_px = round(ruler_mm * px_per_mm)
    width = max(side + 2 * margin, ruler_px + 2 * margin)
    height = side + 2 * margin + 160
    canvas = np.full((height, width), 255, dtype=np.uint8)
    x0 = (width - side) // 2
    canvas[margin : margin + side, x0 : x0 + side] = marker

    y = margin + side + 70
    rx = (width - ruler_px) // 2
    cv2.line(canvas, (rx, y), (rx + ruler_px, y), 0, 3)
    for tick in range(0, ruler_mm + 1, 10):
        tx = rx + round(tick * px_per_mm)
        cv2.line(canvas, (tx, y - 15), (tx, y + 15), 0, 3)
    cv2.putText(
        canvas,
        f"hanjan marker {args.mm:g}mm / ruler {ruler_mm}mm - print at 100%",
        (margin // 2, height - 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        0,
        2,
    )
    Image.fromarray(canvas).save(args.out, dpi=(args.dpi, args.dpi))
    print(f"{args.out}: 마커 {side}px = {args.mm}mm @ {args.dpi}dpi")


if __name__ == "__main__":
    main()
