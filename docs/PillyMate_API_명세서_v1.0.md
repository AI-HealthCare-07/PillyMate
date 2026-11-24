# PillyMate 1차 MVP API 명세서 v1.0 (제출본)

2026-11-23 · 작성: BE-1 강선영 · 기준: 종부님(BE-2) 초안(11/20)과 AI-2 v0.2(11/19)를 통합한 v0.3, 보완 사항 반영, 팀 채택

## 개요

1차 MVP는 **핵심 API 10개**로 로그인 → 자녀 등록 → 처방전 등록·OCR → 처방 확정 → 가이드 생성까지 연결합니다. 인증은 BE-1, 나머지 핵심 API는 BE-2가 구현합니다. 시연에 필요한 추가 API 2개(데모 로그인, 내 정보)는 BE-1이 함께 구현합니다.

## 0. 확정 사항

| 항목 | 결정 | 확정일 |
| --- | --- | --- |
| 회원가입 항목 | 이메일·비밀번호·**이름·생년월일** (네 항목 모두 필수) | 11/20 |
| 오래 걸리는 요청 | **동기 처리** (OCR 최대 30초, 가이드 최대 60초) | 11/20 |
| 자녀 등록 연령 | **만 18세 미만 미성년자**만 등록 가능 (NFR-SEC-004) | 11/17 확정 (회의록) |
| 원본 이미지 보관 | **가이드 생성 시 삭제**, 가이드를 만들지 않은 사진은 **7일 뒤 자동 삭제** (NFR-SEC-007) | 11/23 채택 |
| 로그인 방식 | 1차는 이메일·비밀번호 로그인과 데모 로그인. 소셜 로그인(카카오·구글)은 2차 | 11/24 결정 |
| 웹 푸시 알림 | **1차 포함**. 알림 API는 2절 P 항목에 자리를 두고, 상세 명세는 추가 작성 | 11/24 결정 |

## 1. 공통 규칙

| 항목 | 규칙 |
| --- | --- |
| 기본 주소 | 로컬 `http://127.0.0.1:8000/api/v1`, 배포 주소는 BE-1이 확정 (HTTPS) |
| 데이터 형식 | JSON (처방전 등록만 `multipart/form-data`), 필드 이름은 DB와 같은 `snake_case` |
| 인증 | 회원가입·로그인·데모 로그인 외 모든 API는 헤더에 `Authorization: Bearer <access_token>` |
| 토큰 | 유효시간 12시간, 리프레시 토큰 없음. 로그아웃은 FE가 토큰을 삭제하는 것으로 처리 |
| 권한 | 내 자녀·내 처방전만 조회·수정. 남의 데이터는 `404` (존재 여부를 알리지 않음) |
| 에러 형식 | `{"detail": "한국어 메시지"}` (FastAPI 기본). 메시지는 "~해요" 말투로 통일 |
| 날짜·시각 | 날짜 `YYYY-MM-DD`, 일시 ISO 8601 + KST (`2026-11-20T10:30:00+09:00`) |
| ID | 모두 정수 (DB AUTO_INCREMENT) |
| DB | MySQL 8.0 · Tortoise ORM(asyncmy 드라이버) · aerich 마이그레이션 (저장소 기존 세팅 기준) |
| 오래 걸리는 요청 | **동기 처리.** OCR 최대 30초, 가이드 최대 60초. 넘으면 `502` |
| 명세 확인 | 서버 실행 후 `/docs`(Swagger)에서 실제 요청·응답 확인 |

FastAPI가 자동으로 내는 입력 형식 오류(422)는 `detail`이 목록(`[{"loc": [...], "msg": "..."}]`)으로 옵니다. FE는 `detail`이 문자열이면 그대로, 목록이면 "입력 내용을 확인해 주세요."로 보여 줍니다.

### 동기 처리 구현 메모

| 담당 | 할 일 |
| --- | --- |
| BE-1 | 배포 서버(nginx) 대기 시간 90초 이상 (기본 60초면 가이드 생성 중 연결이 끊김) |
| BE-2 | OCR·가이드 API는 `async def`가 아닌 `def`로 작성. `async def` 안에서 오래 걸리는 호출을 하면 다른 사용자의 요청까지 함께 멈춤. `def`로 쓰면 FastAPI가 별도 스레드에서 처리 |
| FE-1·FE-2 | 요청 타임아웃 90초 이상, 기다리는 동안 로딩 화면 표시(NFR-PERF-001), 생성 중 버튼 비활성화(중복 요청 방지) |

