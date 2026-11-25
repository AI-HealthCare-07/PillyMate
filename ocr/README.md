# OCR 모듈 (AI-1)

처방전·약봉투 사진을 CLOVA OCR로 읽어 **API 명세 7절 `run_ocr()` 형식**의 dict로 돌려주는 모듈입니다.
BE-2가 `POST /prescriptions` 안에서 함수로 호출합니다. HTTP API가 아닙니다.
프론트엔드 연동(보내는 값, 받는 값, 화면 표시 규칙)은 `docs/PillyMate_OCR_모듈_프론트엔드_연동_안내.md`를 보세요.

- 동기 함수입니다 (명세 1절: OCR API는 `def`로 작성).
- 파이썬 기본 라이브러리만 씁니다. 추가로 설치할 패키지가 없습니다.
- `app`, `ai_worker` 코드를 import하지 않습니다. 반대로 `app`은 `from ocr import ...`로만 씁니다.

## BE-2: 호출 방법

```python
from ocr import OcrError, OcrInputError, run_ocr

def create_prescription(...):          # async def가 아니라 def
    try:
        result = run_ocr(image_bytes, source_type)   # "PRESCRIPTION" 또는 "PILL_BAG"
    except OcrInputError:
        ...  # 422 "jpg 또는 png 사진만 올릴 수 있어요."
    except OcrError:
        ...  # 502 "처방전을 읽지 못했어요. 다시 찍어 주세요." (처방 행을 만들지 않고 S3 이미지 삭제)
```

`async def` 안에서 불러야 한다면 서버가 멈추지 않도록 스레드로 넘겨 주세요.

```python
from fastapi.concurrency import run_in_threadpool
result = await run_in_threadpool(run_ocr, image_bytes, source_type)
```

### 반환 형식 (명세 7절)

```json
{
  "prescription_date": "2026-11-12",
  "hospital_name": "해솔소아청소년과의원",
  "diagnosis_extracted": "J00,J209",
  "medications": [
    { "name": "세파클러건조시럽(내복)/60(1)mL/병", "insurance_code": "643901230",
      "dose_per_time": 4.2, "unit": "mL", "daily_count": 3, "total_days": 5,
      "max_daily_count": null, "as_needed": false, "usage": "식후 30분",
      "route": "ORAL", "dosage_form": "DRY_SYRUP", "confidence": 0.95 }
  ]
}
```

- 모르는 값은 `null`입니다. 약을 하나도 못 읽으면 `medications`는 `[]`이고, 이건 예외가 아닙니다.
- `unit`: `mL`·`포`·`정`·`캡슐`·`g`·`방울`·`개` 중 하나 또는 `null` (11절)
- `route`: `ORAL`·`EXTERNAL` 또는 `null` / `dosage_form`: 11절 목록 또는 `null`
- `as_needed`가 `true`면 `daily_count`는 항상 `null`입니다.
- `confidence`: 그 약 줄에 있는 글자들의 CLOVA 인식 신뢰도 평균(0~1)
- 환자 성명·주민등록번호·나이·전화번호는 결과 어디에도 없습니다.
- **OCR 원문은 돌려주지 않습니다** (11/25 변경, 11/24 멘토링 4절 "필요한 데이터만 구조화해 저장").
  CLOVA가 읽은 글자 전체는 `run_ocr()` 안에서 파서에만 쓰이고 함수가 끝나면 사라집니다.
  예전 `raw_text_masked`(마스킹 원문) 키와 DB 컬럼은 없앴습니다.

### 신뢰도 판정 (`ocr/ocr_confidence_policy.py`)

`judge_ocr_confidence(result)` → `{"level", "min_confidence", "low_confidence_count"}`.
가장 낮은 약 신뢰도로 사진 전체를 판정합니다 (11/24 멘토링 3절 기준).

| 가장 낮은 약 신뢰도 | `level` | `POST /prescriptions` 처리 |
| --- | --- | --- |
| 0.8 이상 | `OK` | 저장, 그대로 확인 |
| 0.6 이상 ~ 0.8 미만 | `REVIEW` | 저장, 0.8 미만 약은 `low_confidence: true` → S-04에서 노란 표시로 직접 수정 |
| 0.6 미만, 또는 약을 하나도 못 읽음 | `RETAKE` | 저장하지 않고 사진 삭제, `422 {"code": "OCR_LOW_CONFIDENCE"}` → 다시 찍기 모달 |

