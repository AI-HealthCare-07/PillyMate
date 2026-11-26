/**
 * 복약 알림 설정 API — 처방마다 알림 켜기/끄기와 먹는 때(아침·점심·저녁)별 알림 시각.
 * GET /children/{id}/alarms: 아이의 확정된 처방마다 { prescription_id, enabled, times: { 아침: '08:00' }, start_date, end_date }
 * PATCH /prescriptions/{id}/alarms: { enabled?, times? } — 보낸 항목만 바꿔요.
 */

export class AlarmApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'AlarmApiError';
    this.status = status;
  }
}

export async function request(path, { method = 'GET', body, fallback = '알림 설정을 불러오지 못했어요.' } = {}) {
  const token = sessionStorage.getItem('access_token');
  let response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new AlarmApiError('서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.');
  }
  const data = await response.json().catch(() => null);
  if (response.ok) return data;
  const message = typeof data?.detail === 'string' ? data.detail : fallback;
  throw new AlarmApiError(message, response.status);
}

/** 아이의 확정된 처방마다 알림 설정 */
export const fetchChildAlarms = (childId) => request(`/children/${encodeURIComponent(childId)}/alarms`);

/** 처방의 알림 켜기/끄기·시각 저장. 저장된 설정을 돌려받아요. */
export const updatePrescriptionAlarms = (prescriptionId, body) =>
  request(`/prescriptions/${encodeURIComponent(prescriptionId)}/alarms`, { method: 'PATCH', body, fallback: '알림 설정을 저장하지 못했어요.' });