## 2. API 목록

| # | 메서드 | 경로 | 기능 | 담당 | 우선순위 | 화면 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POST | `/auth/signup` | 회원가입 | BE-1 | P0 | S-01 |
| 2 | POST | `/auth/login` | 로그인, 토큰 발급 | BE-1 | P0 | S-01 |
| 3 | POST | `/children` | 자녀 등록 | BE-2 | P1 | S-02 |
| 4 | GET | `/children` | 내 자녀 목록 | BE-2 | P1 | S-02, S-03 |
| 5 | POST | `/prescriptions` | 처방전 이미지 등록 + OCR | BE-2 | P1 | S-03 |
| 6 | GET | `/prescriptions/{prescription_id}` | 처방전 상세 (OCR 결과, 원본 이미지 주소) | BE-2 | P1 | S-04 |
| 7 | PUT | `/prescriptions/{prescription_id}/confirm` | 보호자 수정본 확정 + 병명 저장 | BE-2 | P1 | S-04 |
| 8 | POST | `/prescriptions/{prescription_id}/guide` | 가이드 생성 | BE-2 | P1 | S-05 |
| 9 | GET | `/prescriptions/{prescription_id}/guide` | 가이드 조회 | BE-2 | P1 | S-05 |
| 10 | GET | `/children/{child_id}/prescriptions` | 자녀별 처방전 목록 (이력) | BE-2 | P2 | S-07 |
| A1 | POST | `/auth/demo-login` | 시연용 데모 계정 로그인 | BE-1 | P1 | S-01 |
| A2 | GET | `/me` | 내 정보 | BE-1 | P2 | 공통 |
| P | POST 외 | `/push/tokens` 외 알림 API (P1~P6) | 웹 푸시 알림. 상세 요청·응답은 추가 작성 필요 | 담당 협의 | P1 | S-03, S-05 |

가이드는 처방전과 1:1 관계이므로 처방전 경로 아래에 둡니다.

## 3. 인증 API (BE-1)

### 1. `POST /auth/signup` 회원가입

네 항목 모두 필수입니다.

```json
// 요청
{ "email": "parent@example.com", "password": "pilly1234!", "name": "김보호", "birth_date": "1990-05-14" }

// 응답 201
{ "guardian_id": 1, "email": "parent@example.com", "name": "김보호", "birth_date": "1990-05-14" }
```

- 비밀번호 8~64자, bcrypt 해시로 저장
- 이메일은 소문자로 바꿔 저장 (대소문자 구분 없이 로그인)
- 만 19세 미만이면 `422` "만 19세 이상만 가입할 수 있어요." (NFR-SEC-005)
- 에러: `409` 이미 가입된 이메일, `422` 이메일 형식·비밀번호 규칙·날짜 형식·필수값 누락·나이 제한

### 2. `POST /auth/login` 로그인

```json
// 요청
{ "email": "parent@example.com", "password": "pilly1234!" }

// 응답 200
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 43200,
  "guardian": { "guardian_id": 1, "name": "김보호", "child_count": 2 }
}
```

- `child_count`가 0이면 FE-1은 처방전 업로드 대신 자녀 등록(S-02)으로 보냅니다.
- 에러: `401` 이메일 또는 비밀번호 불일치 (어느 쪽이 틀렸는지 알려 주지 않음)

### A1. `POST /auth/demo-login` 데모 로그인

요청 본문 없음. 미리 넣어 둔 데모 보호자(DATA-SAMPLE-004)로 로그인하며, 응답은 로그인과 같습니다. 배포 환경에서는 환경변수 `DEMO_LOGIN_ENABLED=false`로 끌 수 있고, 꺼져 있으면 `404`입니다.

### A2. `GET /me` 내 정보

```json
// 응답 200
{ "guardian_id": 1, "email": "parent@example.com", "name": "김보호", "birth_date": "1990-05-14", "created_at": "2026-11-20T10:00:00+09:00" }
```

앱을 다시 열었을 때 저장된 토큰이 유효한지 확인하는 데 씁니다. `401`이면 로그인 화면으로 보냅니다.

## 4. 자녀 API (BE-2)

### 3. `POST /children` 자녀 등록

`name`, `birth_date`, `consent_agreed` 필수, 나머지 선택. 체중 단위는 kg입니다.

