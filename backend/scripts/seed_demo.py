"""로컬 데모 데이터. 개발 모드(가짜 LLM · 가짜 임베딩 · dev 로그인) 서버와 같은 DB에 넣는다.

    cd backend && python scripts/seed_demo.py

- 로스터리·원두 이름은 데모용으로 지어낸 것이다
- 입도 측정 사진은 합성 이미지(지름을 아는 원)다 — 실제 가루 사진이 아니다
- 비어 있는 DB에만 넣는다 (원두가 하나라도 있으면 멈춘다)
"""

import io
import sys
from datetime import date, timedelta

import httpx
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from hanjan.collect.run import collect
from hanjan.collect.sources import Fetcher, SourceConfig
from hanjan.config import Settings
from hanjan.embedding.fake import FakeEmbedder
from hanjan.grind.synthetic import synthetic_grind_image
from hanjan.llm.fake import FakeLLM
from hanjan.main import create_app

ADMIN = {"Authorization": "Bearer dev-admin"}

BEANS = [
    {
        "name": "예가체프 코체레",
        "roaster": "데모 로스터리",
        "country": "에티오피아",
        "region": "Yirgacheffe",
        "variety": "Heirloom",
        "processing": "워시드",
        "roast_level": "라이트",
        "bag_flavor_notes": ["자스민", "레몬", "홍차"],
    },
    {
        "name": "키린야가 AA",
        "roaster": "데모 로스터리",
        "country": "케냐",
        "region": "Kirinyaga",
        "variety": "SL28",
        "processing": "워시드",
        "roast_level": "라이트 미디엄",
        "bag_flavor_notes": ["블랙커런트", "자몽"],
    },
    {
        "name": "우일라 수프리모",
        "roaster": "골목 커피 (데모)",
        "country": "콜롬비아",
        "region": "Huila",
        "variety": "Caturra",
        "processing": "워시드",
        "roast_level": "미디엄",
        "bag_flavor_notes": ["캐러멜", "사과"],
    },
    {
        "name": "산토스 옐로 버번",
        "roaster": "골목 커피 (데모)",
        "country": "브라질",
        "region": "Santos",
        "variety": "Yellow Bourbon",
        "processing": "내추럴",
        "roast_level": "미디엄 다크",
        "bag_flavor_notes": ["초콜릿", "견과"],
    },
]

# (원두 순번, 며칠 전, 클릭, 온도, 원두g, 물g, 초, 만족도, 태그, 메모)
BREWS = [
    (0, 1, 18, 92, 15, 240, 150, 5, ["floral.floral", "fruity.citrus", "floral.black_tea"], "자스민 향이 확 올라오고 레몬 같은 산미. 식으니 홍차 느낌"),
    (0, 4, 22, 93, 15, 240, 140, 3, ["fruity.citrus", "green_vegetative.raw"], "너무 굵었는지 밍밍하고 끝이 덜 익은 맛"),
    (1, 2, 18, 94, 16, 250, 160, 4, ["fruity.berry", "fruity.citrus", "sour_fermented.sour"], "블랙커런트, 자몽. 산미가 밝다"),
    (2, 3, 20, 91, 15, 240, 155, 4, ["sweet.brown_sugar", "fruity.other_fruit"], "캐러멜 단맛에 사과 같은 과일감"),
    (3, 5, 26, 89, 15, 225, 135, 2, ["nutty_cocoa.cocoa", "roasted.burnt"], "초콜릿은 좋은데 탄 맛이 남는다"),
    (0, 7, 14, 92, 15, 240, 170, 3, ["floral.black_tea", "roasted.burnt"], "곱게 갈았더니 쓴맛이 올라옴"),
]

# 클릭 → 합성 D50(mm). 클릭이 늘수록 굵어진다
GRIND_MM = {14: 0.55, 18: 0.70, 20: 0.78, 22: 0.85, 26: 1.0}

