# PillyMate 1차 MVP ERD 설계서 v1.1

- **기준 문서:** `PillyMate_API_명세서_v1.0.md` (2026-11-24 제출본)
- **반영 코드:** OCR 모듈 `run_ocr()` (`feat/ocr` 브랜치 `7d495da`, 샘플 사진 30장 실측) — 변경 내용은 5절 참고
- **대상 DBMS / ORM:** MySQL 8.0 · Tortoise ORM (`asyncmy`) · `aerich` 마이그레이션
- **테이블 구성:** 핵심 5개 (`GUARDIAN`, `CHILD`, `PRESCRIPTION`, `MEDICATION`, `GUIDE`) + 웹 푸시 초안 2개 (`PUSH_TOKEN`, `MEDICATION_ALARM`)

---

## 1. ERD 다이어그램 (Mermaid)

GitHub, Notion, Mermaid Live Editor에서 자동으로 렌더링됩니다.

```mermaid
erDiagram
    GUARDIAN ||--o{ CHILD : "1:N (CASCADE)"
    GUARDIAN ||--o{ PUSH_TOKEN : "1:N (CASCADE, P1~P6)"
    CHILD ||--o{ PRESCRIPTION : "1:N (CASCADE)"
    PRESCRIPTION ||--o{ MEDICATION : "1:N (CASCADE)"
    PRESCRIPTION ||--o| GUIDE : "1:0..1 (CASCADE)"
    MEDICATION ||--o{ MEDICATION_ALARM : "1:N (CASCADE, P1~P6)"

    GUARDIAN {
        bigint guardian_id PK "AUTO_INCREMENT"
        varchar(255) email UK "소문자 정규화, NOT NULL"
        varchar(255) password_hash "bcrypt, NOT NULL"
        varchar(50) name "NOT NULL"
        date birth_date "만 19세 이상, NOT NULL"
        datetime created_at "NOT NULL"
        datetime updated_at "NOT NULL"
    }

    CHILD {
        bigint child_id PK "AUTO_INCREMENT"
        bigint guardian_id FK "IDX, NOT NULL"
        varchar(50) name "NOT NULL"
        date birth_date "만 18세 미만, NOT NULL"
        decimal(5,2) weight_kg "CHECK(0.5~150.0), NULL"
        text allergies "NULL"
        text notes "NULL"
        datetime consent_agreed_at "동의 시각, NOT NULL"
        datetime created_at "NOT NULL"
        datetime updated_at "NOT NULL"
    }

    PRESCRIPTION {
        bigint prescription_id PK "AUTO_INCREMENT"
        bigint child_id FK "IDX(child_id, created_at DESC)"
        varchar(20) source_type "CHECK(PRESCRIPTION, PILL_BAG), NOT NULL"
        varchar(20) status "CHECK(UPLOADED, OCR_DONE, CONFIRMED, GUIDE_DONE, FAILED)"
        date prescription_date "NULL(약봉투는 항상 NULL)"
        varchar(100) hospital_name "NULL"
        varchar(50) diagnosis_extracted "질병분류기호 쉼표 연결(참고용), NULL"
        varchar(200) diagnosis_user_input "CHECK(확정/가이드완료 시 NOT NULL & 비공백)"
        text symptom_notes "NULL"
        varchar(512) image_storage_key "S3 키(가이드 생성 후 NULL)"
        datetime created_at "NOT NULL"
        datetime updated_at "NOT NULL"
    }

    MEDICATION {
        bigint medication_id PK "AUTO_INCREMENT"
        bigint prescription_id FK "IDX, NOT NULL"
        varchar(100) name "NOT NULL"
        varchar(20) insurance_code "NULL(약봉투는 항상 NULL)"
        decimal(8,4) dose_per_time "소수 4자리(예: 0.3333), NULL"
        varchar(10) unit "CHECK(mL, 포, 정, 캡슐, g, 방울, 개), NULL"
        tinyint daily_count "CHECK(as_needed=1이면 NULL), NULL"
        smallint total_days "NULL"
        boolean as_needed "DEFAULT false, NOT NULL"
        tinyint max_daily_count "NULL(필요시 약 확정 시 필수, 앱 검증)"
        varchar(100) usage "NULL"
        varchar(10) route "CHECK(ORAL, EXTERNAL), NULL(확정 시 필수)"
        varchar(20) dosage_form "CHECK(SYRUP 등 10종), NULL(확정 시 필수)"
        decimal(3,2) confidence "0.00~1.00, NULL"
        json ocr_value_snapshot "최초 OCR 불변 스냅샷, NULL"
        boolean is_user_edited "DEFAULT false, NOT NULL"
        datetime created_at "NOT NULL"
        datetime updated_at "NOT NULL"
    }

    GUIDE {
        bigint guide_id PK "AUTO_INCREMENT"
        bigint prescription_id FK, UK "1:0..1 UNIQUE, NOT NULL"
        json guide_content "5개 고정 키, NOT NULL"
        datetime created_at "NOT NULL"
    }

    PUSH_TOKEN {
        bigint push_token_id PK "AUTO_INCREMENT (P1~P6 초안)"
        bigint guardian_id FK "IDX, NOT NULL"
        varchar(512) token UK "COLLATE utf8mb4_bin(대소문자 구분), NOT NULL"
        boolean is_active "DEFAULT true, NOT NULL"
        datetime created_at "NOT NULL"
        datetime updated_at "NOT NULL"
    }

    MEDICATION_ALARM {
        bigint alarm_id PK "AUTO_INCREMENT (P1~P6 초안)"
        bigint medication_id FK "IDX, NOT NULL"
        time notify_time "복약 알림 시각, NOT NULL"
        date start_date "알림 시작일, NOT NULL"
        date end_date "start_date + total_days - 1, NOT NULL"
        boolean is_enabled "DEFAULT true, NOT NULL"
        datetime created_at "NOT NULL"
    }
```

