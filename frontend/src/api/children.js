/** 자녀 API (명세 3번 POST /children 등록, 4번 GET /children 내 자녀 목록). */

const ENDPOINT = '/api/v1/children';

export class ChildApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ChildApiError';
    this.status = status;
  }
}

export const hasLoginToken = () => Boolean(sessionStorage.getItem('access_token'));

async function request(options = {}) {
  const token = sessionStorage.getItem('access_token');
  let response;
  try {
    response = await fetch(ENDPOINT, {
      ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    });
  } catch {
    throw new ChildApiError('서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.');
  }
  const data = await response.json().catch(() => null);
  if (response.ok) return data;
  // 자동 검증 422는 detail이 목록이라 명세 8절대로 공통 문구로 바꿔요.
  const message = typeof data?.detail === 'string' ? data.detail : '입력 내용을 확인해 주세요.';
  throw new ChildApiError(message, response.status);
}

/** 로그인한 보호자의 자녀 목록 (등록 순서) */
export const fetchChildren = () => request();

/** 자녀 등록. body는 AddChildConsent.jsx의 toChildCreateRequest() 결과 그대로예요. */
export const createChild = (body) => request({ method: 'POST', body: JSON.stringify(body) });