기준값은 회의록대로 "실제 테스트 후 확정"이라 `RETAKE_BELOW`, `REVIEW_BELOW` 상수로 두었습니다.
샘플 30장 기준으로 `REVIEW`는 1장(rx_10, 최저 0.78), `RETAKE`는 0장입니다.

### 예외 (`ocr/ocr_exceptions.py`)

| 예외 | 언제 | 상태코드 |
| --- | --- | --- |
| `OcrInputError` | `source_type`이 틀림, jpg·png가 아님, 빈 파일 | 422 |
| `OcrConfigurationError` | CLOVA 환경변수 없음 | 502 |
| `OcrRequestError` | CLOVA 요청 실패, 시간 초과 (기본 25초) | 502 |
| `OcrRecognitionError` | CLOVA가 인식 실패, 글자가 하나도 없음 | 502 |
| `OcrParseError` | 읽은 글자를 항목으로 정리하다 실패 | 502 |

모든 예외는 `OcrError`를 상속합니다. 예외 메시지에는 읽은 글자(환자 정보)가 들어가지 않으니 로그에 남겨도 됩니다.
화면에 보여 줄 문구(`detail`)는 명세 8절의 문구를 쓰세요.

### 필요한 설정

| 무엇을 | 누가 | 내용 |
| --- | --- | --- |
| 환경변수 | BE-1·BE-2 | `CLOVA_OCR_URL`(APIGW Invoke URL), `CLOVA_OCR_SECRET` 를 `.env`·배포 서버에 추가 |
| `app/Dockerfile` | 반영됨 | `COPY ./ocr ./ocr` |
| `docker-compose.yml` | 반영됨 | fastapi 서비스에 `./ocr:/app/ocr` 볼륨 (로컬에서 수정 즉시 반영) |

환경변수 대신 값을 직접 넘길 수도 있습니다: `run_ocr(..., credentials=ClovaCredentials(url, secret))`.

## AI-1: 테스트 방법

모두 프로젝트 루트(`PillyMate/`)에서 실행합니다. CLOVA 키는 `~/ocr/.env`에 있다고 가정합니다.

**1) 자동 테스트 — 인터넷·키 필요 없음**

```bash
uv run pytest ocr
```

가짜 처방전·약봉투 배치(`tests/fake_clova_fields.py`)로 파서, 명세 형식, 신뢰도 판정, 예외를 확인합니다.

**2) 사진 한 장 실제로 돌려 보기 — CLOVA 1회 호출**

```bash
uv run --env-file ~/ocr/.env python -m ocr.tools.run_ocr_on_image ~/ocr/"PillyMate Image"/처방전/rx_01_scan.png --source-type PRESCRIPTION
```

**2-1) 브라우저에서 사진 올려 보기 — 사진마다 CLOVA 1회 호출**

```bash
uv run --env-file ~/ocr/.env python -m ocr.tools.ocr_preview_server
```

http://127.0.0.1:8010 에서 처방전·약봉투를 고르고 사진을 올리면 `run_ocr()` 결과를 표로 보여 줍니다.
신뢰도 판정(`OK`·`REVIEW`·`RETAKE`)이 함께 나오고, 기준값(기본 0.8) 미만인 약은 노란색으로 표시됩니다. API 서버(`app`)와 상관없이 혼자 돌아가는 개발용 도구입니다.

**3) 샘플 사진의 CLOVA 응답 저장 — 사진마다 1회 호출, 이미 저장한 사진은 건너뜀**

```bash
uv run --env-file ~/ocr/.env python -m ocr.tools.save_clova_responses --source-type PRESCRIPTION ~/ocr/"PillyMate Image"/처방전/*
uv run --env-file ~/ocr/.env python -m ocr.tools.save_clova_responses --source-type PILL_BAG ~/ocr/"PillyMate Image"/약봉투/*
```

`tests/clova_responses/`에 저장됩니다. 이후 파서를 고칠 때는 CLOVA를 다시 부르지 않고 저장한 응답으로 반복합니다.
저장할 때 환자 이름은 `홍길동`, 주민등록번호는 `000000-0000000`으로 바꿉니다 (`[이름]`처럼 `[`로 시작하면
약봉투 파서가 분류 칸으로 착각하므로 같은 모양의 가짜 값을 씁니다).