```json
// 요청
{ "name": "민준", "birth_date": "2021-03-02", "consent_agreed": true, "weight_kg": 18.5, "allergies": "계란", "notes": "열성 경련 이력 있음" }

// 응답 201
{
  "child_id": 3, "name": "민준", "birth_date": "2021-03-02", "weight_kg": 18.5,
  "allergies": "계란", "notes": "열성 경련 이력 있음", "created_at": "2026-11-20T10:30:00+09:00"
}
```

- 미래 생년월일이면 `422`
- `consent_agreed`는 USER-003의 동의 3항목을 모두 체크했을 때만 `true`로 보냅니다. 화면(FE-1)에서 3개 중 하나라도 빠지면 등록 버튼이 비활성화됩니다. 서버는 `true`일 때 동의 시각을 `child.consent_agreed_at`에 저장하고, `false`이면 `422`를 반환합니다.
- 만 18세 이상이면 `422` (자녀 등록 연령: 만 18세 미만 미성년자, 11/17 확정)
- `weight_kg`는 0.5~150
- 에러: `401` 로그인 필요, `422` 필수값 누락·날짜 형식 오류·동의 없음·나이 제한

### 4. `GET /children` 내 자녀 목록

로그인한 보호자의 자녀만 등록 순서대로 반환합니다. 없으면 `[]`.

```json
[ { "child_id": 3, "name": "민준", "birth_date": "2021-03-02", "weight_kg": 18.5 } ]
```

## 5. 처방전 API (BE-2 + AI-1)

약 항목(`medications`) 필드는 AI-1의 OCR 결과 형식(7절)과 같습니다.

### 5. `POST /prescriptions` 처방전 등록 + OCR

`multipart/form-data`

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `child_id` | O | 어느 자녀의 처방인지 |
| `source_type` | O | `PRESCRIPTION`(처방전) 또는 `PILL_BAG`(약봉투) |
| `image` | O | jpg·png, 10MB 이하 |
| `diagnosis_user_input` | | 병명. 여기서 비어 있어도 확정 단계에서 필수 |
| `symptom_notes` | | 증상·특이사항 |

처리 순서 (요청 하나 안에서 끝나며 최대 30초):
1. `child_id`가 내 자녀인지 확인 → 아니면 `404`
2. 형식·용량 검사 → 아니면 `422`
3. S3 저장 (BE-1 `upload_image()`, 키 `prescriptions/{child_id}/{무작위값}.jpg`)
4. AI-1 `run_ocr()` 호출 (마스킹까지 모듈 안에서 처리)
5. OCR 성공 시 `prescription`(`status = OCR_DONE`)과 `medication` 행 저장
6. 6번과 같은 형식으로 응답 `201`

- OCR이 실패하거나 30초를 넘기면 **처방 행을 만들지 않고**, S3 이미지도 삭제한 뒤 `502`를 응답합니다. FE-2는 "다시 찍기"를 보여 줍니다.
- 서버 로그에 OCR 원문을 남기지 않습니다.
- 에러: `404` 내 자녀가 아님, `422` 파일 형식·용량 오류, `502` OCR 실패·시간 초과

### 6. `GET /prescriptions/{prescription_id}` 처방전 상세

```json
{
  "prescription_id": 12,
  "child_id": 3,
  "source_type": "PRESCRIPTION",
  "status": "OCR_DONE",
  "prescription_date": "2026-11-19",
  "hospital_name": "행복소아과의원",
  "diagnosis_extracted": "J06",
  "diagnosis_user_input": null,
  "symptom_notes": null,
  "image_url": "https://...(presigned URL, 10분 유효)",
  "has_guide": false,
  "created_at": "2026-11-20T10:30:00+09:00",
  "medications": [
    {
      "medication_id": 41,
      "name": "타이레놀현탁액",
      "insurance_code": "648500030",
      "dose_per_time": 5.0,
      "unit": "mL",
      "daily_count": 3,
      "total_days": 3,
      "as_needed": false,
      "max_daily_count": null,
      "usage": "식후 30분",
      "route": "ORAL",
      "dosage_form": "SYRUP",
      "confidence": 0.93,
      "is_user_edited": false
    }
  ]
}
```

