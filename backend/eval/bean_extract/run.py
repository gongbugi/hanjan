"""봉투 인식 모델 비교 — 실제 Gemini를 부르므로 무료 한도를 쓴다.

    cd backend
    HANJAN_GEMINI_API_KEY=... python -m eval.bean_extract.run --models gemini-3.8-flash gemini-3.7-flash

labels.json 형식은 labels.example.json 참고. 사진(images/)과 라벨은 gitignore 돼 있다 — 송장이 섞일 수 있다.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from eval.bean_extract.score import markdown_report, score
from hanjan.images import prepare_for_llm
from hanjan.llm.base import LLMError
from hanjan.llm.gemini import GeminiLLM
from hanjan.services.beans import extract_bean_draft

HERE = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--labels", default=str(HERE / "labels.json"))
    parser.add_argument("--sleep", type=float, default=7.0, help="호출 간격(초) — 분당 한도를 넘지 않게")
    args = parser.parse_args(argv)

    api_key = os.environ.get("HANJAN_GEMINI_API_KEY")
    if not api_key:
        print("HANJAN_GEMINI_API_KEY가 필요하다", file=sys.stderr)
        return 2

    labels_path = Path(args.labels)
    items = json.loads(labels_path.read_text(encoding="utf-8"))
    results, failures = {}, {}
    for model in args.models:
        llm = GeminiLLM(api_key, vision_model=model, text_model=model)
        pairs, failed = [], []
        for item in items:
            image = prepare_for_llm((labels_path.parent / item["image"]).read_bytes())
            try:
                draft, _ = extract_bean_draft(llm, image)
                pairs.append((item["expected"], draft.model_dump()))
            except LLMError as e:
                failed.append(f"{item['image']}: {e}")
            time.sleep(args.sleep)
        results[model] = score(pairs)
        failures[model] = failed

    report = markdown_report(results, failures, n_images=len(items))
    out = HERE / "reports" / f"{datetime.now():%Y%m%d-%H%M}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8", newline="\n")
    print(report)
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
