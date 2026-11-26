/**
 * 처방 확정 → 가이드 생성·조회 → 챗봇 API (API 명세서 v1.0 7·8·9번 + 챗봇)
 *
 * 위치: frontend/src/api/prescriptionFlow.js
 *
 * 백엔드 주소 (모두 로그인 필요)
 *   PUT  /api/v1/prescriptions/{id}/confirm   처방 확정 (S-04)        → 200, 처방 상세
 *   POST /api/v1/prescriptions/{id}/guide     가이드 만들기 (약 20초)  → 201 새로 만듦 / 200 이미 있음
 *   GET  /api/v1/prescriptions/{id}/guide     저장된 가이드 보기       → 200 / 404 아직 없음
 *   POST /api/v1/prescriptions/{id}/chat      챗봇 질문               → 200 { reply, category, needs_professional }
 *
 * 실패하면 ApiError를 던져요. error.status(HTTP 코드)와 error.message(화면에 보여 줄 한국어 문구)를 쓰면 돼요.
 */

// 토큰 보관 위치는 기존 guide.jsx와 같게 맞췄어요. api/children.js와 다르면 그쪽에 맞춰 주세요.
const TOKEN_KEY = 'access_token';
const BASE = '/api/v1';

const GUIDE_TIMEOUT_MS = 90_000; // 서버 가이드 제한 60초 + 여유 (명세서: FE 90초 이상)
const CHAT_TIMEOUT_MS = 40_000; // 서버 챗봇 제한 30초 + 여유
const DEFAULT_TIMEOUT_MS = 20_000;
const MAX_HISTORY = 10; // 서버가 받는 최근 대화 최대 개수

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** FastAPI 오류 본문 { detail } → 화면 문구. detail이 목록(입력 형식 오류)이면 일반 문구로 바꿔요. */
function messageOf(body, fallback) {
  const detail = body?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) return '입력 내용을 확인해 주세요.';
  return fallback;
}

async function request(path, { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS, fallback } = {}) {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (!token) throw new ApiError(401, '로그인이 필요해요.');

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const data = await res.json().catch(() => null);
    if (res.status === 401) {
      sessionStorage.removeItem(TOKEN_KEY);
      throw new ApiError(401, '로그인이 만료됐어요. 다시 로그인해 주세요.');
    }
    if (!res.ok) throw new ApiError(res.status, messageOf(data, fallback ?? '요청에 실패했어요.'));
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new ApiError(0, '응답이 너무 오래 걸려 멈췄어요. 다시 시도해 주세요.');
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, '서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.');
  } finally {
    clearTimeout(timer);
  }
}

/**
 * 처방 확정 (S-04 "확인했어요, 가이드 만들기")
 * body 모양 (서버 PrescriptionConfirmRequest):
 * {
 *   prescription_date: "2026-11-12" | null,
 *   hospital_name: string | null,
 *   diagnosis_user_input: string,          // 필수. 보호자가 적은 병명
 *   symptom_notes: string | null,
 *   medications: [{
 *     medication_id: number | null,        // OCR로 만든 약이면 그 id, 새로 넣은 약이면 null
 *     name, dose_per_time, unit,           // unit: "mL" | "포" | "정" | "캡슐" | "g" | "방울" | "개"
 *     daily_count,                         // 필요할 때 먹는 약이면 null
 *     total_days, as_needed, max_daily_count, usage,
 *     route,                               // "ORAL" | "EXTERNAL"
 *     dosage_form,                         // "SYRUP" | "DRY_SYRUP" | "POWDER" | "TABLET" | "CAPSULE" | "OINTMENT" | "CREAM" | "EYE_DROP" | "SUPPOSITORY" | "ETC"
 *   }]
 * }
 * 보낸 목록에 없는 약은 서버에서 지워져요. 전체 목록을 보내야 해요.
 */
export function confirmPrescription(prescriptionId, body) {
  return request(`/prescriptions/${encodeURIComponent(prescriptionId)}/confirm`, {
    method: 'PUT',
    body,
    fallback: '처방을 확정하지 못했어요.',
  });
}

