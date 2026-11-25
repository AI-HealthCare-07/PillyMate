# PillyMate OCR 모듈 프론트엔드 연동 안내

> 작성: AI-1 · 2026-11-24 · 기준: `docs/PillyMate_API_명세서_v1.0.md` (5·6·7·8·11절), `ocr/` 모듈
> 대상: FE-2 (S-03 처방 올리기, S-04 처방 확인), FE-1·BE-2 참고

AI-1은 OCR 모듈을 넘기고 빠집니다. 이 문서만 보고 화면을 연결할 수 있도록 **어떻게 동작하는지, 무엇을 보내고 무엇을 받는지,
화면에서 어떻게 보여 줘야 하는지**를 정리했습니다. 모듈 내부 설명은 `ocr/README.md`에 있습니다.

## 1. 한눈에 보기

```text
[S-03 처방 올리기]                    [BE-2 서버]                                 [S-04 처방 확인]
사진 + 처방전/약봉투 선택  ──POST /prescriptions──▶  S3에 사진 저장
(multipart, 최대 30초 대기)                         run_ocr(사진, 종류)  ← AI-1 모듈
                                                    · CLOVA OCR로 글자 읽기
                                                    · 처방전/약봉투 양식에서 항목 찾기
                                                    · 이름·주민번호·나이·전화번호 가리기
                                                    DB에 처방 1행 + 약 N행 저장
                              ◀──── 201 응답 ────  처방 상세 JSON (6번 형식)  ──────▶  약 카드로 보여 주고
                                                                                      보호자가 고친 뒤 확정(7번)
```

- 프론트는 **OCR 모듈을 직접 부르지 않습니다.** 항상 BE-2 API(`POST /prescriptions`, `GET /prescriptions/{id}`)로 주고받습니다.
- OCR은 요청 하나 안에서 끝나는 **동기 처리**입니다. 보통 몇 초, 최대 30초. 넘으면 502입니다.
- OCR 결과는 **틀릴 수 있는 초안**입니다. 보호자가 S-04에서 확인·수정·확정해야 가이드를 만들 수 있습니다 (명세 8번: 확정 전 OCR 값으로 가이드 생성 금지).

## 2. 프론트가 보내는 것 — `POST /prescriptions` (명세 5번)

`multipart/form-data`

| 필드 | 필수 | 값 | 주의 |
| --- | --- | --- | --- |
| `child_id` | O | 자녀 ID | |
| `source_type` | O | `PRESCRIPTION`(처방전) 또는 `PILL_BAG`(약봉투) | **S-03에 처방전/약봉투 선택이 필요합니다** (지금 화면에는 없음). 종류가 틀리면 엉뚱한 칸을 읽습니다 |
| `image` | O | 사진 파일 | **jpg·png만**, 10MB 이하. WEBP·HEIC·PDF는 422 |
| `diagnosis_user_input` | | 병명 | 비어 있어도 되지만 확정(7번) 때는 필수 |
| `symptom_notes` | | 증상·특이사항 | |

- 요청 타임아웃은 **90초 이상**, 기다리는 동안 로딩 화면, 버튼 비활성화 (명세 1절 동기 처리 메모).
- 사진 품질 팁: 처방전 전체가 한 장에 들어오고 글자가 수평에 가깝게. 약간 기울어진 사진은 모듈이 보정합니다 (테스트는 ±3° 기준).

## 3. 프론트가 받는 것 — 201 응답 / `GET /prescriptions/{id}` (명세 6번)

응답의 아래 필드는 **OCR 모듈이 만든 값**이고, 나머지(`prescription_id`, `status`, `image_url`, `medication_id`, `is_user_edited` 등)는 BE-2가 붙입니다.

### 3-1. 처방전 예시 (샘플 `rx_01_scan`, 실제 OCR 결과)

