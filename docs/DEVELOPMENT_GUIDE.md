# PillyMate 디렉터리 구조 및 개발 시 주의사항

> 작성일: 2026-11-20
> 대상: PillyMate 백엔드·AI 개발 팀원
> 기준: 현재 `main` 브랜치의 템플릿 코드(FastAPI + AI Worker)

---

## 1. 한눈에 보는 구조

```text
PillyMate/
├── app/                      # FastAPI API 서버
│   ├── main.py               # 앱 생성, Tortoise 초기화, v1 라우터 등록
│   ├── apis/v1/              # 라우터 (HTTP 계층)
│   │   ├── __init__.py       #   └ v1_routers(prefix="/api/v1")에 각 라우터 include
│   │   ├── auth_routers.py   #   └ /auth/signup, /auth/login, /auth/demo-login
│   │   └── me_routers.py     #   └ /me (GET)
│   ├── services/             # 비즈니스 로직 (AuthService, JwtService)
│   ├── repositories/         # DB 접근 계층 (GuardianRepository)
│   ├── models/               # Tortoise ORM 모델 (Guardian, ERD v1.0)
│   ├── dtos/                 # Pydantic 요청/응답 스키마
│   ├── dependencies/         # FastAPI Depends용 함수 (CurrentGuardian, MyChild, MyPrescription)
│   ├── core/
│   │   ├── __init__.py       # 전역 config, default_logger 싱글턴
│   │   ├── config.py         # pydantic-settings 기반 Config, Env(local/dev/prod)
│   │   ├── logger.py
│   │   ├── db/               # TORTOISE_ORM 설정 + aerich 마이그레이션
│   │   ├── jwt/              # 토큰 백엔드(PyJWT), Access 토큰 클래스
│   │   ├── utils/            # 비밀번호 해시(bcrypt)
│   │   └── validators/       # Pydantic AfterValidator용 검증 함수
│   ├── tests/                # pytest + tortoise TestCase (MySQL 필요)
│   └── Dockerfile
├── ai_worker/                # AI 추론 워커 (현재 뼈대만 존재)
│   ├── main.py               # 대기 루프(작업 처리 로직은 TODO), SIGTERM 시 정상 종료
│   ├── core/                 # config, logger
│   ├── schemas/  tasks/      # 비어 있음
│   └── Dockerfile
├── envs/                     # example.local.env, example.prod.env (실제 .local.env/.prod.env는 git 제외)
├── infra/
│   ├── docker/docker-compose.prod.yml   # 운영용 compose (EC2에 docker-compose.yml로 복사됨)
│   └── nginx/                # default.conf(로컬), prod_http.conf, prod_https.conf
├── scripts/
│   ├── deployment.sh         # 이미지 빌드·푸시 → EC2 배포
│   ├── certbot.sh            # Let's Encrypt 인증서 발급
│   └── ci/                   # run_test.sh, code_fommatting.sh, check_mypy.sh
├── docs/                     # 회의록 및 문서
├── .github/                  # CI(checks.yml), PR 템플릿, 커밋 템플릿
├── docker-compose.yml        # 로컬 전체 스택 (redis, mysql, fastapi, ai-worker, nginx)
├── pyproject.toml            # uv 의존성 그룹(app / ai / dev), ruff·pytest·aerich 설정
└── uv.lock
```

---

## 2. 구조의 특징

### 2.1 모노레포 + 두 개의 실행 단위
- 하나의 `pyproject.toml`/`uv.lock`으로 **API 서버(`app`)와 AI 워커(`ai_worker`)** 를 함께 관리합니다.
- 의존성은 그룹으로 나뉩니다.
  - 공통: `pydantic`, `pydantic-settings`, `redis`, `cryptography` 등
  - `app`: FastAPI, Tortoise ORM, aerich, asyncmy, PyJWT, passlib/bcrypt
  - `ai`: torch(CPU 인덱스), sentence-transformers, scikit-learn
  - `dev`: ruff, mypy, pytest-asyncio, coverage
- 각 Dockerfile은 자기 그룹만 설치합니다 (`uv sync --group app` / `--group ai`). **`app` 코드에서 `ai` 그룹 패키지를 import하면 API 컨테이너에서 실패**하고, 그 반대도 마찬가지입니다.

