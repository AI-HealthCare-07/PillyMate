/**
 * 복약 가이드 API — 8번 POST /prescriptions/{id}/guide (만들기), 9번 GET /prescriptions/{id}/guide (조회).
 * 서버는 guide_content를 화면 형식(schedule·asNeeded·howTo·life·danger·summary·disclaimer)으로 저장해 둬요.
 */

export class PrescriptionGuideError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'PrescriptionGuideError';
    this.status = status;
  }
}

// 가이드 만들기는 LLM을 불러서 20초쯤 걸려요(서버 제한 60초). 그보다 조금 넉넉하게 기다려요.
const CREATE_TIMEOUT_MS = 90_000;

async function request(path, { method = 'GET', timeoutMs = 0, fallback }) {
  const token = sessionStorage.getItem('access_token');
  const controller = new AbortController();
  const timer = timeoutMs ? setTimeout(() => controller.abort(), timeoutMs) : null;
  let response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: controller.signal,
    });
  } catch (error) {
    throw new PrescriptionGuideError(
      error.name === 'AbortError' ? '가이드를 만드는 데 너무 오래 걸려요. 다시 시도해 주세요.' : '서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.',
    );
  } finally {
    if (timer) clearTimeout(timer);
  }
  const data = await response.json().catch(() => null);
  if (response.ok) return data;
  const message = typeof data?.detail === 'string' ? data.detail : fallback;
  throw new PrescriptionGuideError(message, response.status);
}

// 같은 처방으로 동시에 두 번 만들지 않아요(개발 모드의 StrictMode는 화면 효과를 두 번 실행해요).
const creating = new Map();

/** 가이드 만들기. 이미 있으면 서버가 새로 만들지 않고 그 가이드를 돌려줘요(200). */
export function createGuide(prescriptionId) {
  const key = String(prescriptionId);
  if (!creating.has(key)) {
    const pending = request(`/prescriptions/${encodeURIComponent(prescriptionId)}/guide`, {
      method: 'POST',
      timeoutMs: CREATE_TIMEOUT_MS,
      fallback: '가이드를 만들지 못했어요. 다시 시도해 주세요.',
    }).finally(() => creating.delete(key));
    creating.set(key, pending);
  }
  return creating.get(key);
}

/** 저장된 가이드 조회 */
export const fetchGuide = (prescriptionId) =>
  request(`/prescriptions/${encodeURIComponent(prescriptionId)}/guide`, { fallback: '가이드를 불러오지 못했어요.' });
