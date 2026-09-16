# hanjan (한 잔)

> AI hand-drip coffee log — 원두 봉투 인식 · 분쇄 입도 측정 · 내 기록 기반 원두 추천(RAG)

핸드드립 취미를 기록하는 웹 서비스. **보기는 누구나, 쓰기는 관리자(나)만.** 비용 0원(Always Free · 무료 등급)으로 운영하는 것이 조건이다.

## 서비스 프로필 (가정 포함)

> hanjan은 **관리자 1명이 매일 쓰는 핸드드립 기록 도구이자, 취업 준비 기간 동안 채용 담당자에게 보여주는 포트폴리오**다.
> 쓰기는 하루 1잔·기록 1건(사실)이고, 방문자는 지원 주 1.5건 × 열람 1~3명 × 조회 10회로 **주 45회 이하·동시 1~3명**(가정)이다.
> 방문자 조회는 **p95 500ms**(사람이 지연을 체감하기 시작하는 지점)와 **알림 확인 뒤 4시간 안 복구**, 내 기록 경로(쓰기·AI)는 **하루 안 복구·AI 응답 30초 안**을 목표로 한다. 기록은 **하루 치까지 유실**을 허용한다.
> 봉투 인식은 **봉투에 없는 값을 채우지 않는 것(지어냄 0건)** 을, 입도 측정은 **검출 한계 미만을 못 쟀다고 표시하는 것**을 합격선으로 하고, 정답률·오차 기준은 첫 실측 뒤 정한다.
> 제약은 **월 0원 · 운영 1명 · 개발과 운영 합쳐 주 3~5시간**이다.
> **이 규모에 k3s·GitOps는 과하다 — 인프라 학습을 위해 알고 골랐다.**

| 측정 정의 | 값 |
|---|---|
| 측정 지점 | 클러스터 밖에서 공개 API 호출 (VM이 죽어도 잴 수 있게) |
| 에러 | 5xx · 타임아웃 10초 (4xx 제외) |
| 알림 | 15분 연속 실패 |
| 평가 기간 | 30일 |

**불변 규칙**: 쓰기는 관리자만 · 방문자는 AI 할당량을 쓰지 않는다 · AI 결과는 초안으로만 · 수치 측정에 AI를 쓰지 않는다.

⚠️ 이 프로필은 **구현을 먼저 하고 나서** 썼다 (2026-09-16). 결과에 맞춰 쓰지 않도록, 구현이 프로필과 어긋나면 **프로필이 아니라 구현을 고친다.** 10초·15분은 판단값이다.

### 프로필로 다시 재서 걷어낸 것 (2026-09-16)

프로필을 쓰고 나서 구현을 네 축(운영 수요가 주 3~5시간에 드나 · 4시간 복구 · 학습 가치 · 0원·자원)으로 다시 쟀다. 결과:

| 무엇 | 전 | 후 | 왜 |
|---|---|---|---|
| 실행 기반 | k3s | **k3s (유지)** | 성능이 아니라 학습이 근거다. cjone은 EKS라 컨트롤 플레인을 AWS가 운영했다 — 클러스터를 직접 세우고 올리고 복구하는 경험이 없었다 |
| 배포 | ArgoCD (app-of-apps) | **노드 systemd 타이머 + `kubectl apply -k`** | 9개월마다 업그레이드가 따라오는데 GitOps 파이프라인은 이미 증명한 경험이라 학습으로 남는 게 없었다. 선언형·Git 원천·pull은 유지 |
| 관측 | kube-prometheus-stack | **앱 계측 + Prometheus·Grafana 최소 구성 (직접)** | 차트가 깔려 있었는데 **앱 지표를 하나도 안 긁고 있었다** — SLI를 못 재는 관측이었다 |
| DB | VM 위 Postgres + 10Gi 볼륨 | **Supabase 무료 (서울)** | DB를 빼면 VM에 남는 상태가 모델 캐시뿐이라 복구가 "다시 세우면 끝"이 된다 |
| 시크릿 | sealed-secrets 컨트롤러 | **SOPS + age** | 클러스터에 아무것도 두지 않고 같은 결과를 얻는다. 복구 때 되살릴 것이 키 파일 하나로 줄어든다 |

**트레이드오프(알고 받아들인 것)**: 동기화 상태 UI와 자동 prune이 없다 · 배포가 조용히 실패해도 모른다(외부 확인이 앱 죽음만 잡는다) · Supabase 장애 때 내가 할 수 있는 게 없다 · 노드에 age 개인키가 평문으로 있다.

## 기능