### 2.2 계층형 아키텍처 (Router → Service → Repository → Model)
| 계층 | 위치 | 역할 | 예시 |
| --- | --- | --- | --- |
| Router | `app/apis/v1/` | HTTP 입출력, 의존성 주입, 쿠키·상태코드 처리 | `auth_routers.login` |
| DTO | `app/dtos/` | 요청 검증/응답 직렬화 (Pydantic) | `SignUpRequest`, `MeResponse` |
| Service | `app/services/` | 비즈니스 규칙, 트랜잭션 | `AuthService.signup` |
| Repository | `app/repositories/` | ORM 쿼리 캡슐화 | `GuardianRepository.get_by_email` |
| Model | `app/models/` | 테이블 정의 | `Guardian` |

- 서비스는 `Depends(AuthService)` 형태로 **요청마다 새로 인스턴스화**되고, 내부에서 Repository를 직접 생성합니다.
- 인증이 필요한 API는 `guardian: CurrentGuardian`으로 로그인한 `Guardian`을 주입받습니다 (Authorization: Bearer 헤더). 토큰 문제는 모두 401 "로그인이 필요해요."
- 내 자녀·내 처방전 확인은 `MyChild`, `MyPrescription`, `get_my_child_or_404()`를 씁니다 (남의 데이터는 404).

### 2.3 인증 방식
- 로그인·데모 로그인은 **Access Token만 응답 바디**로 내려줍니다 (유효시간 12시간, 리프레시 토큰 없음, 로그아웃은 FE가 토큰 삭제). API 명세서 v1.0 1절 기준.
- JWT는 `app/core/jwt/`에 직접 구현되어 있습니다 (HS256, `SECRET_KEY` 서명, `jti`/`exp`/`type`/`guardian_id` 클레임).

### 2.4 설정 관리
- `app/core/__init__.py`에서 **import 시점에 `Config()`를 생성**하여 `config` 싱글턴으로 사용합니다.
- `Config`는 **현재 작업 디렉터리의 `.env`** 파일과 OS 환경변수를 읽습니다.

### 2.5 DB / 마이그레이션
- MySQL 8.0 + Tortoise ORM(asyncmy) + aerich.
- 모델 등록 목록: `app/core/db/databases.py`의 `TORTOISE_APP_MODELS`.
- 마이그레이션 파일: `app/core/db/migrations/models/`.
- `register_tortoise`에 `generate_schemas`가 없으므로 **테이블은 자동 생성되지 않습니다.** aerich로 직접 적용해야 합니다.

### 2.6 인프라
- 로컬: `docker-compose.yml` → nginx(80) → fastapi(8000), mysql, redis, ai-worker.
- 운영: `scripts/deployment.sh`가 이미지를 Docker Hub에 푸시하고 EC2의 `~/project/`에 `.env`, `docker-compose.yml`, `nginx/default.conf`를 복사한 뒤 `docker compose up`을 실행합니다.
- Nginx는 `/api/` 경로만 프록시하고 나머지는 404를 반환합니다. Swagger는 `/api/docs`입니다.

### 2.7 CI
- `.github/workflows/checks.yml`: `main`, `develop`, `release/*`, `hotfix/*` 대상 push/PR에서
  1. `ruff check .` + `ruff format --check`
  2. MySQL 서비스 컨테이너를 띄워 `pytest app` + coverage

---

## 3. 새 기능 추가 절차

PillyMate 1차 MVP(로그인 → 처방전 업로드 → OCR → 가이드 생성) 기능을 추가할 때의 순서입니다.

### 3.1 새 도메인(예: 처방전 `prescriptions`) 추가
1. **모델**: `app/models/prescriptions.py` 작성
2. **모델 등록**: `app/core/db/databases.py`의 `TORTOISE_APP_MODELS`에 `"app.models.prescriptions"` 추가
3. **마이그레이션 생성/적용**
   ```bash
   uv run aerich migrate --name add_prescriptions
   uv run aerich upgrade
   ```
   생성된 마이그레이션 파일은 반드시 커밋합니다. 여러 명이 동시에 마이그레이션을 만들면 순번이 충돌하므로 **모델 변경 PR은 순서를 조율**하세요.