---

## 2. 테이블 상세 명세

### 2.1 `GUARDIAN` (보호자)
| 컬럼명 | 타입 | 제약조건 | NULL | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| `guardian_id` | `BIGINT` | `PK`, `AUTO_INCREMENT` | N | 보호자 고유 ID |
| `email` | `VARCHAR(255)` | `UNIQUE` | N | 소문자 정규화 저장 (대소문자 구분 없는 로그인) |
| `password_hash` | `VARCHAR(255)` | - | N | bcrypt 해시값 (원본 8~64자) |
| `name` | `VARCHAR(50)` | - | N | 보호자 이름 |
| `birth_date` | `DATE` | - | N | 생년월일 (가입 시 만 19세 이상 서버 검증) |
| `created_at` | `DATETIME` | - | N | 생성 일시 (KST) |
| `updated_at` | `DATETIME` | - | N | 수정 일시 (KST) |

### 2.2 `CHILD` (자녀)
| 컬럼명 | 타입 | 제약조건 | NULL | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| `child_id` | `BIGINT` | `PK`, `AUTO_INCREMENT` | N | 자녀 고유 ID |
| `guardian_id` | `BIGINT` | `FK (GUARDIAN)`, `INDEX` | N | 보호자 ID (`ON DELETE CASCADE`) |
| `name` | `VARCHAR(50)` | - | N | 자녀 이름 |
| `birth_date` | `DATE` | - | N | 생년월일 (만 18세 미만 미성년자만 허용) |
| `weight_kg` | `DECIMAL(5,2)` | `CHECK (0.5 ~ 150.0)` | Y | 체중(kg), 가이드 참고용 |
| `allergies` | `TEXT` | - | Y | 알레르기 정보 |
| `notes` | `TEXT` | - | Y | 특이사항 (예: 열성 경련 이력) |
| `consent_agreed_at` | `DATETIME` | - | N | 보호자 동의 3항목 완료 시각 |
| `created_at` | `DATETIME` | - | N | 생성 일시 |
| `updated_at` | `DATETIME` | - | N | 수정 일시 |