- `diagnosis_extracted`는 처방전의 질병분류기호이며 **참고용**입니다. 병명으로 쓰지 않습니다 (요구사항 v1.4).
- `image_url`은 S-04에서 원본과 대조할 때만 씁니다. 가이드 생성 후 원본을 지우면 `null`입니다.
- `confidence`가 낮은 항목은 S-04에서 강조합니다 (기준값은 FE-2·AI-1이 정함).
- 환자 성명·주민등록번호는 응답에 포함하지 않습니다. 마스킹 원문(`raw_text_masked`)도 내려주지 않고 DB에만 저장합니다.
- 에러: `404` 없거나 내 처방전이 아님

### 7. `PUT /prescriptions/{prescription_id}/confirm` 처방 확정

보호자가 고친 최종 약 목록과 병명을 통째로 보냅니다. 서버는 기존 목록을 이 내용으로 바꾸고 `status = CONFIRMED`로 변경합니다. `medication_id`가 없는 항목은 새로 추가하고, 빠진 항목은 삭제합니다.

```json
// 요청
{
  "prescription_date": "2026-11-19",
  "hospital_name": "행복소아과의원",
  "diagnosis_user_input": "목감기, 접촉성 피부염",
  "symptom_notes": "밤에 기침이 심함",
  "medications": [
    { "medication_id": 41, "name": "타이레놀현탁액", "dose_per_time": 5.0, "unit": "mL",
      "daily_count": null, "total_days": 3, "as_needed": true, "max_daily_count": 4,
      "usage": "열날 때", "route": "ORAL", "dosage_form": "SYRUP" },
    { "medication_id": null, "name": "리도멕스크림", "dose_per_time": null, "unit": null,
      "daily_count": 2, "total_days": 7, "as_needed": false, "max_daily_count": null,
      "usage": "하루 2번 바르기", "route": "EXTERNAL", "dosage_form": "CREAM" }
  ]
}
// 응답 200: 6번과 같은 형식, status = "CONFIRMED"
```

검증 규칙:
- 상태가 `OCR_DONE` 또는 `CONFIRMED`일 때만 가능. 이미 가이드가 생성됐으면(`GUIDE_DONE`) `409`
- `diagnosis_user_input` 필수, 없으면 `422` (DB에도 CHECK 제약)
- 약은 1개 이상. 각 약은 `name`·`route`·`dosage_form` 필수
- `as_needed: true`이면 `daily_count`는 `null`, `max_daily_count` 필수
- `route: "EXTERNAL"`(외용제)이면 `dose_per_time`을 가이드에서 "한 번에 바를 양"으로 안내하지 않음 (NFR-SAFE-004)
- 요청의 `medication_id`가 이 처방의 약이 아니면 `422` (다른 처방의 약은 고칠 수 없음)
- OCR 원래 값과 달라진 항목은 서버가 `is_user_edited: true`로 바꾸며, `ocr_value_snapshot`은 변경하지 않음
- 약 목록 교체와 상태 변경은 한 트랜잭션으로 처리 (중간에 실패하면 모두 원래대로)
- 에러: `404` 없거나 내 처방전이 아님, `409` 이미 가이드가 생성된 처방, `422` 병명 누락·약 목록 비어 있음·필수 필드 누락

### 10. `GET /children/{child_id}/prescriptions` 처방전 목록 (P2)

S-07 이력 화면용이며 최신순으로 반환합니다.

```json
[
  { "prescription_id": 12, "status": "GUIDE_DONE", "prescription_date": "2026-11-19",
    "diagnosis_user_input": "목감기, 접촉성 피부염", "hospital_name": "행복소아과의원",
    "medication_count": 2, "created_at": "2026-11-20T10:30:00+09:00" }
]
```

에러: `404` 내 자녀가 아님

## 6. 가이드 API (BE-2 + AI-2)

### 8. `POST /prescriptions/{prescription_id}/guide` 가이드 생성

요청 본문 없음. 서버가 DB에서 자녀 정보·확정 처방·병명을 조회해 AI-2 모듈에 넘기고, 결과를 저장한 뒤 돌려줍니다. 최대 60초.

```json
// 응답 201 (새로 생성) / 200 (이미 있어 기존 것 반환)
{
  "guide_id": 7,
  "prescription_id": 12,
  "created_at": "2026-11-20T10:31:00+09:00",
  "guide_content": { "...": "AI-2 가이드 JSON 스키마를 그대로 따름" }
}
```