CATALOG = [
    ("에티오피아 구지 함벨라 워시드", "<p>에티오피아 구지 워시드. 컵노트 복숭아, 자스민, 베르가못</p>", "21000"),
    ("케냐 니에리 AB 워시드", "<p>케냐 니에리 워시드. 컵노트 블랙커런트, 토마토, 자몽</p>", "23000"),
    ("과테말라 안티구아 허니", "<p>과테말라 안티구아 허니 프로세스. 컵노트 밀크초콜릿, 오렌지</p>", "18000"),
    ("브라질 세하도 내추럴", "<p>브라질 내추럴. 컵노트 땅콩, 코코아</p>", "15000"),
    ("시즌 드립백 10개입", "<p>드립백 세트</p>", "12000"),
]


def png(img: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, "PNG")
    return buf.getvalue()


def ok(response: httpx.Response) -> dict:
    if response.status_code >= 400:
        raise SystemExit(f"{response.request.method} {response.request.url} → {response.status_code} {response.text}")
    return response.json()


def demo_fetcher() -> Fetcher:
    products = [
        {"title": t, "handle": f"demo-{i}", "body_html": body, "variants": [{"price": price, "available": True}]}
        for i, (t, body, price) in enumerate(CATALOG)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, json={"products": products})

    return Fetcher(httpx.Client(transport=httpx.MockTransport(handler)), "hanjan-demo", 0)


def main() -> int:
    settings = Settings(env="dev", auth_mode="dev", llm_mode="fake", embedding_mode="fake")
    llm, embedder = FakeLLM(), FakeEmbedder(dim=settings.embedding_dim)
    app = create_app(settings, llm=llm, embedder=embedder)
    client = TestClient(app)

    if ok(client.get("/api/beans"))["total"] > 0:
        print("이미 데이터가 있어 건너뜀")
        return 0

    grinder = ok(client.post("/api/admin/grinders", json={"name": "알리 핸드밀 (모델 모름)", "notes": "3년 전 구매. 딸깍 클릭, 영점에서 푼 수로 기록"}, headers=ADMIN))
    beans = [ok(client.post("/api/admin/beans", json=b, headers=ADMIN)) for b in BEANS]

    measured_clicks = set()
    for bean_idx, days_ago, clicks, temp, dose, water, seconds, rating, tags, note in BREWS:
        brew = ok(
            client.post(
                "/api/admin/brews",
                json={
                    "bean_id": beans[bean_idx]["id"],
                    "grinder_id": grinder["id"],
                    "brewed_on": (date.today() - timedelta(days=days_ago)).isoformat(),
                    "grind_clicks": clicks,
                    "water_temp_c": temp,
                    "dose_g": dose,
                    "water_g": water,
                    "brew_time_s": seconds,
                    "rating": rating,
                    "flavor_tags": tags,
                    "note": note,
                },
                headers=ADMIN,
            )
        )
        img, _ = synthetic_grind_image(np.random.default_rng(clicks).normal(GRIND_MM[clicks], 0.15, 500).clip(0.25, 1.8), seed=clicks)
        ok(client.post("/api/admin/grind/measurements", data={"brew_id": brew["id"]}, files={"file": ("grind.png", png(img), "image/png")}, headers=ADMIN))
        measured_clicks.add(clicks)

    for clicks, d50 in GRIND_MM.items():  # 표를 채우려고 기록 없이 한 번 더 잰 측정
        img, _ = synthetic_grind_image(np.random.default_rng(clicks + 100).normal(d50, 0.15, 500).clip(0.25, 1.8), seed=clicks + 100)
        ok(client.post("/api/admin/grind/measurements", data={"grinder_id": grinder["id"], "clicks": clicks}, files={"file": ("grind.png", png(img), "image/png")}, headers=ADMIN))

    with app.state.sessions() as session:
        result = collect(
            session,
            sources=[SourceConfig(name="데모 로스터리 온라인몰", kind="shopify", url="https://demo-roastery.invalid")],
            fetcher=demo_fetcher(),
            llm=llm,
            embedder=embedder,
        )
    snapshot = ok(client.post("/api/admin/recommendations/refresh", headers=ADMIN))

    print(f"원두 {len(beans)} · 추출 {len(BREWS)} · 입도 측정 {len(BREWS) + len(GRIND_MM)} · 신상 {result.normalized}(원두 아님 {result.skipped}) · 추천 {len(snapshot['items'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