### 2.3 `PRESCRIPTION` (처방전)
| 컬럼명 | 타입 | 제약조건 | NULL | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| `prescription_id` | `BIGINT` | `PK`, `AUTO_INCREMENT` | N | 처방전 고유 ID |
| `child_id` | `BIGINT` | `FK (CHILD)`, `INDEX` | N | 자녀 ID (`ON DELETE CASCADE`) |
| `source_type` | `VARCHAR(20)` | `CHECK` | N | `PRESCRIPTION`, `PILL_BAG` (`run_ocr()`에 그대로 넘기는 값) |
| `status` | `VARCHAR(20)` | `CHECK` | N | `UPLOADED`, `OCR_DONE`, `CONFIRMED`, `GUIDE_DONE`, `FAILED` |
| `prescription_date` | `DATE` | - | Y | 처방일 (처방전의 교부일). 약봉투에는 처방일이 없어서 OCR이 항상 `NULL`로 줌 (조제일자는 처방일과 다를 수 있어 넣지 않음, 6절 참고) |
| `hospital_name` | `VARCHAR(100)` | - | Y | 병원명 |
| `diagnosis_extracted` | `VARCHAR(50)` | - | Y | OCR 추출 질병분류기호 (참고용, 병명 대체 불가). 여러 개면 쉼표로 연결 (예: `J00,J209`). 약봉투는 항상 `NULL` |
| `diagnosis_user_input` | `VARCHAR(200)` | `CHECK` | Y | 보호자 입력 병명 (`CONFIRMED`, `GUIDE_DONE` 시 필수·비공백) |
| `symptom_notes` | `TEXT` | - | Y | 증상·특이사항 |
| `image_storage_key` | `VARCHAR(512)` | - | Y | S3 저장 키 (가이드 생성 완료 시 삭제 후 `NULL`) |
| `created_at` | `DATETIME` | - | N | 생성 일시 (7일 경과 시 `image_url: null` 판단 기준) |
| `updated_at` | `DATETIME` | - | N | 수정 일시 |

### 2.4 `MEDICATION` (처방 약품)
| 컬럼명 | 타입 | 제약조건 | NULL | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| `medication_id` | `BIGINT` | `PK`, `AUTO_INCREMENT` | N | 약품 고유 ID |
| `prescription_id` | `BIGINT` | `FK (PRESCRIPTION)`, `INDEX` | N | 처방전 ID (`ON DELETE CASCADE`) |
| `name` | `VARCHAR(100)` | - | N | 약품명. 처방전은 인쇄된 그대로 저장 (예: `세파클러건조시럽(내복)/60(1)mL/병`). OCR 결과의 `name`이 `null`인 약은 저장 전에 앱에서 처리 (4절) |
| `insurance_code` | `VARCHAR(20)` | - | Y | 보험코드 (처방전 9자리). 약봉투는 항상 `NULL` |
| `dose_per_time` | `DECIMAL(8,4)` | - | Y | 1회 투약량. 처방전에 `0.3333`, `6.6667`처럼 소수 4자리까지 인쇄되므로 4자리 보존 |
| `unit` | `VARCHAR(10)` | `CHECK` | Y | `mL`, `포`, `정`, `캡슐`, `g`, `방울`, `개`. 목록에 없는 단위(`관`, `분무`, `흡입` 등)는 OCR이 `NULL`로 줌 |
| `daily_count` | `TINYINT` | `CHECK` | Y | 1일 투여횟수 (`as_needed=true`이면 반드시 `NULL`) |
| `total_days` | `SMALLINT` | - | Y | 총 투약일수 |
| `as_needed` | `BOOLEAN` | `DEFAULT FALSE` | N | 필요시 복용 여부 |
| `max_daily_count` | `TINYINT` | - | Y | 필요시 복용 1일 최대 횟수. OCR은 "1일 최대 n회" 문구가 있을 때만 채우고, 없으면 `NULL` → 보호자가 S-04에서 입력. `as_needed=true`인 약은 **확정 시 필수 (앱 검증)** |
| `usage` | `VARCHAR(100)` | - | Y | 용법 (예: 식후 30분) |
| `route` | `VARCHAR(10)` | `CHECK` | Y | `ORAL`, `EXTERNAL` (OCR 시 NULL 허용, 확정 시 필수) |
| `dosage_form` | `VARCHAR(20)` | `CHECK` | Y | `SYRUP`, `DRY_SYRUP`, `POWDER`, `TABLET`, `CAPSULE`, `OINTMENT`, `CREAM`, `EYE_DROP`, `SUPPOSITORY`, `ETC` (확정 시 필수) |
| `confidence` | `DECIMAL(3,2)` | - | Y | OCR 신뢰도 (`0.00` ~ `1.00`). OCR이 이미 소수 2자리로 반올림해서 줌 |
| `ocr_value_snapshot` | `JSON` | - | Y | 최초 OCR 결과 불변 스냅샷 — `run_ocr()`의 약품 dict 12개 키를 그대로 저장 (보호자 직접 추가 시 `NULL`) |
| `is_user_edited` | `BOOLEAN` | `DEFAULT FALSE` | N | `ocr_value_snapshot` 대비 수정 여부 (확정 시마다 재계산) |
| `created_at` | `DATETIME` | - | N | 생성 일시 |
| `updated_at` | `DATETIME` | - | N | 수정 일시 |