처리 순서:
1. 상태가 `CONFIRMED` 또는 `GUIDE_DONE`인지 확인 → 아니면 `409` (확정 전 OCR 결과로는 만들지 않음, NFR-SAFE-003)
2. 이미 가이드가 있으면 새로 만들지 않고 `200`과 기존 가이드 반환
3. AI-2 `generate_guide()` 호출
4. `guide` 저장과 `status = GUIDE_DONE` 변경을 **한 트랜잭션**으로 처리
5. S3 원본 이미지 삭제 (0절 보관 정책)
6. `201`로 응답

- LLM이 실패해도 AI-2 모듈이 기본 가이드를 반환하므로 대개 성공합니다. 모듈 자체가 실패하거나 60초를 넘기면 상태는 `CONFIRMED`를 유지하고 `502`를 응답합니다. FE는 "다시 만들기"(8번 재호출)를 보여 줍니다.
- 같은 처방에 요청이 동시에 두 번 들어오면(버튼을 두 번 누른 경우) `guide.prescription_id`의 UNIQUE 제약으로 하나만 저장됩니다. 저장에 실패한 쪽은 오류 대신 먼저 저장된 가이드를 `200`으로 받습니다.
- 에러: `404` 없거나 내 처방전이 아님, `409` 아직 확정되지 않은 처방, `502` LLM 실패·시간 초과

### 9. `GET /prescriptions/{prescription_id}/guide` 가이드 조회

응답 `200`은 8번과 같은 형식입니다. 에러: `404` 가이드가 아직 없거나 내 처방전이 아님

### `guide_content` 형식

AI-2의 가이드 JSON 스키마를 따릅니다 (AI-2·FE-1 합의). 아래 두 항목은 반드시 포함되며, FE-1은 **항상 보이도록** 표시합니다 (NFR-SAFE-001).
- `warning_signs`: 바로 병원에 가야 하는 신호
- `disclaimer`: "의료진의 진단·처방을 대신하지 않습니다"라는 안내

## 7. 내부 모듈 (HTTP 아님, BE-2가 함수로 호출)

### AI-1 `run_ocr(image_bytes, source_type) -> dict`

```json
{
  "prescription_date": "2026-11-19",
  "hospital_name": "행복소아과의원",
  "diagnosis_extracted": "J06",
  "raw_text_masked": "환자 성명 [이름] 주민등록번호 [주민번호] ...",
  "medications": [
    { "name": "타이레놀현탁액", "insurance_code": "648500030", "dose_per_time": 5.0, "unit": "mL",
      "daily_count": 3, "total_days": 3, "max_daily_count": null, "as_needed": false,
      "usage": "식후 30분", "route": "ORAL", "dosage_form": "SYRUP", "confidence": 0.93 }
  ]
}
```

- 모르는 값은 `null`입니다. 약봉투는 병원명·처방일·질병분류기호가 없을 수 있습니다.
- 식별정보는 함수 안에서 `[이름]`, `[주민번호]`처럼 바꾸고, 원문은 밖으로 내보내지 않습니다 (NFR-SEC-007).
- 실패하면 예외를 던집니다. BE-2는 30초 타임아웃 안에서 호출합니다.

### AI-2 `generate_guide(child, prescription, medications) -> dict`

| 인자 | BE-2가 넘기는 값 |
| --- | --- |
| `child` | `{ "age_months", "weight_kg", "allergies", "notes" }` (이름·생년월일은 넘기지 않음) |
| `prescription` | `{ "prescription_id", "diagnosis_user_input", "symptom_notes" }` |
| `medications` | 확정된 약 목록 (7번 요청의 `medications` + `medication_id`) |

- 반환값은 `guide_content` 그대로 저장합니다. 스키마 검증은 모듈 안에서 끝냅니다.
- 모듈 안에서 LLM 재시도는 1회이며 호출당 25초 제한을 둡니다. 실패하면 기본 가이드를 반환합니다. 전체 60초 안에 끝냅니다.
- LLM 키는 환경변수 `ANTHROPIC_API_KEY`로 설정합니다 (BE-1이 배포 환경에 설정).
- `weight_kg`는 참고용입니다. 가이드에서 체중으로 용량을 계산해 안내하지 않으며, 용량은 처방 확정값만 사용합니다 (NFR-SAFE-002).

## 8. 처방 상태와 에러 코드

처방 상태는 아래 순서로만 바뀝니다.

```
(OCR 성공 시 행 생성) OCR_DONE → CONFIRMED → GUIDE_DONE
                                    ↑    │
                                    └────┘ 가이드 생성 실패 시 CONFIRMED 유지
```

