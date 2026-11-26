/**
 * 7번 PUT /prescriptions/{id}/confirm (처방 확정) 호출과 요청 변환.
 *
 * 확인 화면의 약 카드는 글자로 된 값(1회 양 '4.2mL', 하루 '3번', 기간 '5일')을 들고 있어요.
 * 서버는 숫자·단위·제형을 따로 받으므로 여기서 나눠요.
 * - 필요할 때 먹는 약: 하루 횟수 대신 하루 최대 횟수('최대 4번')를 보내요. 최대 횟수와 기간은 비워도 돼요.
 * - 제형·경로(route·dosage_form): OCR이 읽은 값을 쓰고, 없으면(보호자가 추가한 약 등) 약 이름·단위로 추정해요.
 */

import { isAsNeeded } from '../state/records.jsx';

export class PrescriptionConfirmError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'PrescriptionConfirmError';
    this.status = status;
  }
}

// 붙이는 약은 '1매'·'1장'으로 적기도 해요. 서버 단위에는 없어서 '개'로 보내요.
const UNITS = { ml: 'mL', 포: '포', 정: '정', 캡슐: '캡슐', g: 'g', 방울: '방울', 개: '개', 매: '개', 장: '개' };
const UNIT_PATTERN = '(mL|ml|ML|포|정|캡슐|g|방울|개|매|장)';

/** '4.2mL' → { dose: 4.2, unit: 'mL' }, '1/2정' → { dose: 0.5, unit: '정' }. 단위가 없으면 fallbackUnit(OCR 단위)을 써요. */
export function parseDose(text, fallbackUnit = null) {
  const value = String(text ?? '').replace(/,/g, '');
  const fraction = value.match(new RegExp(`(\\d+)\\s*/\\s*(\\d+)\\s*${UNIT_PATTERN}?`));
  const decimal = value.match(new RegExp(`(\\d+(?:\\.\\d+)?)\\s*${UNIT_PATTERN}?`));
  const match = fraction ?? decimal;
  if (!match) return { dose: null, unit: fallbackUnit };
  const raw = fraction ? Number(fraction[1]) / Number(fraction[2]) : Number(decimal[1]);
  const unitText = fraction ? fraction[3] : decimal[2];
  // 서버는 1회 양을 소수 둘째 자리까지 받아요.
  const dose = Number.isFinite(raw) && raw > 0 ? Math.round(raw * 100) / 100 : null;
  return { dose, unit: unitText ? UNITS[unitText.toLowerCase()] ?? UNITS[unitText] ?? null : fallbackUnit };
}

/** '3번', '하루 3회' → 3. '번'·'회' 앞 숫자를 먼저 보고, 없으면 처음 나온 숫자. */
const countOf = (text) => {
  const value = String(text ?? '');
  const n = value.match(/(\d+)\s*(?:번|회)/)?.[1] ?? value.match(/\d+/)?.[0];
  return n ? Number(n) : null;
};
/** '5일', '5일분' → 5 */
const daysOf = (text) => {
  const value = String(text ?? '');
  const n = value.match(/(\d+)\s*일/)?.[1] ?? value.match(/\d+/)?.[0];
  return n ? Number(n) : null;
};
/** '필요할 때, 최대 4번' → 4 */
const maxCountOf = (text) => {
  const n = String(text ?? '').match(/최대\s*(\d+)/)?.[1];
  return n ? Number(n) : null;
};

/* 약 이름에 보이는 낱말 → [제형, 경로]. 위에서부터 먼저 맞는 것을 써요(건조시럽을 시럽보다 먼저). */
const FORM_BY_NAME = [
  // 붙이는 약(호쿠날린패취 등)은 서버 제형 목록에 따로 없어서 기타(ETC)로 보내요.
  [/패취|패치|파스/, 'ETC', 'EXTERNAL'],
  [/점안|안약|눈약/, 'EYE_DROP', 'EXTERNAL'],
  [/좌약|좌제|좌정/, 'SUPPOSITORY', 'EXTERNAL'],
  [/연고/, 'OINTMENT', 'EXTERNAL'],
  [/크림/, 'CREAM', 'EXTERNAL'],
  [/건조\s*시럽|건조\s*현탁/, 'DRY_SYRUP', 'ORAL'],
  [/시럽|현탁|액/, 'SYRUP', 'ORAL'],
  [/캡슐/, 'CAPSULE', 'ORAL'],
  [/정제|정(?![가-힣])/, 'TABLET', 'ORAL'],
  [/가루|과립|세립|산제/, 'POWDER', 'ORAL'],
];
const FORM_BY_UNIT = { mL: 'SYRUP', 포: 'POWDER', 정: 'TABLET', 캡슐: 'CAPSULE' };