### 2.5 `GUIDE` (맞춤형 복약 가이드)
| 컬럼명 | 타입 | 제약조건 | NULL | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| `guide_id` | `BIGINT` | `PK`, `AUTO_INCREMENT` | N | 가이드 고유 ID |
| `prescription_id` | `BIGINT` | `FK (PRESCRIPTION)`, `UNIQUE` | N | 처방전 ID (1:0..1 보장, 동시 중복 생성 방지) |
| `guide_content` | `JSON` | - | N | 최상위 5개 고정 키 (`summary`, `medications`, `warning_signs`, `care_tips`, `disclaimer`) |
| `created_at` | `DATETIME` | - | N | 생성 일시 |

### 2.6 `PUSH_TOKEN` (웹 푸시 토큰 · P1~P6 초안)
| 컬럼명 | 타입 | 제약조건 | NULL | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| `push_token_id` | `BIGINT` | `PK`, `AUTO_INCREMENT` | N | 토큰 고유 ID |
| `guardian_id` | `BIGINT` | `FK (GUARDIAN)`, `INDEX` | N | 보호자 ID (`ON DELETE CASCADE`) |
| `token` | `VARCHAR(512)` | `UNIQUE`, `COLLATE utf8mb4_bin` | N | 기기 푸시 토큰 (대소문자 구분) |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | N | 토큰 활성 상태 |
| `created_at` | `DATETIME` | - | N | 등록 일시 |
| `updated_at` | `DATETIME` | - | N | 갱신 일시 |

> **참고:** Web Push API(VAPID) 방식 채택 시 `endpoint`, `p256dh`, `auth` 컬럼 구조로 변경될 수 있습니다.

### 2.7 `MEDICATION_ALARM` (복약 알림 스케줄 · P1~P6 초안)
| 컬럼명 | 타입 | 제약조건 | NULL | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| `alarm_id` | `BIGINT` | `PK`, `AUTO_INCREMENT` | N | 알림 고유 ID |
| `medication_id` | `BIGINT` | `FK (MEDICATION)`, `INDEX` | N | 약품 ID (`ON DELETE CASCADE`) |
| `notify_time` | `TIME` | - | N | 알림 발송 시각 |
| `start_date` | `DATE` | - | N | 알림 시작일 |
| `end_date` | `DATE` | - | N | 알림 종료일 (`start_date + total_days - 1`, 종료일 포함 기준) |
| `is_enabled` | `BOOLEAN` | `DEFAULT TRUE` | N | 알림 활성화 여부 |
| `created_at` | `DATETIME` | - | N | 생성 일시 |

> **자동 생성 기준 (명세서 7절):** `as_needed = false` 이면서 `daily_count`와 `total_days`가 모두 존재하는 약품만 자동 생성 대상입니다.

---

## 3. 주요 제약조건 및 인덱스 (MySQL 8.0)

### 3.1 복합 인덱스
```sql
-- 자녀별 처방전 최신순 조회 (GET /children/{child_id}/prescriptions)
CREATE INDEX idx_prescription_child_created
    ON prescription (child_id, created_at DESC);
```

### 3.2 핵심 `CHECK` 및 `UNIQUE` 제약조건
```sql
-- PRESCRIPTION: 확정/가이드 완료 상태에서 병명 필수 및 공백 방지
ALTER TABLE prescription
    ADD CONSTRAINT chk_prescription_diagnosis
    CHECK (
        status NOT IN ('CONFIRMED', 'GUIDE_DONE')
        OR (
            diagnosis_user_input IS NOT NULL
            AND CHAR_LENGTH(TRIM(diagnosis_user_input)) > 0
        )
    );

-- MEDICATION: 필요시 복용약은 daily_count가 항상 NULL
-- max_daily_count는 OCR 직후(OCR_DONE)에는 비어 있을 수 있으므로 DB에서 강제하지 않는다.
-- (medication에는 status가 없어 "확정 시에만" 조건을 CHECK로 걸 수 없음 → 4절의 앱 검증)
ALTER TABLE medication
    ADD CONSTRAINT chk_medication_as_needed
    CHECK (
        as_needed = FALSE
        OR daily_count IS NULL
    );

-- MEDICATION_ALARM: 동일 약품·동일 시간·동일 시작일 중복 알림 방지
ALTER TABLE medication_alarm
    ADD CONSTRAINT uq_medication_alarm_schedule
    UNIQUE (medication_id, notify_time, start_date);
```

---

## 4. 운영 및 삭제 정책 메모