| 상태 | 바뀌는 시점 |
| --- | --- |
| `OCR_DONE` | 5번에서 이미지 저장과 OCR이 끝나고 행이 만들어질 때 |
| `CONFIRMED` | 7번에서 약 목록·병명 확정. 병명이 없으면 이 상태가 될 수 없음 |
| `GUIDE_DONE` | 8번에서 가이드 저장 |

| 코드 | 의미 | 예 |
| --- | --- | --- |
| 401 | 로그인 필요 | 토큰 없음·만료 |
| 404 | 없거나 남의 데이터 | 다른 보호자의 자녀 조회 |
| 409 | 중복·상태 충돌 | 가입된 이메일, 확정 전 가이드 요청, 가이드 생성 후 재확정 |
| 422 | 입력 오류 | 병명 누락, 날짜 형식, 나이 제한, 파일 형식·용량 |
| 502 | 외부 호출 실패 | OCR 30초·가이드 60초 초과, OCR·LLM 오류 |

## 9. 1차 이후 (범위 밖)

| 경로 (안) | 기능 | 비고 |
| --- | --- | --- |
| `GET·PATCH·DELETE /children/{child_id}` | 자녀 상세·수정·삭제 | 요구사항 USER-003. 삭제 시 처방·가이드·S3 이미지 함께 삭제 |
| `DELETE /prescriptions/{prescription_id}` | 이력 삭제 | 요구사항 MED-002 |
| 소셜 로그인 (카카오·구글) | 2차 기능. 1차는 이메일·비밀번호와 데모 로그인 (0절) | 11/17 S-01 화면 기준 |
| `POST /prescriptions/{id}/chat` | 챗봇 | 1차는 화면만 |
| 복약 체크, 공유 링크, 투약의뢰서 | 선택 기능 | 요구사항 선택 기능 |

## 10. 이 명세를 위해 필요한 DB 변경

| 변경 | 쓰는 API | 담당 |
| --- | --- | --- |
| `guardian.name`, `guardian.birth_date` 추가 | 1, 2, A1, A2 | BE-2 (스키마) |
| `medication.route`, `medication.dosage_form` 추가 | 5, 6, 7, 8 | BE-2 |
| `medication.ocr_value_snapshot`, `medication.is_user_edited` 추가 | 6, 7 | BE-2 |
| `diagnosis_user_input` 필수 CHECK (`CONFIRMED`·`GUIDE_DONE`일 때) | 7 | BE-2 |
| `child.consent_agreed_at` 추가 | 3 | BE-2 |
| `prescription.image_storage_key` NULL 허용 (원본 삭제 후 비움) | 6, 8 | BE-2 (현 스키마 그대로 가능) |
| `prescription.status`의 `UPLOADED`·`FAILED` | 5, 8 | 1차 흐름에서는 쓰지 않으며, CHECK 목록에만 남김 |
| 데모 보호자·자녀 시드 데이터 | A1 | BE-1(보호자), BE-2(자녀·처방 예시) |

DB 변경은 aerich 마이그레이션으로 추가합니다 (`aerich migrate` → `aerich upgrade`, 초기 세팅 BE-1, 이후 변경 BE-2).

## 11. 결정 사항 (채택, 11/23 · 11/24 추가)

| 항목 | 결정 | 담당 |
| --- | --- | --- |
| 기본 주소 | `/api/v1` 붙임 (FE 전체 요청 주소) | 전체 |
| 약 항목 필드 | DB 컬럼 이름 그대로. `name` 외에는 비워도 됨. 단위는 `mL`·`포`·`정`·`캡슐`·`g`·`방울`·`개` | AI-1, BE-2 |
| `route`·`dosage_form` 값 | `route` = `ORAL`·`EXTERNAL`. `dosage_form` = `SYRUP`·`DRY_SYRUP`·`POWDER`·`TABLET`·`CAPSULE`·`OINTMENT`·`CREAM`·`EYE_DROP`·`SUPPOSITORY`·`ETC`. 제형을 고르면 `route`는 자동 결정 | AI-1, BE-2, FE-2 |
| `guide_content` 형식 | AI-2 스키마 기준. `summary`·`medications`·`warning_signs`·`care_tips`·`disclaimer` 고정 | AI-2, FE-1 |
| 상태값 `UPLOADED` | 쓰지 않음. CHECK 목록에는 남김 | BE-2 |
| 병명 입력 위치 | S-04에서만 입력 (요구사항 v1.4). API는 등록·확정 둘 다 받음 | FE-2 |
| 원본 이미지 보관 | 가이드 생성 시 삭제, 가이드를 만들지 않은 사진은 7일 뒤 자동 삭제 | 전체 (NFR-SEC-007) |
| 자녀 등록 연령 | 만 18세 미만 미성년자만 등록. 14세 기준으로 나누지 않고 전체 같은 동의 흐름 적용 (11/24 결정) | 전체 (NFR-SEC-004) |
| 자녀 등록 동의 | 동의 3항목 모두 필수. 화면에서 3개를 모두 체크해야 `consent_agreed: true`로 전송하고, 서버는 하나의 불리언만 받음. 미동의 `422`, 동의 시각 저장 | BE-2, FE-1 (USER-003) |
| 로그인 방식 | 1차는 이메일·비밀번호와 데모 로그인. 소셜 로그인은 2차 | BE-1, FE-1 |
| 웹 푸시 알림 | 1차 포함 (11/24 결정). 알림 API 상세 명세는 추가 필요 | 전체 |

