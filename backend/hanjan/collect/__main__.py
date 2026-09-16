"""k8s CronJob 진입점: `python -m hanjan.collect`

태평양 자정(Gemini 하루 한도 초기화) 직후에 돌게 스케줄한다 — hanjan-deploy의 CronJob timeZone 참고.
"""

import argparse
import json
import sys
from dataclasses import asdict

from hanjan.collect.run import collect
from hanjan.collect.sources import load_sources, open_fetcher
from hanjan.config import Settings
from hanjan.db import make_engine, make_sessionmaker
from hanjan.embedding import build_embedder
from hanjan.llm.factory import build_llm
from hanjan.services.recommend import refresh_recommendations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="로스터리 신상 수집 → 정리 → 임베딩 → 추천 갱신")
    parser.add_argument("--skip-recommend", action="store_true", help="추천 갱신을 건너뛴다")
    args = parser.parse_args(argv)

    settings = Settings()
    sessions = make_sessionmaker(make_engine(settings.database_url))
    embedder = build_embedder(settings)
    llm = build_llm(settings, sessions)
    sources = load_sources(settings.roasters_file)

    with open_fetcher(settings) as fetcher, sessions() as session:
        result = collect(session, sources=sources, fetcher=fetcher, llm=llm, embedder=embedder)
        if not args.skip_recommend:
            snapshot = refresh_recommendations(session, embedder, llm)
            print(json.dumps({"recommendation_snapshot": snapshot.id, "items": len(snapshot.items)}))

    print(json.dumps(asdict(result), ensure_ascii=False))
    enabled = [s for s in sources if s.enabled]
    all_failed = bool(enabled) and len([e for e in result.errors if not e.startswith("정리")]) >= len(enabled)
    return 1 if all_failed else 0


if __name__ == "__main__":
    sys.exit(main())