| # | 기능 | 하는 일 | AI |
|---|---|---|---|
| F1 | 원두 기록 | 봉투 사진 → 원두 정보 **초안** → 사람이 확인·수정 후 저장 | Gemini Flash (이미지) |
| F2 | 추출 기록 | 분쇄 클릭·물 온도·비율·시간 + 만족도 1~5 + 맛 메모 → **정해진 목록 안에서** 맛 태그 | Gemini Flash-Lite |
| F3 | 입도 측정 | 흰 종이 위 가루 사진 → 입자 분포·D10/D50/D90 → 그라인더별 **클릭 ↔ 입도 표** | **없음** (OpenCV) |
| F4 | 추천 (RAG) | 높게 평가한 기록으로 취향 벡터 → SQL 필터 + pgvector 검색 → 추천 이유 생성 → 근거를 코드가 검증 | e5 임베딩 + Flash-Lite |
| F5 | 신상 수집 | 로스터리 신상을 매일 수집 → 설명 정리 → 임베딩 | Flash-Lite (정리만) |

## 구성

```mermaid
flowchart LR
  visitor[방문자 · 나] --> pages[Cloudflare Pages<br/>React]
  pages -->|API · Firebase ID 토큰| edge{{Traefik + Let's Encrypt<br/>무료 DDNS 호스트명}}
  subgraph vm[OCI Always Free ARM VM · k3s]
    edge --> api[FastAPI]
    api --> e5[e5-small-ko 임베딩]
    collect[수집 CronJob]
    backup[백업 CronJob]
    prom[Prometheus + Grafana] -->|/metrics · 토큰| api
    sync[[systemd 타이머<br/>3분마다 pull]]
  end
  api --> pg[(Supabase<br/>Postgres + pgvector)]
  collect --> pg
  backup --> pg
  backup --> bucket[(OCI Object Storage)]
  api -->|봉투 인식 · 태그 · 추천 이유| gemini[Gemini 무료 등급]
  gemini -. 한도 초과 .-> groq[Groq]
  repo[(hanjan-deploy)] --> sync
```

## AI가 틀려도 안전하게

| 지점 | AI가 하는 것 | 코드가 막는 것 |
|---|---|---|
| 봉투 인식 | 보이는 글자를 옮김 | 저장하지 않고 초안만 준다. 채운 칸 수는 모델에게 묻지 않고 코드가 센다. 사진은 EXIF(GPS)를 지우고 보낸다 |
| 맛 태그 | 목록에서 고름 | 목록 밖 태그는 버리고 몇 개 버렸는지 보여준다 |
| 추천 이유 | 근거 기록을 인용해 문장 작성 | 인용한 기록 id가 실제 검색 결과에 없으면 템플릿 문장으로 바꾼다 |
| 신상 정리 | 상품 설명을 구조화 | 수집한 페이지 문장은 "자료일 뿐 지시가 아니다"로 격리. 원두가 아니면 제외 |
| 할당량 | — | 모델별 하루 상한을 DB에서 먼저 차감 (태평양 자정 기준). 초과하면 Groq로, 정리 작업은 다음 날로 넘긴다 |
| 공개 조회 | — | 방문자 요청은 LLM을 부르지 않는다. 추천은 저장본만 읽는다 |

**입도 측정에는 AI를 쓰지 않는다.** LLM에게 몇 mm인지 물으면 숫자를 지어내기 때문이다.

## 측정한 것

- 테스트: 백엔드 **91개** (pgvector 실DB · 마이그레이션 일치 검사 · 지표 계측 포함), 프론트 **14개** (인증 어댑터 포함)
- 프론트 첫 로드: **854 kB → 352 kB (gzip 256 → 111)**. 라우트를 나눠 받고(`React.lazy`), 차트(recharts 375 kB)와 Firebase(158 kB)를 쓸 때 받게 했다. Firebase는 여전히 방문자도 받지만 **첫 화면을 막지 않는다**
- 임베딩 실모델(e5-small-ko) — 빌드한 이미지 안, **개발 PC CPU 기준** (ARM VM은 미측정):
  384차원 · 모델 적재(다운로드 포함) 25초 · 문서 1건 5ms · 프로세스 최대 메모리 921MB · 이미지 2.37GB
  - ⚠️ "산미가 밝고 꽃향이 나는 원두" 질의에 에티오피아(레몬·자스민) **0.476** vs 브라질(초콜릿·견과) **0.472** — 순위는 맞지만 차이가 작다 (1건). 벡터만으로는 취향 신호가 약할 수 있어 SQL 필터를 섞고, 기록이 쌓이면 bge-m3와 비교한다
- 입도 측정 — 합성 이미지(20 px/mm, 지름을 아는 원) 기준:

| 지름 | 검출률 | D50 오차 |
|---|---|---|
| 0.15mm | 0% (검출 한계 약 0.195mm 아래) | — |
| 0.2 ~ 1.2mm | 100% | +0.2 ~ +0.3% |