```json
{
  "source_type": "PRESCRIPTION",
  "prescription_date": "2026-11-12",
  "hospital_name": "해솔소아청소년과의원",
  "diagnosis_extracted": "J00,J209",
  "medications": [
    { "name": "세파클러건조시럽(내복)/60(1)mL/병", "insurance_code": "643901230",
      "dose_per_time": 4.2, "unit": "mL", "daily_count": 3, "total_days": 5,
      "as_needed": false, "max_daily_count": null, "usage": "가루약,물약 따로 식후 30분",
      "route": "ORAL", "dosage_form": "DRY_SYRUP", "confidence": 1.0 },
    { "name": "비오플250산(사카로마이세스보울라디)/1포", "insurance_code": "644702121",
      "dose_per_time": 0.5, "unit": "포", "daily_count": 3, "total_days": 5,
      "as_needed": false, "max_daily_count": null, "usage": "가루약,물약 따로 식후 30분",
      "route": "ORAL", "dosage_form": "POWDER", "confidence": 1.0 },
    { "name": "세토펜현탁액(아세트아미노펜)/100(1)mL/병", "insurance_code": "649806731",
      "dose_per_time": 5.0, "unit": "mL", "daily_count": null, "total_days": 3,
      "as_needed": true, "max_daily_count": null, "usage": "필요시 (5)mL씩복용(사용)하세요",
      "route": "ORAL", "dosage_form": "SYRUP", "confidence": 1.0 }
  ]
}
```

### 3-2. 약봉투 예시 (샘플 `bag_01_photo`, 실제 OCR 결과)

```json
{
  "source_type": "PILL_BAG",
  "prescription_date": null,
  "hospital_name": "해솔소아청소년과의원",
  "diagnosis_extracted": null,
  "medications": [
    { "name": "세파클러건조시럽", "insurance_code": null,
      "dose_per_time": 4.2, "unit": "mL", "daily_count": 3, "total_days": 5,
      "as_needed": false, "max_daily_count": null, "usage": null,
      "route": "ORAL", "dosage_form": "DRY_SYRUP", "confidence": 0.92 },
    { "name": "세토펜현탁액", "insurance_code": null,
      "dose_per_time": 5.0, "unit": "mL", "daily_count": null, "total_days": null,
      "as_needed": true, "max_daily_count": null, "usage": "필요시",
      "route": "ORAL", "dosage_form": "SYRUP", "confidence": 0.92 }
  ]
}
```

### 3-3. 필드 설명

**처방 머리**

| 필드 | 타입 | 뜻 | `null`일 때 | 화면 |
| --- | --- | --- | --- | --- |
| `prescription_date` | `"YYYY-MM-DD"` \| null | 처방전 교부일 | **약봉투는 항상 null** (조제일자만 있음) | null이면 보호자가 날짜 입력. `dateParts(null)` 호출하지 않도록 주의 |
| `hospital_name` | string \| null | 병원 이름 | 못 읽은 경우 | 수정 가능 입력칸 |
| `diagnosis_extracted` | string \| null | 질병분류기호. 여러 개면 쉼표로 이음 (`"J00,J209"`) | **약봉투는 항상 null** | **병명이 아닙니다.** "처방전에서 읽은 기호"로 참고 표시만. 병명은 `diagnosis_user_input`(보호자 입력) |

**약 (`medications[]`)**

