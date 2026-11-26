/**
 * 처방 기록 API — 명세 10번 GET /children/{id}/prescriptions 목록, 6번 GET /prescriptions/{id} 상세,
 * 9절 DELETE /prescriptions/{id} 삭제.
 */

export class PrescriptionRecordsError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'PrescriptionRecordsError';
    this.status = status;
  }
}

async function request(path, { method = 'GET', fallback = '처방 기록을 불러오지 못했어요.' } = {}) {
  const token = sessionStorage.getItem('access_token');
  let response;
  try {
    response = await fetch(`/api/v1${path}`, { method, headers: token ? { Authorization: `Bearer ${token}` } : {} });
  } catch {
    throw new PrescriptionRecordsError('서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.');
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (response.ok) return data;
  const message = typeof data?.detail === 'string' ? data.detail : fallback;
  throw new PrescriptionRecordsError(message, response.status);
}

const getJson = (path) => request(path);

/** 아이의 처방 목록 (최신 등록순). 약 내용은 없고 medication_count만 있어요. */
export const fetchChildPrescriptions = (childId) => getJson(`/children/${encodeURIComponent(childId)}/prescriptions`);

/** 처방 하나의 상세 — 약 목록 포함. 5번 등록 응답과 같은 형식이에요(ocr_confidence만 없음). */
export const fetchPrescriptionDetail = (prescriptionId) => getJson(`/prescriptions/${encodeURIComponent(prescriptionId)}`);

/** 처방 하나를 지워요. 서버가 약·가이드·복약 알림과 남은 원본 사진까지 함께 지워요(204, 본문 없음). */
export const deletePrescription = (prescriptionId) =>
  request(`/prescriptions/${encodeURIComponent(prescriptionId)}`, { method: 'DELETE', fallback: '처방 기록을 지우지 못했어요.' });