**4) 정확도 확인 — 인터넷 필요 없음**

```bash
uv run python -m ocr.tools.check_parser_accuracy --details
```

저장한 응답을 정리한 결과를 `tests/expected_results/`의 정답과 비교해 항목별 정확도를 보여 줍니다.
응답을 저장하고 나면 `uv run pytest ocr`도 사진별로 정답과 비교합니다.

> `expected_results/`는 `~/ocr`의 `*_OCR결과.md`(기존 파서 결과)를 명세 형식으로 옮긴 뒤,
> 사진과 대조해 틀린 값(rx_14 질병분류기호, 약 이름 OCR 오타 8개)을 고친 것입니다.
> 나머지 값은 전부 대조하지는 않았으니, 틀린 값을 발견하면 정답 파일을 직접 고쳐 주세요.

2026-11-24 샘플 30장 기준 결과: 약 이름을 뺀 모든 항목 100%,
약 이름은 처방전 45/52(86.5%)·약봉투 51/52(98.1%). 틀린 이름은 모두 CLOVA가 글자 한두 개를 잘못 읽은 경우입니다
(`밀리그램 → 밀리그림`, `사카로마이세스 → 사카로아이세스`, `돔페리돈 → 동페리돈`, `건조시럽 → 건조사립` 등).
`uv run pytest ocr`는 이런 이름 오타(유사도 85% 이상)는 통과시키고 나머지 항목은 정확히 비교합니다.

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `ocr_pipeline.py` | `run_ocr()`: 사진 → CLOVA → 파서 → 명세 형식 (원문은 버림) |
| `ocr_confidence_policy.py` | 신뢰도 판정 `judge_ocr_confidence()` (OK·REVIEW·RETAKE) |
| `clova_ocr_client.py` | CLOVA OCR(General V2) 동기 호출, 타임아웃, 오류 변환 |
| `ocr_exceptions.py` | `OcrError`와 하위 예외 |
| `text_layout_utils.py` | 기울기 보정, 좌표로 행 묶기, 신뢰도 평균 |
| `prescription_parser.py` | 처방전 양식 → 항목(한글 키) |
| `medicine_bag_parser.py` | 약봉투(영수증 + 복약안내) → 항목(한글 키) |
| `personal_info_masking.py` | 테스트용 CLOVA 응답을 저장할 때(`tools/save_clova_responses.py`) 이름·주민등록번호 등을 가림 |
| `ocr_result_formatter.py` | 한글 키 → 명세 snake_case, 제형·경로·단위 추정 |
| `tools/` | AI-1용 명령줄 도구 (위 테스트 방법 2~4) |
| `tests/` | pytest 테스트, 가짜 CLOVA 응답, 정답 파일 |

## 팀과 정할 것

- `diagnosis_extracted`: 질병분류기호가 여러 개면 `"J00,J209"`처럼 쉼표로 잇습니다. BE-2 DB 컬럼 길이 확인 필요.
- 약봉투 `prescription_date`: 약봉투에는 조제일자만 있어서 `null`로 둡니다. 조제일자를 대신 넣을지 FE-2와 결정 필요.
- 처방전 약 이름은 `세파클러건조시럽(내복)/60(1)mL/병`처럼 인쇄된 그대로 둡니다 (함량 정보 보존).
- 허용 목록에 없는 단위(`관`, `분무`, `흡입`)는 `null`입니다. 목록에 추가할지 BE-2·FE-2와 결정 필요.
- 신뢰도 기준값(0.6 / 0.8)은 멘토링 논의 기준을 그대로 쓴 것이라, 실제 촬영 사진으로 다시 확인해야 합니다.
  참고로 0.9로 강조하면 샘플에서 강조 6개 중 5개가 실제 오타였고, 0.8이면 1개만 잡혔습니다.
- 필요시 복용약의 `max_daily_count`는 "1일 최대 n회"가 적혀 있을 때만 채웁니다. 없으면 보호자가 S-04에서 입력합니다.
  샘플 30장의 필요시 약 15개 중 이 문구가 적힌 것은 없어서, 지금은 전부 보호자가 입력해야 합니다.
- 약 이름 OCR 오타: 처방전의 `insurance_code`(9자리 보험코드)는 정확히 읽히므로, 보험코드로 공식 약 이름을
  찾아 바로잡는 방법을 검토할 수 있습니다 (심평원 약가 마스터 등).