4. **DTO**: `app/dtos/prescriptions.py` (응답 DTO는 `BaseSerializerModel`을 상속하면 ORM 객체에서 바로 `model_validate` 가능)
5. **Repository**: `app/repositories/prescription_repository.py`
6. **Service**: `app/services/prescriptions.py`
7. **Router**: `app/apis/v1/prescription_routers.py` 작성 후 `app/apis/v1/__init__.py`에 `include_router`
8. **테스트**: `app/tests/prescription_apis/test_*.py` (+ 빈 `__init__.py`)

### 3.2 AI 기능(OCR, LLM 가이드) 추가
- `ai_worker/tasks/`에 작업 로직, `ai_worker/schemas/`에 입출력 스키마를 둡니다.
- 현재 **API ↔ 워커 간 통신 방식이 정해져 있지 않습니다.** (redis가 의존성과 compose에 있지만 코드에서는 사용하지 않음)
  - 옵션 A: Redis 큐(RQ/arq/Celery 등)로 작업 위임 → 비동기 처리, 결과는 DB 저장 후 조회
  - 옵션 B: 회의록대로 외부 API(Clova OCR, LLM API) 호출은 `app` 내부 모듈로 두고 워커는 무거운 로컬 모델 작업에만 사용
  - 팀에서 방식을 먼저 확정하고 공통 JSON 스키마(처방 JSON, 가이드 Structured Output)를 합의하세요.
- 외부 API 호출(Clova OCR, LLM)은 `httpx.AsyncClient` 등 **비동기 클라이언트**를 사용하세요. FastAPI 이벤트 루프에서 동기 블로킹 호출을 하면 전체 요청이 멈춥니다.

---

## 4. 개발 시 주의해야 할 점

### 4.1 환경변수 / 실행 환경 ⚠️
- **`.env` 위치 문제**
  - `Config`·`docker-compose.yml`(`env_file: .env`, `${DB_...}` 치환)·`scripts/ci/run_test.sh`(`source .env`)는 모두 **프로젝트 루트의 `.env`** 를 읽습니다.
  - 로컬에서는 `cp envs/.local.env .env` 로 루트에도 두거나, `docker compose --env-file envs/.local.env` 를 사용하세요.
  - `Config`는 실행 디렉터리 기준으로 `.env`를 찾으므로 **항상 프로젝트 루트에서 실행**해야 합니다.
- **`DB_HOST` 값**
  - 호스트에서 `uv run uvicorn ...`으로 실행 → `DB_HOST=localhost`
  - Docker 컨테이너(fastapi) 안에서 실행 → `DB_HOST=mysql` (서비스명). `example.local.env`의 `localhost`를 그대로 쓰면 컨테이너에서 DB 연결이 실패합니다.
- **`SECRET_KEY` 필수 설정**: example env의 값은 템플릿 값이니 `python -c "import secrets; print(secrets.token_urlsafe(48))"`로 생성한 값으로 교체하세요. 미설정 시 프로세스마다 랜덤 키가 생성됩니다. 운영 Dockerfile은 `--workers 3`이라 **워커마다 키가 달라져 토큰 검증이 무작위로 실패**하고, 재시작 시 모든 토큰이 무효화됩니다.
- **`ENV` 변수**: example env 파일에 `ENV=local` / `ENV=prod`가 들어 있습니다. 운영에서는 `ENV=prod`, `STORAGE_BACKEND=s3`, `DEMO_LOGIN_ENABLED`(시연 여부에 맞게)를 꼭 확인하세요.
- example env의 `DOCKER_USER=ozcodingschool`, 비밀번호·SECRET_KEY는 템플릿 값입니다. **팀 값으로 교체하고, 실제 값은 절대 커밋하지 마세요** (`.gitignore`의 `.*.env`, `.env` 규칙 유지).

- **로컬 MySQL 포트 충돌**: Homebrew 등으로 Mac에 MySQL이 설치·실행 중이면 `127.0.0.1:3306`을 먼저 점유해 Docker MySQL 대신 로컬 MySQL로 접속됩니다(`Access denied for user ...@'localhost'`). `brew services stop mysql@8.4` 등으로 끄거나 `DB_EXPOSE_PORT`/`DB_PORT`를 3307 등으로 바꾸세요.

### 4.2 서비스명
- compose 서비스명은 **`fastapi`**, **`ai-worker`** 입니다.
  ```bash
  docker compose up -d --build fastapi
  docker compose up -d --build ai-worker
  ```