### 미정 항목

- 없음. 자녀 등록 동의 3항목(USER-003)은 모두 체크해야 `consent_agreed: true`로 전송하는 방식으로 정해졌습니다 (11/24 결정).

## 부록 A. 정린님 초안 대비 변경 사항과 이유

정린님 초안(11/20)을 기준으로 했으며, 아래는 바꾸거나 더한 항목입니다.

| # | 항목 | 초안 | 제출본 | 이유 |
| --- | --- | --- | --- | --- |
| 1 | 기본 주소 | `http://127.0.0.1:8000` + `/auth/signup` | `/api/v1` 추가 | 배포 시 FE와 BE를 같은 도메인에 두고 nginx가 `/api/`로 나눕니다. 나중에 붙이면 FE의 모든 요청 주소를 고쳐야 하므로 지금 붙입니다. 버전(`v1`)이 있으면 2차에서 형식이 바뀌어도 기존 화면이 깨지지 않습니다 |
| 2 | 처방일 필드명 | `prescribed_date` | `prescription_date` | DB 컬럼명이 `prescription_date`입니다. "필드 이름은 DB와 같은 snake_case"라는 공통 규칙에 맞춥니다 |
| 3 | 단위 표기 | `ml` | `mL` | 의약품 표기 관례이며, 처방전·약봉투에도 대부분 `mL`로 적혀 있어 OCR 결과를 그대로 쓸 수 있습니다 |
| 4 | 로그인 응답 | `access_token`, `token_type` | + `expires_in`, `guardian{guardian_id, name, child_count}` | `child_count`가 0이면 FE-1이 자녀 등록(S-02)으로 보낼 수 있습니다 (USER-003). 이름은 화면 상단에 표시합니다. 로그인 직후 추가 호출이 필요 없습니다. 기존 두 필드는 그대로입니다 |
| 5 | 만 19세 확인 | 없음 | 19세 미만이면 `422` | 보호자는 만 19세 이상이어야 합니다 (NFR-SEC-005). 생년월일을 받으므로 서버에서 확인합니다 |
| 6 | 비밀번호 규칙 | "비밀번호 규칙" | 8~64자 | FE-1의 입력 검증과 기준을 맞추기 위해 명시했습니다 |
| 7 | 이메일 | 언급 없음 | 소문자로 저장 | `Mom@a.com`과 `mom@a.com`이 다른 계정이 되는 것을 막습니다 |
| 8 | 추가 API | 없음 | `POST /auth/demo-login`, `GET /me` | 데모 로그인은 시연용 원클릭 로그인(USER-001)입니다. 데모데이에 가입 없이 바로 시연할 수 있습니다. `/me`는 저장된 토큰이 유효한지 확인하는 데 씁니다 |
| 9 | 처방 등록 필드 | `child_id`, `source_type`, `image`, `diagnosis_user_input` | + `symptom_notes` | DB에 `symptom_notes` 컬럼이 있으며 가이드 생성 재료로 씁니다 |
| 10 | OCR 실패 시 S3 이미지 | 언급 없음 | 삭제 | 처방 행을 만들지 않으므로 사진을 가리킬 곳이 없습니다. 삭제하지 않으면 개인정보가 담긴 사진이 S3에 남습니다 |
| 11 | 처방 상세 응답 | 등록 응답 + `image_url` | + `diagnosis_extracted`, `symptom_notes`, `has_guide`, `created_at` | `has_guide`로 FE가 S-04와 S-05 중 어디로 갈지 정합니다. `diagnosis_extracted`는 S-04에서 "처방전에서 읽은 기호"로 참고 표시합니다 (요구사항 v1.4) |
| 12 | 처방 확정 요청 | 병명, 약 목록 | + `prescription_date`, `hospital_name`, `symptom_notes` | OCR이 병원명·처방일을 잘못 읽었을 때 보호자가 S-04에서 고칠 수 있어야 합니다 |
| 13 | 처방 확정 검증 | 병명 누락, 약 목록 비어 있음 | + 약마다 `name`·`route`·`dosage_form` 필수, `as_needed`면 `max_daily_count` 필수 | 외용제는 "한 번에 바를 양"을 숫자로 안내하면 안 되므로(NFR-SAFE-004) `route`가 반드시 있어야 구분할 수 있습니다. 복용약은 하루 최대 횟수가 있어야 안전 안내를 할 수 있습니다 |
| 14 | 다시 확정 | 가이드 생성 후 `409` | `OCR_DONE`·`CONFIRMED`에서 가능, 가이드 생성 후 `409` | 확정 후 가이드를 만들기 전에 틀린 값을 발견하면 고칠 수 있어야 합니다. 초안의 409 규칙은 그대로입니다 |
| 15 | 가이드 생성 실패 | `502` | `502` + 상태 `CONFIRMED` 유지 | FE가 같은 API를 다시 호출하면 되므로 별도 실패 상태나 컬럼이 필요 없습니다 |
| 16 | `guide_content` 예시 | `summary`, `medications`, `care_tips`, `warning_signs`, `disclaimer` | AI-2 스키마를 따르며 `warning_signs`·`disclaimer` 필수 | 내부 형식은 AI-2·FE-1이 정하기로 한 초안의 원칙을 따랐습니다. 두 항목은 항상 보여야 하므로(NFR-SAFE-001) 빠지면 안 됩니다 |
| 17 | 이력 목록 응답 | `prescription_id`, `status`, 병명, 병원명, `created_at` | + `prescription_date`, `medication_count` | 이력 화면(S-07)은 진료 날짜로 찾는 경우가 많습니다. 업로드 날짜(`created_at`)와 진료 날짜는 다를 수 있습니다 |
| 18 | 내부 모듈 | 없음 | AI-1 `run_ocr()`, AI-2 `generate_guide()` 입출력 (7절) | BE-2가 AI 모듈을 함수로 호출하므로 입출력이 정해져야 서로 기다리지 않고 개발할 수 있습니다 |
| 19 | 원본 이미지 보관 | 미정 | 가이드 생성 시 삭제 + 7일 자동 삭제 (0절) | 원본 사진에 아이 이름·주민번호가 그대로 있습니다 (NFR-SEC-007) |

