# OCI Always Free 인프라

단일 ARM VM(2 OCPU · 12GB) 위 k3s. 백엔드·크롤러·임베딩·관측이 여기서 돈다.

**DB는 여기 없다** — Supabase(무료, 서울)를 쓴다. VM이 죽어도 데이터가 살아 있게 밖으로 뺐고, 그래서 이 VM에 남는 상태는 임베딩 모델 캐시(다시 받으면 되는 것)뿐이다.

## 순서

1. OCI 가입 — **홈 리전은 가입 때 정하면 바꿀 수 없다.** 춘천(`ap-chuncheon-1`)은 A1 예외 리전이라 고르지 않는다
2. 콘솔에서 API 키 등록 → `~/.oci/oci_api_key.pem`
3. 콘솔에서 상태 버킷 `hanjan-tfstate` 생성 + Customer Secret Key 발급 (S3 호환 자격증명)
4. `cp backend.hcl.example backend.hcl`, `cp terraform.tfvars.example terraform.tfvars` 후 값 채우기
5. 실행

```bash
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

6. VM이 뜨면 cloud-init이 k3s·sops·age를 깔고 배포 레포를 클론해 **동기화 타이머**를 켠다 (ArgoCD는 쓰지 않는다)
7. `age` 개인키를 `/etc/hanjan/age.key`(권한 600)에 넣는다 — 그 전까지 동기화는 시크릿 단계에서 **일부러 실패**한다
8. 이어서 [hanjan-deploy README](https://github.com/gongbugi/hanjan-deploy) 의 부트스트랩

## 함정

| 증상 | 원인 · 대응 |
|---|---|
| `Out of host capacity` | 홈 리전의 무료 A1 자리가 일시적으로 없다. `availability_domain_index`를 바꾸거나 시간을 두고 다시 apply |
| 인스턴스가 어느 날 멈춤 | **7일간 CPU(p95)·네트워크·메모리가 모두 20% 미만이면 회수될 수 있다** (Oracle 공식 문서). 방문자 적은 개인 앱이 딱 이 조건이다. ⚠️ 적용 계정 범위·회수 방식(중지/삭제)·사전 알림은 **공식 문서에 없다** (2026-09-16 확인). **자원을 일부러 더 써서 기준을 넘기는 건 대응이 아니다** — 회수를 장애로 보고 서비스 프로필의 복구 목표(알림 확인 뒤 4시간) 안에 다시 세울 수 있게 대비한다 |
| 보안 목록을 열었는데 접속 불가 | OCI 우분투 이미지의 iptables REJECT 규칙. cloud-init이 필요한 포트를 연다 |
| 이미지 갱신 때 VM이 교체되려 함 | `ignore_changes`로 막아 두었다. DB가 밖에 있어 예전만큼 위험하지는 않지만, 교체되면 age 키와 모델 캐시가 사라진다 |
| Supabase에 연결이 안 됨 | **직접 연결은 IPv6 전용**이다. IPv4 VM에서는 Shared Pooler(session mode, **5432**) 주소를 쓴다. 이그레스 5432는 이 보안 목록이 연다 |
| 한도를 넘는 값 | `ocpus`(≤2)·`memory_gb`(≤12)는 변수 검증이 막는다. 2026-06-15에 4 OCPU·24GB에서 절반으로 줄었다 |

비용이 1이라도 생기면 `budget_alert_email`로 메일이 온다.
