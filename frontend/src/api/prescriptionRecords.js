/** 처방 기록 조회 API (명세 10번 GET /children/{id}/prescriptions 목록, 6번 GET /prescriptions/{id} 상세). */

export class PrescriptionRecordsError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'PrescriptionRecordsError';
    this.status = status;
  }
}

async function getJson(path) {
  const token = sessionStorage.getItem('access_token');
  let response;
  try {
    response = await fetch(`/api/v1${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  } catch {
    throw new PrescriptionRecordsError('서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.');
  }
  const data = await response.json().catch(() => null);
  if (response.ok) return data;
  const message = typeof data?.detail === 'string' ? data.detail : '처방 기록을 불러오지 못했어요.';
  throw new PrescriptionRecordsError(message, response.status);
}

/** 아이의 처방 목록 (최신 등록순). 약 내용은 없고 medication_count만 있어요. */
export const fetchChildPrescriptions = (childId) => getJson(`/children/${encodeURIComponent(childId)}/prescriptions`);

/** 처방 하나의 상세 — 약 목록 포함. 5번 등록 응답과 같은 형식이에요(ocr_confidence만 없음). */
export const fetchPrescriptionDetail = (prescriptionId) => getJson(`/prescriptions/${encodeURIComponent(prescriptionId)}`);