/** 가이드 만들기. 이미 있으면 서버가 새로 만들지 않고 기존 것을 돌려줘요(같은 버튼을 다시 눌러도 안전). */
export function createGuide(prescriptionId) {
  return request(`/prescriptions/${encodeURIComponent(prescriptionId)}/guide`, {
    method: 'POST',
    timeoutMs: GUIDE_TIMEOUT_MS,
    fallback: '가이드를 만들지 못했어요. 다시 시도해 주세요.',
  });
}

/** 저장된 가이드 보기. 아직 없으면 ApiError(status 404). */
export function getGuide(prescriptionId) {
  return request(`/prescriptions/${encodeURIComponent(prescriptionId)}/guide`, {
    fallback: '가이드를 불러오지 못했어요.',
  });
}

/**
 * 챗봇 질문.
 * messages: 화면의 대화 목록 [{ from: 'me' | 'bot', text }]. 최근 10개만 history로 보내요.
 * 반환: { reply, category, needs_professional }
 */
export function askChat(prescriptionId, question, messages = []) {
  const history = messages
    .filter((m) => m.text && m.text.trim())
    .slice(-MAX_HISTORY)
    .map((m) => ({ role: m.from === 'me' ? 'user' : 'assistant', text: m.text.slice(0, 1000) }));
  return request(`/prescriptions/${encodeURIComponent(prescriptionId)}/chat`, {
    method: 'POST',
    body: { message: question.slice(0, 500), history },
    timeoutMs: CHAT_TIMEOUT_MS,
    fallback: '답변을 만들지 못했어요. 잠시 후 다시 물어봐 주세요.',
  });
}

/* ───────────────────────── S-04 약 카드 → 확정 API 요청 ───────────────────────── */

/** 확정 전에 보호자가 고쳐야 하는 입력 문제. message를 그대로 보여 주면 돼요. */
export class ConfirmInputError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ConfirmInputError';
  }
}