1. **연쇄 삭제 (`ON DELETE CASCADE`):** 보호자 또는 자녀 삭제 시 하위 처방전·약품·가이드·알림이 DB에서 함께 삭제됩니다. 단, S3에 남아 있는 원본 이미지는 DB CASCADE로 지워지지 않으므로 애플리케이션 레벨의 S3 삭제 로직을 반드시 병행해야 합니다.
2. **원본 이미지 수명주기:** 가이드 생성 완료 시 즉시 S3 삭제 및 `image_storage_key = NULL` 처리하며, 미생성 처방전은 S3 Lifecycle Rule(7일)에 의해 자동 삭제됩니다.
3. **Tortoise ORM / `aerich` 주의:** MySQL `ENUM` 대신 `VARCHAR` + `CHECK` 제약을 사용하여 추후 코드값 추가 시 마이그레이션 충돌을 최소화했습니다.
4. **확정(`CONFIRMED`) 시 앱에서 검증할 항목:** DB CHECK로 걸 수 없는 "확정 시 필수" 규칙은 확정 API에서 검사합니다.
   - 모든 약품의 `route`, `dosage_form`이 `NULL`이 아님
   - `as_needed = true`인 약품의 `max_daily_count`가 `NULL`이 아님 (OCR은 대부분 비워서 줌 — 샘플 30장의 필요시 약 15개 모두 `NULL`)
5. **OCR 결과 저장 시 주의 (`POST /prescriptions`):**
   - `run_ocr()`의 약품 dict는 `MEDICATION` 컬럼과 키 이름이 같아서 그대로 넣을 수 있고, 같은 dict를 `ocr_value_snapshot`에 저장합니다.
   - `name`이 `null`인 약품은 `name NOT NULL` 때문에 그대로 저장할 수 없습니다. 저장에서 빼거나 보호자 입력으로 넘깁니다 (샘플 30장에서는 0건).
   - `medications`가 `[]`이어도 오류가 아닙니다. 처방전만 `OCR_DONE`으로 저장하고 보호자가 직접 추가합니다.
   - OCR 원문·마스킹 원문은 저장하지 않습니다 (11/25, 11/24 멘토링 4절). 정리된 항목만 `prescription`·`medication`에 남깁니다.

---

## 5. 변경 이력

### v1.1 (2026-11-24) — OCR 모듈 `run_ocr()` 반영

| 대상 | v1.0 | v1.1 | 이유 |
| :--- | :--- | :--- | :--- |
| `chk_medication_as_needed` | `as_needed=FALSE OR (daily_count IS NULL AND max_daily_count IS NOT NULL)` | `as_needed=FALSE OR daily_count IS NULL` | OCR은 필요시 약의 `max_daily_count`를 대부분 `NULL`로 줘서 v1.0 CHECK로는 OCR 결과 INSERT가 실패함. 필수 검사는 확정 시 앱 검증으로 옮김 |
| `MEDICATION.dose_per_time` | `DECIMAL(7,2)` | `DECIMAL(8,4)` | 처방전 투약량이 `0.3333`처럼 소수 4자리. 2자리로 잘리면 `ocr_value_snapshot`과 값이 달라져 `is_user_edited`가 잘못 `true`가 됨 |
| `PRESCRIPTION.diagnosis_extracted` | `VARCHAR(20)` | `VARCHAR(50)` | 질병분류기호 여러 개를 쉼표로 이어서 줌. 4개 이상이면 20자를 넘을 수 있음 |
| 설명 보강 | - | 2.3·2.4절, 4절 4~5항 | 약봉투에서 항상 `NULL`인 값, 마스킹 표기, 단위 `NULL` 규칙, 앱 검증 항목 |

**샘플 30장 실측 최댓값 (컬럼 크기 확인용):** `name` 38자, `usage` 21자, `hospital_name` 12자, `insurance_code` 9자, `diagnosis_extracted` 10자. 모두 현재 컬럼 크기 안에 들어갑니다.

---

## 6. 팀과 정할 것

- **약봉투 조제일자:** 약봉투에는 처방일 대신 조제일자만 있어서 지금은 `prescription_date = NULL`입니다. 조제일자를 화면에 보여 주기로 하면 `PRESCRIPTION.dispensed_date DATE NULL` 컬럼과 OCR 반환 필드 추가가 필요합니다 (FE-2·AI-1).
- **단위 허용 목록:** `관`, `분무`, `흡입`을 `unit` CHECK 목록에 추가할지 결정이 필요합니다. 추가하면 OCR 쪽 허용 목록도 같이 바꿔야 합니다 (BE-2·FE-2·AI-1).