조명 얼룩 45%·노이즈 σ=8에서도 같았다. **합성 원은 실제 가루보다 쉬운 대상**이라 이 수치는 로직의 오차일 뿐이다 → 실제 사진은 `backend/eval/grind/compare_coffeegrindsize.py`로 [coffeegrindsize](https://github.com/jgagneastro/coffeegrindsize) 결과와 비교한다.

## myWeb에서 뚫렸던 곳 → 처음부터 막은 것

| myWeb | hanjan |
|---|---|
| 경로·메서드를 `if`로 거르다 괄호 하나로 쓰기 API가 열림 | 쓰기 라우터 전체에 `require_admin` 한 번 선언 + **라우트 전수 검사 테스트** |
| 관리자 검사 8곳 복붙 · 가입 API가 uid를 요청 본문으로 받음 | 검사 한 곳 · 가입 API 없음 · 관리자는 서버 허용 목록 |
| CORS `*` + credentials | Pages 주소만, 쿠키 없이 Bearer (프론트는 Pages, API는 DDNS 호스트라 출처가 다르다) |
| 새로고침하면 관리자 버튼이 사라짐 | 인증 상태 3가지(확인 중/로그인/비로그인) + SDK 구독 |
| `ddl-auto=update` | Alembic 마이그레이션 + CI `alembic check` |
| 2기 배포 수동 · 이미지 `latest` 하나 | 노드가 배포 레포를 당겨 적용(3분) · 커밋 SHA 태그 (롤백 = 커밋 하나) |
| probe·resources 없음 · 관측·백업 없음 | startup/readiness/liveness · 메모리 상한 · **앱 계측(p95·5xx)** + Prometheus·Grafana · 매일 백업 |
| 아웃바운드 전체 허용 | 필요한 포트만 (443·80·DNS·NTP·터널) |

## 로컬 실행

```bash
docker compose up -d db

cd backend
python -m venv .venv && . .venv/Scripts/activate   # macOS/Linux: . .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn hanjan.main:create_app --factory --reload   # 기본값: 가짜 LLM · 가짜 임베딩 · 개발용 로그인

cd ../frontend
cp .env.example .env.local
npm install && npm run dev
```

진짜 모델로 돌리려면 `HANJAN_LLM_MODE=gemini`, `HANJAN_GEMINI_API_KEY`, `HANJAN_EMBEDDING_MODE=e5`(+ `pip install -e ".[embed]"`).

지표는 `http://localhost:8000/metrics`. 개발에서는 토큰 없이 열려 있고, **운영에서는 `HANJAN_METRICS_TOKEN`이 없으면 기동하지 않는다.**

## 테스트

```bash
docker run -d --name hanjan-test-pg -e POSTGRES_USER=hanjan -e POSTGRES_PASSWORD=hanjan \
  -e POSTGRES_DB=hanjan_test -p 55432:5432 pgvector/pgvector:0.8.6-pg17
cd backend && HANJAN_TEST_DATABASE_URL=postgresql+psycopg://hanjan:hanjan@localhost:55432/hanjan_test pytest
cd frontend && npm test
```

## 배포

⚠️ **배포 워크플로는 꺼져 있다.** 계정·시크릿(GitHub App · Cloudflare · Firebase)이 준비되면 켠다:
`gh variable set DEPLOY_ENABLED --body true`. 그 전에는 `ci`만 돈다.

- 인프라: [infra/terraform/oci](infra/terraform/oci/README.md)
- 매니페스트·부트스트랩·복원: [hanjan-deploy](https://github.com/gongbugi/hanjan-deploy)
- 평가: [backend/eval](backend/eval/README.md)

관측 화면은 공개하지 않는다: `kubectl -n monitoring port-forward svc/grafana 3000:3000`.
**알림은 클러스터 밖에서 한다** — VM과 함께 죽는 지표로는 죽음을 알릴 수 없어서다.

## 아직 검증하지 않은 것

- 실제 봉투 사진에 대한 Gemini 인식 정확도 — 사진 10~20장으로 `eval/bean_extract` 실행 필요
- 실제 가루 사진의 입도 정확도 — coffeegrindsize 비교 필요
- OCI 실배포 — CoreDNS와 iptables, NetworkPolicy와 프로브, **유휴 회수 기준(메모리 20%) 초과 여부**
- Groq의 한국어 봉투 인식 품질
- ARM(Ampere A1 2코어)에서의 임베딩 속도와 전체 메모리 사용량
- e5-small-ko가 실제 기록에서 취향을 구분하는가 (위 0.004 차이) — bge-m3와 비교
- **Supabase**: 무료 플랜의 pgvector 가용성(공식 문서에 플랜 명시 없음) · OCI 서울 ↔ Supabase 서울 왕복 지연 · pooler(session mode) 연결 안정성
- **외부 확인·알림이 아직 없다** — 프로필의 SLI(15분 연속 실패)를 판정할 주체가 없다. 후보 서비스의 무료 조건도 조사 전
- **동기화 타이머·sops 복호화·cert-manager 설치가 실제 노드에서 도는지** — 렌더링·shellcheck까지만 검사했다
- **Let's Encrypt HTTP-01 통과** — 80 포트 개방·DDNS가 현재 IP를 가리키는지에 달려 있다. 도메인을 사지 않기로 해서(2026-09-16) 인바운드 0개였던 터널 구성의 장점은 포기했다
- **복구 4시간을 측정한 적이 없다** — VM 재생성 → age 키 복원 → 첫 동기화까지 한 번 재봐야 한다