| 필드 | 타입 | 뜻 | `null`일 때 / 주의 |
| --- | --- | --- | --- |
| `name` | string | 약 이름. 처방전은 인쇄된 그대로 긴 이름, 약봉투는 짧은 이름 | 항상 있음. 글자 한두 개가 틀릴 수 있음 (예: 밀리그램 → 밀리그림) |
| `insurance_code` | string \| null | 9자리 보험 약품코드 | 약봉투는 항상 null. 화면에 안 보여도 됨 |
| `dose_per_time` | number \| null | 1회 양 (숫자만) | `6.6667`처럼 처방전에 인쇄된 소수가 그대로 옴 → 표시할 때 소수 둘째 자리 정도로 반올림 권장 |
| `unit` | string \| null | `mL`·`포`·`정`·`캡슐`·`g`·`방울`·`개` 중 하나 | 목록에 없는 단위(관, 분무, 흡입)나 못 읽으면 null |
| `daily_count` | int \| null | 하루 복용 횟수 | **`as_needed: true`면 항상 null** (명세 규칙) |
| `total_days` | int \| null | 복용 일수 | 약봉투의 필요시 약·바르는 약은 null인 경우가 많음 |
| `as_needed` | boolean | 필요할 때만 먹는 약인지 ("필요시", "열날 때") | 항상 true/false |
| `max_daily_count` | int \| null | 필요시 약의 하루 최대 횟수 | **샘플 30장에서는 전부 null** (처방전에 "1일 최대 n회"가 거의 안 적힘). `as_needed: true`면 확정 때 필수(없으면 400) → **S-04에서 입력받아야 함** |
| `usage` | string \| null | 용법 문구 ("식후 30분", "필요시", "적당량") | 약봉투는 52개 중 21개만 있음 |
| `route` | `"ORAL"` \| `"EXTERNAL"` \| null | 먹는 약 / 바르거나 넣거나 뿌리는 약 | 확정 때 필수. `EXTERNAL`이면 "한 번에 바를 양"을 숫자로 안내하지 않음 (NFR-SAFE-004) |
| `dosage_form` | 11절 코드 \| null | `SYRUP`, `DRY_SYRUP`, `POWDER`, `TABLET`, `CAPSULE`, `OINTMENT`, `CREAM`, `EYE_DROP`, `SUPPOSITORY`, `ETC` | 확정 때 필수. 화면에는 한글로 바꿔 표시 (아래 표) |
| `confidence` | number (0~1) | 그 약 줄 글자들의 인식 신뢰도 평균 | **약 단위 값**입니다 (칸별 값이 아님). 4절 참고 |

**`dosage_form` 한글 표시 (제안)**

| 코드 | 표시 | 코드 | 표시 |
| --- | --- | --- | --- |
| `SYRUP` | 시럽 | `OINTMENT` | 연고 |
| `DRY_SYRUP` | 건조시럽(가루를 물에 녹이는 시럽) | `CREAM` | 크림 |
| `POWDER` | 가루약 | `EYE_DROP` | 안약 |
| `TABLET` | 알약 | `SUPPOSITORY` | 좌약 |
| `CAPSULE` | 캡슐 | `ETC` | 기타 (흡입제·스프레이·귀약 등) |

### 3-4. 처방전 vs 약봉투 (샘플 각 15장, 약 각 52개 기준)

| 항목 | 처방전 | 약봉투 |
| --- | --- | --- |
| 처방일 | 15/15 있음 | **항상 null** |
| 병원명 | 15/15 | 15/15 |
| 질병분류기호 | 14/15 (나머지 1장은 처방전에 비어 있음 → null) | **항상 null** |
| 약 이름 정확도 | 45/52 (86.5%) — 틀린 7개는 글자 1~2개 오타 | 51/52 (98.1%) |
| 1회 양·단위·횟수·일수·경로·제형 | 기존 결과와 100% 일치 | 기존 결과와 100% 일치 |
| `usage`(용법) | 52개 중 51개 | 52개 중 21개 |

## 4. S-04 화면 표시 규칙

1. **신뢰도 강조** (11/25 반영, 11/24 멘토링 3절 기준): 서버가 약마다 `low_confidence`(`confidence < 0.8`)를 내려 줍니다.
   가장 낮은 약이 0.6 미만이면 서버가 저장하지 않고 `422 {"code": "OCR_LOW_CONFIDENCE"}`를 돌려주며, 화면은 다시 찍기 모달을 띄웁니다 (5절).
   참고: 샘플에서 0.9로 강조하면 6개 중 5개가 실제 이름 오타였고, 0.8이면 1개만 잡혔습니다. 기준값은 실제 촬영 사진으로 다시 확인해야 합니다.
   `confidence`는 약 하나에 하나뿐이라, 칸마다 `low`를 다는 현재 카드 구조에서는 약 단위로 표시하거나 이름 옆에 표시하는 게 맞습니다.
