# Oracle 무료 VM은 ARM(Ampere A1)이다. CI에서 linux/arm64로 빌드한다.
# amd64 이미지를 올리면 파드가 `exec format error`로 뜨지 않는다.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models

WORKDIR /app

COPY pyproject.toml ./
COPY hanjan ./hanjan
# torch는 CPU 전용 인덱스에서 받는다 (기본 인덱스는 amd64에서 CUDA 의존성까지 끌어온다)
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu ".[embed]"

COPY alembic.ini ./
COPY alembic ./alembic

RUN useradd --uid 10001 --no-create-home app && mkdir -p /models && chown 10001 /models
USER 10001

EXPOSE 8000
CMD ["uvicorn", "hanjan.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