// 서버가 받는 단위 (app/dtos/prescriptions.py Unit)
const UNIT_WORDS = [
  [/^(ml|mL|ML|cc|씨씨|밀리리터)$/, 'mL'],
  [/^포$/, '포'],
  [/^(정|알)$/, '정'],
  [/^캡슐$/, '캡슐'],
  [/^(g|그램)$/i, 'g'],
  [/^방울$/, '방울'],
  [/^개$/, '개'],
];
// 약 이름으로 제형 추측 (서버 값이 없을 때만). 위에 있을수록 먼저 봐요: '건조시럽'이 '시럽'보다 먼저.
const FORM_WORDS = [
  [/건조\s*시럽/, 'DRY_SYRUP'],
  [/시럽|현탁|액제|내용액/, 'SYRUP'],
  [/연고/, 'OINTMENT'],
  [/크림|로션/, 'CREAM'],
  [/점안|안약/, 'EYE_DROP'],
  [/좌약|좌제/, 'SUPPOSITORY'],
  [/캡슐/, 'CAPSULE'],
  [/산$|산\(|가루|과립|세립/, 'POWDER'],
  [/정$|정\(|정\s|츄어블/, 'TABLET'],
];
const EXTERNAL_FORMS = ['OINTMENT', 'CREAM', 'EYE_DROP'];

const numberIn = (text) => {
  const m = String(text ?? '').match(/\d+(?:\.\d+)?/);
  return m ? Number(m[0]) : null;
};
const textOf = (field) => String(field?.value ?? '').trim();

/** '4.2mL' → { amount: 4.2, unit: 'mL' }. 단위를 못 읽으면 unit: null */
function parseDose(text) {
  // '1회 0.5g'처럼 숫자가 여러 개면, 바로 뒤에 단위가 붙은 숫자를 써요.
  const pairs = [...String(text ?? '').matchAll(/(\d+(?:\.\d+)?)\s*([A-Za-z가-힣]*)/g)].map(([, n, word]) => ({
    amount: Number(n),
    unit: UNIT_WORDS.find(([re]) => re.test(word))?.[1] ?? null,
  }));
  return pairs.find((p) => p.unit) ?? pairs[0] ?? { amount: null, unit: null };
}

function guessForm(name) {
  return FORM_WORDS.find(([re]) => re.test(name))?.[1] ?? 'ETC';
}

/**
 * S-04 약 카드 하나 → 서버 MedicationConfirmItem.
 * med: toConfirmMed()가 만든 모양 + 보호자가 고친 값 ({ name, dose, perDay, days, timing } 각 { value })
 * asNeeded: 필요할 때 먹는 약인지 (records.jsx의 isAsNeeded 결과)
 */
export function toConfirmMedication(med, asNeeded) {
  const name = String(med.name ?? '').trim();
  const label = `「${name || '이름 없는 약'}」`;

  // 제형·내복/외용: OCR 값이 있으면 그대로, 없으면(새로 넣은 약 등) 약 이름으로 추측해요.
  const dosageForm = med.dosageForm ?? guessForm(name);
  const route = med.route ?? (EXTERNAL_FORMS.includes(dosageForm) ? 'EXTERNAL' : 'ORAL');
  const external = route === 'EXTERNAL';

  // 바르는 약·안약은 '적당량'처럼 숫자가 없어도 돼요 (NFR-SAFE-004: 외용제 양은 숫자로 안내하지 않아요).
  const { amount, unit: typedUnit } = parseDose(textOf(med.dose));
  const unit = amount ? typedUnit ?? med.unit ?? null : null;
  if (!external && (!amount || amount <= 0)) throw new ConfirmInputError(`${label}의 1회 양을 숫자로 적어 주세요. 예: 5mL, 1포`);
  if (!external && !unit) throw new ConfirmInputError(`${label}의 1회 양에 단위를 함께 적어 주세요. 예: 5mL, 1포, 1정`);
  if (external && amount && !unit) throw new ConfirmInputError(`${label}의 양에 단위를 함께 적거나, 숫자를 지우고 '적당량'으로 적어 주세요.`);

  const count = numberIn(textOf(med.perDay));
  const days = numberIn(textOf(med.days));
  if (asNeeded && !count) {
    throw new ConfirmInputError(`${label}은 필요할 때 먹는 약이에요. 하루 최대 몇 번까지인지 적어 주세요. 예: 필요할 때, 최대 4번`);
  }
  if (!asNeeded && !count) throw new ConfirmInputError(`${label}의 하루 횟수를 적어 주세요. 예: 3번`);
  if (count && (count < 1 || count > 24)) throw new ConfirmInputError(`${label}의 하루 횟수를 다시 확인해 주세요.`);
  if (days && (days < 1 || days > 365)) throw new ConfirmInputError(`${label}의 복용 기간을 다시 확인해 주세요.`);

  return {
    medication_id: med.medicationId ?? null,
    name,
    dose_per_time: amount ? Math.round(amount * 100) / 100 : null, // 서버는 소수 둘째 자리까지 받아요
    unit,
    daily_count: asNeeded ? null : count,
    total_days: days || null,
    as_needed: Boolean(asNeeded),
    max_daily_count: asNeeded ? count : null,
    usage: textOf(med.timing) || null,
    route,
    dosage_form: dosageForm,
  };
}

/** S-04 확인 화면 값 → PUT /confirm 요청 본문. 문제가 있으면 ConfirmInputError를 던져요. */
export function toConfirmBody({ meds, isAsNeeded, date, disease, note }) {
  const diagnosis = String(disease ?? '').trim();
  if (!diagnosis) throw new ConfirmInputError('진료받은 이유(병명)를 적어 주세요. 예: 목감기, 중이염');
  return {
    prescription_date: date || null,
    hospital_name: null, // 화면에서 고칠 수 없는 값이라 보내지 않아요(서버가 OCR 값을 그대로 둬요)
    diagnosis_user_input: diagnosis.slice(0, 200),
    symptom_notes: note?.trim() || null,
    medications: meds.map((m) => toConfirmMedication(m, isAsNeeded(m))),
  };
}
