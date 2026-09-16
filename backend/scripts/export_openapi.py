"""OpenAPI 명세를 파일로 뽑는다. 프론트는 이 파일에서 TS 타입을 생성한다 (npm run gen:api).

CI가 다시 뽑아서 커밋본과 다르면 실패시킨다 — 백엔드 스키마를 바꾸고 프론트 타입을 안 바꾼 경우를 잡는다.
"""

import json
import sys
from pathlib import Path

from hanjan.config import Settings
from hanjan.embedding.fake import FakeEmbedder
from hanjan.llm.fake import FakeLLM
from hanjan.main import create_app


def main(out: str) -> None:
    app = create_app(
        Settings(env="dev", auth_mode="dev", llm_mode="fake", embedding_mode="fake"),
        llm=FakeLLM(),
        embedder=FakeEmbedder(),
    )
    # newline="\n": Windows에서 CRLF로 쓰면 리눅스 CI의 diff가 전부 다르다고 실패한다
    Path(out).write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