### 4.3 DB / 마이그레이션
- 테이블 자동 생성이 없으므로 **최초 실행 시 `uv run aerich upgrade`** 가 필요합니다.
- 테이블·컬럼 이름은 `PillyMate_ERD_v1.0`을 따릅니다. `guardian.email`은 UNIQUE이며 소문자로 저장합니다. PK 컬럼 이름이 `guardian_id`처럼 테이블별로 다르면 `fields.BigIntField(primary_key=True, source_field="guardian_id")`처럼 코드에서는 `id`, DB에서는 ERD 이름을 씁니다.
- 한글 저장을 위해 MySQL은 `utf8mb4`로 설정되어 있습니다. 컨테이너 설정을 바꿀 때 이 옵션을 유지하세요.
- 시간대는 `Asia/Seoul`로 통일되어 있습니다(`config.TIMEZONE`, Tortoise `timezone`). 시간 생성 시 `datetime.now(config.TIMEZONE)`을 사용하세요.

### 4.4 템플릿 코드 버그 수정 내역 (2026-11-20 ✅ 수정 완료)
| 위치 | 기존 문제 | 수정 |
| --- | --- | --- |
| `app/core/jwt/tokens.py` `RefreshToken.lifetime` | 분 값을 일(day)로 사용 → 만료 약 55년 | `timedelta(minutes=...)` (14일) |
| `app/core/jwt/tokens.py` `set_exp` | `timegm(dt.timetuple())`이 KST 시각을 UTC로 계산 → 모든 토큰 `exp`가 9시간 늦음 | `int(dt.timestamp())` |
| `app/apis/v1/auth_routers.py` `login` | 쿠키 `expires`에 access token exp(정수) 사용. Starlette는 정수를 "지금부터 N초"로 해석해 사실상 무기한 | refresh token exp를 UTC `datetime`으로 전달 |
| `app/dtos/auth.py` `SignUpRequest.email` | `Field(None, ...)` → email 누락 시 500 | 필수값(422) |
| `app/repositories/user_repository.py` | `ALLOWED_UPDATE_FIELDS` 미사용 | `update_instance`에서 허용 필드만 반영 (`email` 포함) |
| `app/services/users.py` `update_user` | 본인 현재 이메일/전화번호도 409 | 현재 값과 다를 때만 중복 검사 |

### 4.5 코드 컨벤션 / 품질
- **import 정렬**: ruff의 `I`(isort) 규칙이 켜져 있습니다. 커밋 전 `./scripts/ci/code_fommatting.sh` 실행을 습관화하세요.
- 라인 길이 120, 더블쿼트. `__init__.py`는 F401(미사용 import) 예외.
- ruff `target-version = "py312"`, 실제 런타임은 Python 3.13입니다. 3.13 전용 문법을 쓰면 pyupgrade 규칙과 엇갈릴 수 있습니다.
- `pyproject.toml`에 mypy 설정이 없습니다. `check_mypy.sh`는 `mypy .` 전체를 검사하므로 필요하면 `[tool.mypy]`에 `exclude`/`strict` 범위를 정하세요.
- **응답 처리 방식**: 라우터가 `Response(...)` 객체를 직접 반환하므로 `response_model`은 **문서화 용도로만** 쓰이고 응답 검증은 일어나지 않습니다. 반드시 DTO의 `model_dump()`를 거쳐 반환하세요. 또 `auth_routers`는 `JSONResponse`, `user_routers`는 `ORJSONResponse`를 쓰고 있으니 신규 라우터는 하나로 통일하세요 (기본 응답 클래스는 `ORJSONResponse`).
- 서비스에서 `HTTPException`을 직접 raise하는 구조입니다. 이 패턴을 따르되, 에러 메시지(한국어)와 상태코드 규칙을 팀에서 통일하세요.

