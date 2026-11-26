/**
 * 처방 확인 화면의 '용법' 칸 — 드롭다운에서 고르거나 '직접 입력'으로 적어요.
 * 서버(usage)는 최대 100자 문자열이라 직접 적은 글도 그대로 저장돼요.
 *
 * 처음 보여 주는 방식은 문서마다 달라요.
 * - 처방전: 용법 칸에 적힌 글('1일 3회 식후 30분' 등)을 그대로 직접 입력 칸에 넣어요. 드롭다운으로 바꿔 골라도 돼요.
 * - 약봉투: '□식전 30분 □식후 30분' 체크 표시라서 드롭다운 값으로 맞춰요. 맞는 값이 없으면 읽은 글을 직접 입력 칸에 둬요.
 */
export const USAGE_OPTIONS = ['식전 30분', '식후 30분', '필요시'];
export const USAGE_MAX_LENGTH = 100;

/** 읽은 용법 → 드롭다운 값. 필요할 때 먹는 약이면 '필요시', 어느 것에도 맞지 않으면 ''. */
export function toUsageOption(text, asNeeded = false) {
  const value = String(text ?? '');
  if (asNeeded || /필요|열\s*이?\s*날|아플|prn/i.test(value)) return '필요시';
  if (/식전/.test(value)) return '식전 30분';
  if (/식후/.test(value)) return '식후 30분';
  return '';
}

/**
 * 처음 불러올 때의 용법 값과 입력 방식(mode: 'select' 드롭다운 | 'custom' 직접 입력).
 * sourceType이 없으면(예시 데이터 등) 처방전처럼 읽은 글을 그대로 둬요.
 */
export function initialUsage(text, { sourceType, asNeeded = false } = {}) {
  const raw = String(text ?? '').trim();
  if (sourceType === 'PILL_BAG') {
    const option = toUsageOption(raw, asNeeded);
    if (option || !raw) return { value: option, mode: 'select' };
    return { value: raw, mode: 'custom' };
  }
  if (raw) return { value: raw, mode: 'custom' };
  return { value: asNeeded ? '필요시' : '', mode: 'select' };
}

/** 카드에 저장된 입력 방식. 예전 카드처럼 없으면 값이 드롭다운 목록에 있는지로 정해요. */
export const usageMode = (timing) =>
  timing?.mode ?? (timing?.value && !USAGE_OPTIONS.includes(timing.value) ? 'custom' : 'select');
