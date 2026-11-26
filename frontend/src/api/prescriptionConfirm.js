/**
 * 7번 PUT /prescriptions/{id}/confirm (처방 확정) 호출과 요청 변환.
 *
 * 확인 화면의 약 카드는 글자로 된 값(1회 양 '4.2mL', 하루 '3번', 기간 '5일')을 들고 있어요.
 * 서버는 숫자·단위·제형을 따로 받으므로 여기서 나눠요.
 * - 필요할 때 먹는 약: 하루 횟수 대신 하루 최대 횟수('최대 4번')를 보내요. 최대 횟수와 기간은 비워도 돼요.
 * - 제형·경로(route·dosage_form): OCR이 읽은 값을 쓰고, 없으면(보호자가 추가한 약 등) 약 이름·단위로 추정해요.
 * - 1회 양 단위: 적힌 단위 → OCR 단위 → 약 이름·제형으로 짐작한 단위 순서로 써요.
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
  // 바르거나 뿌리거나 들이마시는 약 — 서버 제형 목록에 없어서 기타(ETC)예요. '외용액'이 아래 '액'(시럽)보다 먼저 와야 해요.
  // ocr/ocr_result_formatter.py의 EXTERNAL_ETC_PATTERN과 같은 낱말이에요. 겔포스(먹는 위장약)는 빼요.
  [/로션|겔(?!포스)|스프레이|분무|흡입|흠입|네뷸|할러|레스[풀플]|점이|이용액|귀약|외용|가글/, 'ETC', 'EXTERNAL'],
  [/건조\s*시럽|건조\s*현탁/, 'DRY_SYRUP', 'ORAL'],
  // 가루약은 시럽보다 먼저 봐요 — '메이액트세립'의 '액'을 시럽으로 읽지 않게요.
  // '어린이타이레놀산', '비오플250산(…)/1포'처럼 주 이름이 '산'으로 끝나면 가루약이에요(OCR의 POWDER 규칙과 같아요).
  [/가루|과립|세립|산제|산(?=\s*(?:$|[(/（／]))/, 'POWDER', 'ORAL'],
  [/시럽|현탁|액/, 'SYRUP', 'ORAL'],
  [/캡슐/, 'CAPSULE', 'ORAL'],
  [/정제|정(?![가-힣])/, 'TABLET', 'ORAL'],
];
const FORM_BY_UNIT = { mL: 'SYRUP', 포: 'POWDER', 정: 'TABLET', 캡슐: 'CAPSULE' };

/** OCR이 제형·경로를 못 읽었을 때 약 이름과 단위로 추정해요. 모르면 먹는 약(ORAL)·기타(ETC). */
export function inferForm(name, unit) {
  const hit = FORM_BY_NAME.find(([pattern]) => pattern.test(name ?? ''));
  if (hit) return { dosageForm: hit[1], route: hit[2] };
  return { dosageForm: FORM_BY_UNIT[unit] ?? 'ETC', route: 'ORAL' };
}

/* 처방전 약 이름의 포장 단위 표기: '/1포', '/1정', '/100(1)mL/병'. 마지막 표기가 1회 양의 단위예요(ocr/ocr_result_formatter.py와 같은 규칙). */
const PACKAGE_UNIT = /\/\s*\d+(?:\.\d+)?\s*(?:\(\s*\d+\s*\))?\s*(mL|ml|ML|포|정|캡슐|g|개|방울|관|회|병)/g;
const UNIT_BY_FORM = { SYRUP: 'mL', DRY_SYRUP: 'mL', TABLET: '정', CAPSULE: '캡슐', POWDER: '포', EYE_DROP: '방울', SUPPOSITORY: '개' };

/**
 * 1회 양의 단위를 약 이름·제형으로 짐작해요. 보호자가 '5'만 적거나 OCR이 단위를 못 읽어도 '5mL'처럼 채우려고요.
 * 연고·크림처럼 짐작할 수 없으면 null.
 */