2. **null인 칸**은 비워 두고 입력을 받습니다. 모듈은 빈 값을 추정해 채우지 않습니다 (명세 7절 폴백 기준). 비어 있는 `dose_per_time`·`daily_count`·`total_days`는 S-04에서 경고만 하고 확정은 막지 않습니다.
3. **필요시 약(`as_needed: true`)**: "하루 횟수" 대신 "하루 최대 횟수(`max_daily_count`)" 입력칸을 보여 주세요. 확정 때 필수이고, `daily_count`는 비워서 보내야 합니다 (값이 있으면 422).
4. **외용약(`route: "EXTERNAL"`)**: 1회 양을 "몇 mL 바르기"처럼 숫자로 안내하지 않습니다.
5. **`route`·`dosage_form`이 null**이면 보호자가 골라야 합니다 (확정 필수값). 제형을 고르면 경로는 자동으로 정해집니다 (11절: 시럽·건조시럽·가루약·알약·캡슐 → ORAL, 연고·크림·안약·좌약 → EXTERNAL).
6. **확정(7번) 요청은 숫자 필드 그대로** 보내 주세요. 화면용 문자열("6mL", "3번")을 다시 파싱하지 않도록, 원래 값을 카드에 같이 들고 있는 것을 권장합니다.

## 5. 오류 응답 (명세 8절) — 그대로 보여 주면 됩니다

| 코드 | 상황 | `detail` | 화면 |
| --- | --- | --- | --- |
| 400 | `child_id`·`source_type`·`image` 누락 | 필수 항목을 입력해 주세요: … | 입력 다시 |
| 422 | jpg·png가 아님 | jpg 또는 png 사진만 올릴 수 있어요. | 사진 다시 고르기 |
| 422 | 10MB 초과 | 10MB 이하 사진만 올릴 수 있어요. | 사진 다시 고르기 |
| 404 | 내 자녀가 아님 | 자녀 정보를 찾을 수 없어요. | |
| 422 | 신뢰도 0.6 미만·약 0개 (`code: OCR_LOW_CONFIDENCE`) | 사진이 흐릿해서 약 정보를 정확히 읽지 못했어요. … | **다시 찍기 모달** (처방은 만들어지지 않음) |
| 502 | OCR 실패·30초 초과 | 처방전을 읽지 못했어요. 다시 찍어 주세요. | **다시 찍기 모달** (처방은 만들어지지 않음) |

- 글자를 하나도 못 읽거나 CLOVA가 응답하지 않으면 502입니다.
- 글자는 읽었는데 **약을 하나도 못 찾으면** 저장하지 않고 `OCR_LOW_CONFIDENCE`로 다시 찍기를 요청합니다.
- 구현: `frontend/src/api/prescriptionRegistration.js`, `screens/upload.jsx`의 `ReadingScreen`·`RetakeModal`.

## 6. 지금 프론트 코드와 맞춰야 할 것 (FE-2 TODO 목록)

| 위치 | 지금 | 맞춰야 할 것 |
| --- | --- | --- |
| `screens/upload.jsx` 파일 선택 | ~~WEBP 허용~~ | 11/25 반영: jpg·png만 |
| `screens/upload.jsx` | 처방전/약봉투 선택 없음 | **`source_type` 선택 추가** |
| `screens/upload.jsx` `ReadingScreen` | ~~2.5초 뒤 예시 값으로 이동~~ | 11/25 반영: `POST /prescriptions` 호출, 422 `OCR_LOW_CONFIDENCE`·502면 다시 찍기 알럿. 아이 목록은 `GET /children`(서버)에서 받아요 |
| `screens/confirm.jsx` `dateParts(ocr.date)` | 날짜가 항상 있다고 가정 | 약봉투는 `prescription_date: null` → 날짜 입력 받기 |
| `screens/confirm.jsx` 병명 | `ocr.disease` 사용 | `diagnosis_extracted`는 코드(J00)라 병명으로 쓰지 않기 |
| `components/rx/meds.jsx` 카드 | `low`가 칸 단위 | 11/25: `low_confidence` 약은 값이 있는 칸마다 `low`로 표시 (`api/prescriptionRegistration.js`) |
| 약 카드 | "하루 횟수"만 있음 | 필요시 약은 "하루 최대 횟수" 입력 (4절 3번) |

