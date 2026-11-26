/**
 * 처방 확인 화면의 '먹는 때' 드롭다운 — 보호자는 이 세 가지 중에서만 골라요.
 * OCR이 읽은 용법('식후30분', '->식후 30분 취침전', '필요시 1일 최대 4회' 등)은 가장 가까운 것으로 바꿔요.
 */
export const TAKING_TIME_OPTIONS = ['식전 30분', '식후 30분', '필요시'];

/** 읽은 용법 → 드롭다운 값. 필요할 때 먹는 약이면 '필요시', 어느 것에도 맞지 않으면 ''(비어 있음). */
export function toTakingTimeOption(text, asNeeded = false) {
  const value = String(text ?? '');
  if (asNeeded || /필요|열\s*이?\s*날|아플|prn/i.test(value)) return '필요시';
  if (/식전/.test(value)) return '식전 30분';
  if (/식후/.test(value)) return '식후 30분';
  return '';
}