/** OCR이 제형·경로를 못 읽었을 때 약 이름과 단위로 추정해요. 모르면 먹는 약(ORAL)·기타(ETC). */
export function inferForm(name, unit) {
  const hit = FORM_BY_NAME.find(([pattern]) => pattern.test(name ?? ''));
  if (hit) return { dosageForm: hit[1], route: hit[2] };
  return { dosageForm: FORM_BY_UNIT[unit] ?? 'ETC', route: 'ORAL' };
}

/** 확인 화면 약 카드 하나 → 확정 요청의 약 하나 (명세 7번 medications[]) */
/** 단위를 못 읽었을 때 약 이름으로 정할 수 있는 단위 — 붙이는 약은 한 번에 한 장이라 '개'예요. */
const unitByName = (name) => (/패취|패치|파스/.test(name ?? '') ? '개' : null);

export function toConfirmItem(card) {
  const asNeeded = isAsNeeded(card);
  const { dose, unit } = parseDose(card.dose?.value, card.unit ?? unitByName(card.name));
  const inferred = inferForm(card.name, unit);
  return {
    medication_id: card.medicationId ?? null,
    name: card.name.trim(),
    dose_per_time: dose,
    unit,
    daily_count: asNeeded ? null : countOf(card.perDay?.value),
    max_daily_count: asNeeded ? maxCountOf(card.perDay?.value) : null,
    total_days: daysOf(card.days?.value),
    as_needed: asNeeded,
    usage: String(card.timing?.value ?? '').trim() || null,
    route: card.route ?? inferred.route,
    dosage_form: card.dosageForm ?? inferred.dosageForm,
  };
}

/**
 * 서버에 보내기 전에 막을 문제 — 서버의 400 문구(medications[0].unit 같은 칸 이름)는 보호자가 알아보기 어려워요.
 * 문제가 없으면 null, 있으면 보여 줄 문장.
 */
export function confirmItemProblem(item) {
  const name = `「${item.name}」`;
  if (item.dose_per_time === null) return `${name}의 1회 양을 숫자로 적어 주세요. (예: 5mL, 1포)`;
  if (!item.unit) return `${name}의 1회 양에 단위(mL, 포, 정, 캡슐 등)를 붙여 주세요.`;
  // 필요할 때 먹는 약은 하루 최대 횟수·기간이 없어도 돼요(처방전에 안 적힌 경우가 많아요).
  if (item.as_needed) return null;
  if (item.daily_count === null) return `${name}의 하루 횟수를 숫자로 적어 주세요. (예: 3번)`;
  if (item.total_days === null) return `${name}의 복용 기간을 적어 주세요. (예: 5일)`;
  return null;
}

/** 확정 요청 — 성공하면 서버의 처방 상세(6번과 같은 형식)를 돌려줘요. */
export async function confirmPrescription(prescriptionId, body) {
  const token = sessionStorage.getItem('access_token');
  let response;
  try {
    response = await fetch(`/api/v1/prescriptions/${encodeURIComponent(prescriptionId)}/confirm`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(body),
    });
  } catch {
    throw new PrescriptionConfirmError('서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.');
  }
  const data = await response.json().catch(() => null);
  if (response.ok) return data;
  const message = typeof data?.detail === 'string' ? data.detail : '처방 내용을 저장하지 못했어요. 다시 시도해 주세요.';
  throw new PrescriptionConfirmError(message, response.status);
}