### 응답 약 → 현재 카드 모양 변환 예시

실제 구현은 `frontend/src/api/prescriptionRegistration.js`의 `toConfirmMed()`입니다. 아래는 처음 제안한 예시(기준 0.9)로 남겨 둡니다.

```js
const LOW_CONFIDENCE = 0.9;
const trimNumber = (n) => String(Math.round(n * 100) / 100); // 6.6667 → "6.67"

export function toConfirmCard(med) {
  const low = med.confidence !== null && med.confidence < LOW_CONFIDENCE;
  const perDay = med.as_needed
    ? (med.max_daily_count ? `필요할 때, 최대 ${med.max_daily_count}번` : '필요할 때')
    : (med.daily_count ? `${med.daily_count}번` : '');
  return {
    id: med.medication_id ? `m${med.medication_id}` : crypto.randomUUID(),
    name: med.name ?? '',
    low, // 약 단위 강조
    dose: { value: med.dose_per_time === null ? '' : `${trimNumber(med.dose_per_time)}${med.unit ?? ''}` },
    perDay: { value: perDay },
    days: { value: med.total_days ? `${med.total_days}일` : '' },
    timing: { value: med.usage ?? '' },
    source: med, // 확정(7번) 요청에 보낼 원래 숫자 값
  };
}
```

## 7. 개인정보 — 프론트로 오는 것과 오지 않는 것

- 프론트가 받는 응답에는 **환자 이름·주민등록번호·나이·전화번호가 없습니다.** 의사 이름·면허번호, 약국 정보, 영수증 금액도 넣지 않습니다.
- 처방전 OCR 원문은 마스킹본도 **저장하지 않습니다** (11/25 변경). 정리된 항목(병원·처방일·약)만 DB에 남습니다.
- 원본 사진은 `image_url`(10분짜리 주소)로만 볼 수 있고, 가이드를 만들거나 7일이 지나면 `null`입니다 → "원본 사진은 보관 기간(7일)이 지나 삭제됐어요." 안내 (명세 6번).
- 사진은 판독을 위해 **네이버 클라우드 CLOVA OCR로 전송**됩니다.

## 8. 직접 확인해 보기 (API 없이)

BE-2 API가 준비되기 전에도 OCR 결과를 브라우저에서 볼 수 있습니다. CLOVA 키가 있는 사람만 실행할 수 있고, 사진마다 CLOVA를 1번 호출합니다.

```bash
uv run --env-file <CLOVA 키가 든 .env> python -m ocr.tools.ocr_preview_server
```

http://127.0.0.1:8010 에서 처방전/약봉투를 고르고 사진을 올리면 이 문서 3절 형식의 결과가 표로 나옵니다.
키가 없어도 `ocr/tests/expected_results/*.json`(샘플 30장의 결과)으로 실제 데이터 모양을 볼 수 있습니다.

## 9. 문의

- 응답 형식·저장·오류 코드: BE-2 (`POST /prescriptions`, `GET /prescriptions/{id}`)
- OCR 모듈 동작·필드 규칙: `ocr/README.md`, 테스트는 `uv run pytest ocr`
- 이 문서의 숫자(정확도, 신뢰도 분포)는 2026-11-24 샘플 30장(가상 처방전) 기준입니다.