### 초안에서 가져오지 않은 항목 (AI-2 v0.2 기준)

| v0.2 내용 | 가져오지 않은 이유 |
| --- | --- |
| 처방 등록 경로 `/children/{child_id}/prescriptions` | 처방 API 경로를 `/prescriptions` 한 곳으로 모읍니다 |
| 업로드 형식 heic·pdf, 용량 초과 `413` | 모바일 브라우저는 사진을 jpg로 바꿔 올립니다. 오류 코드 종류도 줄입니다 |
| `FAILED` 상태 + `failed_stage` 컬럼 | OCR 실패는 행을 만들지 않고, 가이드 실패는 `CONFIRMED`를 유지하면 되므로 필요 없습니다 |
| 로그아웃 API | JWT를 서버에 저장하지 않으므로 FE가 토큰을 지우면 끝입니다 |
| 자녀 상세·수정·삭제, 이력 삭제 | 1차 핵심 흐름이 아니므로 9절로 옮겼습니다 |
| 웹 푸시 API (P1~P6) | 11/24에 1차 포함으로 결정해 2절 목록에 다시 넣었습니다. 상세 명세는 추가 필요 |
| 자녀의 `sex`, 동의 일시 객체 | DB에 해당 컬럼이 없습니다. 동의 저장 방식은 11절에서 다룹니다 |
| `route` 한글 값(`내복`, `건조시럽`) | 코드값이 DB CHECK 제약을 걸기 쉽고, 화면 표시는 FE가 바꿀 수 있습니다 |
