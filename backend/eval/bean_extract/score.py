"""봉투 인식 채점 — 필드별로 맞음 / 틀림 / 못 읽음 / 지어냄을 센다.

'지어냄'(봉투에 없는데 채움)을 따로 센다. 프롬프트가 금지한 행동이고, 사람이 확인할 때 가장 놓치기 쉬운 오류다.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

FIELDS = ("name", "roaster", "country", "region", "variety", "processing", "roast_level")

# 표기만 다른 같은 값. 여기 없는 차이는 틀림으로 센다 — 관대하게 채점하면 모델 비교가 무의미해진다
SYNONYMS = {
    "워시드": "washed",
    "수세식": "washed",
    "fully washed": "washed",
    "내추럴": "natural",
    "건식": "natural",
    "허니": "honey",
    "무산소": "anaerobic",
    "애너로빅": "anaerobic",
    "에티오피아": "ethiopia",
    "케냐": "kenya",
    "콜롬비아": "colombia",
    "과테말라": "guatemala",
    "브라질": "brazil",
    "코스타리카": "costa rica",
    "파나마": "panama",
    "르완다": "rwanda",
}


def normalize(value: object) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip().lower()
    if not text:
        return None
    return SYNONYMS.get(text, text)


@dataclass
class FieldScore:
    correct: int = 0  # 같음 (둘 다 빈칸인 경우 포함)
    wrong: int = 0  # 둘 다 값이 있는데 다름
    missed: int = 0  # 봉투에 있는데 못 읽음
    invented: int = 0  # 봉투에 없는데 채움

    @property
    def total(self) -> int:
        return self.correct + self.wrong + self.missed + self.invented

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def score(pairs: Iterable[tuple[dict, dict]]) -> dict[str, FieldScore]:
    scores = {field: FieldScore() for field in FIELDS}
    for expected, predicted in pairs:
        for field in FIELDS:
            e, p = normalize(expected.get(field)), normalize(predicted.get(field))
            s = scores[field]
            if e == p:
                s.correct += 1
            elif e is None:
                s.invented += 1
            elif p is None:
                s.missed += 1
            else:
                s.wrong += 1
    return scores


def overall(scores: dict[str, FieldScore]) -> FieldScore:
    total = FieldScore()
    for s in scores.values():
        total.correct += s.correct
        total.wrong += s.wrong
        total.missed += s.missed
        total.invented += s.invented
    return total


def markdown_report(results: dict[str, dict[str, FieldScore]], failures: dict[str, list[str]], n_images: int) -> str:
    lines = [
        f"# 봉투 인식 모델 비교 (사진 {n_images}장)",
        "",
        "| 모델 | 전체 정답률 | 지어냄 | 못 읽음 | 틀림 | 실패 호출 |",
        "|---|---|---|---|---|---|",
    ]
    for model, scores in results.items():
        o = overall(scores)
        lines.append(
            f"| {model} | {o.accuracy:.1%} | {o.invented} | {o.missed} | {o.wrong} | {len(failures.get(model, []))} |"
        )
    lines += ["", "## 필드별 정답률", "", "| 필드 | " + " | ".join(results) + " |", "|---|" + "---|" * len(results)]
    for field in FIELDS:
        lines.append(f"| {field} | " + " | ".join(f"{results[m][field].accuracy:.0%}" for m in results) + " |")
    for model, errors in failures.items():
        if errors:
            lines += ["", f"### {model} 실패", *[f"- {e}" for e in errors]]
    return "\n".join(lines) + "\n"