export function guessDoseUnit(name, dosageForm = null) {
  const text = name ?? '';
  // 안약·귀약은 병 용량('/5mL/병')이 적혀 있어도 한 번에 넣는 양은 방울 수예요.
  if (dosageForm === 'EYE_DROP' || /점안|안약|눈약|점이|이용액|귀약/.test(text)) return '방울';
  const packageUnit = [...text.matchAll(PACKAGE_UNIT)].at(-1)?.[1];
  const fromPackage = packageUnit && (UNITS[packageUnit.toLowerCase()] ?? UNITS[packageUnit]);
  if (fromPackage) return fromPackage;
  if (/패취|패치|파스/.test(text)) return '개';
  if (/ml/i.test(text)) return 'mL';
  const form = dosageForm && dosageForm !== 'ETC' ? dosageForm : FORM_BY_NAME.find(([pattern]) => pattern.test(text))?.[1];
  return UNIT_BY_FORM[form] ?? null;
}

/** 숫자만 적힌 1회 양('5', '0.5', '1/2')에 단위를 붙여요. 이미 단위가 있거나 숫자가 아니면 그대로예요. */
export function withDoseUnit(doseText, unit) {
  const value = String(doseText ?? '').trim();
  if (!unit || !/^\d+(?:\.\d+)?$|^\d+\s*\/\s*\d+$/.test(value)) return value;
  return `${value}${unit}`;
}

/**
 * 바르는 약(연고·크림·로션·겔 등)인지 — 한 번에 바를 양은 숫자로 안내하지 않아요(명세 NFR-SAFE-004).
 * 확인 화면은 1회 양 대신 '바르는 양'(적당량(얇게)·직접 입력)을 받고, 서버에는 1회 양·단위를 비워서 보내요.
 */
const TOPICAL_FORMS = new Set(['OINTMENT', 'CREAM']);
const TOPICAL_NAME = /연고|크림|로션|겔(?!포스)|외용액|바르는/; // 겔포스(먹는 위장약)는 빼요
export const isTopical = (card) => TOPICAL_FORMS.has(card.dosageForm) || TOPICAL_NAME.test(card.name ?? '');
export const TOPICAL_DOSE_DEFAULT = '적당량(얇게)';

/** 카드에 단위가 없을 때 쓸 단위 — OCR 단위가 먼저, 없으면 약 이름·제형으로 짐작해요. */
export const cardDoseUnit = (card) => card.unit ?? guessDoseUnit(card.name, card.dosageForm);

/**
 * 확인 화면 약 카드 하나 → 확정 요청의 약 하나 (명세 7번 medications[])
 * 보호자가 비워 둔 칸(1회 양·하루 횟수·기간)은 null로 보내요. 서버는 약 이름·경로·제형만 꼭 받아요(명세 7번).
 */
export function toConfirmItem(card) {
  const asNeeded = isAsNeeded(card);
  const topical = isTopical(card);
  const { dose, unit } = topical ? { dose: null, unit: null } : parseDose(card.dose?.value, cardDoseUnit(card));
  const inferred = inferForm(card.name, unit);
  return {
    medication_id: card.medicationId ?? null,
    name: card.name.trim(),
    dose_per_time: dose,
    unit,
    daily_count: asNeeded ? null : countOf(card.perDay?.value),
    // 용법을 '필요시'로 바꾼 약은 하루 칸에 '3번'처럼 적혀 있을 수 있어요. 그 숫자를 하루 최대 횟수로 써요.
    max_daily_count: asNeeded ? maxCountOf(card.perDay?.value) ?? countOf(card.perDay?.value) : null,
    total_days: daysOf(card.days?.value),
    as_needed: asNeeded,
    usage: topical ? topicalUsage(card) : String(card.timing?.value ?? '').trim() || null,
    route: card.route ?? inferred.route,
    dosage_form: card.dosageForm ?? inferred.dosageForm,
  };
}

/**
 * 바르는 약의 용법 — 보호자가 바르는 양을 직접 적었으면('손가락 한 마디만큼') 용법 뒤에 붙여서 남겨요.
 * 서버 용법 칸은 100자까지라 넘으면 잘라요.
 */
function topicalUsage(card) {
  const usage = String(card.timing?.value ?? '').trim();
  const amount = String(card.dose?.value ?? '').trim();
  const custom = amount && amount !== TOPICAL_DOSE_DEFAULT ? `바르는 양: ${amount}` : '';
  return [usage, custom].filter(Boolean).join(', ').slice(0, 100) || null;
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
