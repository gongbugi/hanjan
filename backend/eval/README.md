# 평가

AI(봉투 인식)와 AI 아닌 측정(입도)을 **숫자로** 확인한다. "잘 되는 것 같다"를 남기지 않는다.

## F1 봉투 인식 — 모델 비교

1. 원두 봉투 사진 10~20장을 `bean_extract/images/`에 둔다. **송장(이름·주소)은 가리거나 잘라낸다** — Gemini 무료 등급 입력은 제품 개선에 쓰일 수 있다
2. `labels.example.json`을 `labels.json`으로 복사해 봉투에 **실제로 보이는 값만** 정답으로 적는다 (안 보이면 `null`)
3. 실행

```bash
HANJAN_GEMINI_API_KEY=... python -m eval.bean_extract.run --models gemini-3.8-flash gemini-3.7-flash gemini-3.5-flash
```

리포트는 `bean_extract/reports/`에 남는다. 읽는 법:

| 열 | 의미 |
|---|---|
| 지어냄 | 봉투에 없는 값을 채움 — **가장 나쁜 오류**. 사람이 확인할 때 가장 놓치기 쉽다 |
| 못 읽음 | 봉투에 있는데 비움 — 사람이 채우면 되니 덜 나쁘다 |
| 틀림 | 둘 다 값이 있는데 다름 (표기 차이는 `score.py`의 동의어만 봐준다) |

모델을 고정하면 `hanjan-deploy/overlays/prod/config.env`의 `HANJAN_GEMINI_VISION_MODEL`을 바꾸고, **모델 ID를 바꿀 때마다 다시 돌린다.**

## F3 입도 측정

```bash
python -m eval.grind.synthetic_benchmark            # 합성 이미지 기준 검출률·오차
python -m eval.grind.compare_coffeegrindsize --image g.jpg --csv cgs.csv --column <열 이름> --unit mm
```

합성 결과는 로직의 오차일 뿐이다. 실제 가루 사진은 coffeegrindsize 결과와 비교한 숫자를 쓴다.
