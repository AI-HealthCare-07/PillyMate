/** 자녀 API (명세 3번 POST /children 등록, 4번 GET /children 내 자녀 목록, 9절 PATCH·DELETE /children/{id} 수정·삭제). */

const ENDPOINT = '/api/v1/children';

export class ChildApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ChildApiError';
    this.status = status;
  }
}

export const hasLoginToken = () => Boolean(sessionStorage.getItem('access_token'));

async function request(options = {}, path = '') {
  const token = sessionStorage.getItem('access_token');
  let response;
  try {
    response = await fetch(`${ENDPOINT}${path}`, {
      ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    });
  } catch {
    throw new ChildApiError('서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.');
  }
  // 삭제 성공(204)은 본문이 없어서 null이에요.
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

/** 자녀 정보 수정. body에는 바꿀 항목만 넣어요(toChildUpdateRequest). 수정된 자녀를 돌려받아요. */
export const updateChild = (childId, body) => request({ method: 'PATCH', body: JSON.stringify(body) }, `/${encodeURIComponent(childId)}`);

/** 자녀 삭제. 그 아이의 처방·약·가이드·알림과 원본 사진도 서버에서 함께 영구 삭제돼요. */
export const deleteChild = (childId) => request({ method: 'DELETE' }, `/${encodeURIComponent(childId)}`);
