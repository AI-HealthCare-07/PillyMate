/**
 * 5번 POST /prescriptions (처방전 사진 등록 + OCR) 호출과 응답 변환.
 *
 * 서버 신뢰도 판정 (ocr/ocr_confidence_policy.py, 11/24 멘토링 3절):
 * - 가장 낮은 약 신뢰도 0.6 미만 또는 약을 못 읽음 → 422 { code: 'OCR_LOW_CONFIDENCE' }, 저장 안 됨 → 다시 찍기
 * - 0.6 이상 0.8 미만 약이 있음 → 201, 그 약은 low_confidence: true → S-04에서 노란 표시로 직접 확인
 * - 모두 0.8 이상 → 201
 * OCR 실패·시간 초과(502)도 저장되지 않으므로 다시 찍기로 안내해요.
 */

const ENDPOINT = '/api/v1/prescriptions';
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
// 서버(OCR)가 읽을 수 있는 형식만 받아요 (명세 5번: jpg·png).
export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png'];
export const ACCEPT_ATTRIBUTE = ACCEPTED_IMAGE_TYPES.join(',');

/** 고른 사진이 서버 규칙에 맞는지 봐요. 맞으면 '', 아니면 보여 줄 문구. */
export function imageFileProblem(file) {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) return 'JPG, PNG 사진만 올릴 수 있어요.';
  if (file.size > MAX_IMAGE_BYTES) return '사진은 10MB 이하로 선택해 주세요.';
  if (!file.size) return '비어 있는 파일은 올릴 수 없어요.';
  return '';
}

export class PrescriptionRegistrationError extends Error {
  constructor(message, { retake = false, status = 0 } = {}) {
    super(message);
    this.name = 'PrescriptionRegistrationError';
    this.retake = retake;
    this.status = status;
  }
}

export async function registerPrescription({ childId, sourceType = 'PRESCRIPTION', file, disease, note }) {
  const form = new FormData();
  form.append('child_id', String(childId));
  form.append('source_type', sourceType);
  form.append('image', file);
  if (disease) form.append('diagnosis_user_input', disease);
  if (note) form.append('symptom_notes', note);

  const token = sessionStorage.getItem('access_token');
  let response;
  try {
    response = await fetch(ENDPOINT, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
  } catch {
    throw new PrescriptionRegistrationError('서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.');
  }

  const data = await response.json().catch(() => ({}));
  if (response.ok) return data;

  const message = typeof data.detail === 'string' ? data.detail : '처방전을 올리지 못했어요.';
  const retake = data.code === 'OCR_LOW_CONFIDENCE' || response.status === 502;
  throw new PrescriptionRegistrationError(message, { retake, status: response.status });
}

// 화면에는 소수 둘째 자리까지만 보여요 (0.3333포 → 0.33포). 확정 때 보낼 원래 숫자는 서버에 그대로 있어요.
const number = (value) => (value === null || value === undefined ? '' : String(Math.round(Number(value) * 100) / 100));

/** 응답 약 하나 → S-04 약 카드 형식. 신뢰도가 낮은 약은 값이 있는 칸마다 '확인 필요'를 달아요. */
export function toConfirmMed(med) {
  const perDay = med.as_needed
    ? med.max_daily_count ? `필요할 때, 최대 ${med.max_daily_count}번` : '필요할 때'
    : med.daily_count ? `${med.daily_count}번` : '';
  const values = {
    dose: med.dose_per_time === null ? '' : `${number(med.dose_per_time)}${med.unit ?? ''}`,
    perDay,
    days: med.total_days ? `${med.total_days}일` : '',
    timing: med.usage ?? '',
  };
  return {
    id: `rx-med-${med.medication_id}`,
    medicationId: med.medication_id,
    name: med.name,
    confidence: med.confidence,
    ...Object.fromEntries(
      Object.entries(values).map(([key, value]) => [key, med.low_confidence && value ? { value, low: true } : { value }]),
    ),
  };
}

/** 등록 응답 → 처방 임시 데이터(fe2Draft)에 넣을 값 */
export function draftFieldsFromRegistration(data) {
  return {
    status: 'ocr-done',
    prescriptionId: data.prescription_id,
    sourceType: data.source_type,
    ocrConfidence: data.ocr_confidence,
    ocr: {
      hospital: data.hospital_name ?? '병원 이름을 읽지 못했어요',
      // 약봉투에는 처방일이 없어서 null이에요. 확인 화면에서 약 받은 날을 직접 고르게 해요.
      date: data.prescription_date ?? null,
      disease: data.diagnosis_user_input || data.diagnosis_extracted || '',
    },
    ocrMeds: data.medications.map(toConfirmMed),
  };
}