### 4.6 테스트
- 테스트는 **실제 MySQL**이 필요합니다 (`test` DB를 생성/삭제). 로컬에서는 `docker compose up -d mysql` 후 `./scripts/ci/run_test.sh`.
- `run_test.sh`는 루트 `.env`를 `source` 하고, mysql 컨테이너에 `GRANT ALL PRIVILEGES` 를 실행합니다(일반 유저가 `test` DB를 만들 수 있도록).
- `conftest.py`의 세션 단위 이벤트 루프/initializer 구성은 pytest-asyncio 버전과 엮여 있으니 **임의로 수정하지 마세요.**
- 테스트 클래스는 `tortoise.contrib.test.TestCase`를 상속하고, 테스트 간 이메일·전화번호 등 고유값이 겹치지 않게 작성하세요.
- 클라이언트는 `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` 패턴을 사용합니다.
- CI의 MySQL 서비스에는 healthcheck가 없어 간헐적으로 연결 실패가 날 수 있습니다.

### 4.7 AI Worker
- ✅ (2026-11-20 수정) 컨테이너 재시작 반복 문제 해결: Dockerfile이 `COPY ./ai_worker ./ai_worker` + `CMD ["uv", "run", "--no-sync", "python", "-m", "ai_worker.main"]`로 변경되었고, `main.py`는 SIGTERM까지 대기하는 루프입니다. 실제 작업 수신 로직은 통신 방식 확정 후 `run()`의 TODO 위치에 구현하세요.
- ✅ `ai_worker/core/__init__.py`는 이제 자신의 `ai_worker.core.config`/`logger`를 사용합니다. `ai_worker` 코드에서 `app.*`를 import하지 마세요(컨테이너에 `app` 코드가 없습니다).
- ✅ 로거 이름: API는 `"app"`, 워커는 `"AI Worker"`.
- torch 등 `ai` 그룹은 무겁습니다(CPU 인덱스 사용). 컨테이너 메모리 제한은 4G입니다.

### 4.8 배포 / 보안
- `deployment.sh`, `certbot.sh`의 `sed -i ''` 는 **macOS 전용** 문법입니다. Linux/WSL에서 실행하면 실패합니다.
- 스크립트는 `infra/nginx/prod_*.conf`의 `server_name`을 **로컬 파일에서 직접 수정**합니다. 실행 후 변경된 파일을 실수로 커밋하지 않도록 주의하세요.
- `deployment.sh`에서 Docker 로그인이 실패해도 `exit` 하지 않고 다음 단계로 진행합니다.
- 운영 compose가 `8000`(fastapi), `3306`(mysql), `6379`(redis, 비밀번호 없음)을 **호스트에 그대로 노출**합니다. EC2 보안 그룹에서 80/443(+22)만 열거나 compose의 `ports`를 제거하세요.
- 이미지 태그는 `app-v1.0.0`, `ai-v1.0.0` 형식입니다. 배포 시 입력한 버전과 `.prod.env`의 `APP_VERSION`/`AI_WORKER_VERSION`이 **일치해야** EC2에서 올바른 이미지를 pull합니다.
- 처방전·병명 등 **민감한 건강정보**를 다루게 됩니다. 업로드 이미지 저장소(S3) 접근 제어, 로그에 개인정보·처방 내용 출력 금지, 외부 LLM/OCR API로 보내는 데이터 최소화를 설계 단계에서 고려하세요.

### 4.9 Git / 협업
- 커밋 메시지: `.github/commit_template.txt` 규칙 (`✨ feat: ...`, `🐛 fix: ...`). 적용: `git config commit.template .github/commit_template.txt`
- PR은 `.github/PULL_REQUEST_TEMPLATE.md` 양식을 따릅니다.
- CI가 `develop`, `release/*`, `hotfix/*`를 대상으로 하므로 Git Flow(`feature/*` → `develop` → `main`) 사용을 전제로 합니다.
- 문서는 루트 `docs/`에 두세요.

---

## 5. 로컬 개발 빠른 시작 (체크리스트)

```bash
# 1) 의존성
uv sync --group app --group dev

# 2) 환경변수 (루트 .env 필요)
cp envs/example.local.env envs/.local.env
cp envs/.local.env .env          # SECRET_KEY, DB 비밀번호 수정

# 3) DB 기동
docker compose up -d mysql redis

# 4) 마이그레이션 적용
uv run aerich upgrade

# 5) 서버 실행 (DB_HOST=localhost)
uv run uvicorn app.main:app --reload
#   → http://localhost:8000/api/docs

# 6) 커밋 전
./scripts/ci/code_fommatting.sh
./scripts/ci/run_test.sh
```
