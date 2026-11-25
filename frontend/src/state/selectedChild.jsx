import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { createChild, fetchChildren, hasLoginToken } from '../api/children.js';

const STORAGE_KEY = 'pillymate.selectedChildId';
const SelectedChildContext = createContext(null);

function readStored() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function store(id) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // 저장이 막힌 브라우저에서는 이번 방문 동안만 유지돼요.
  }
}

/** '2022.03.14', '2022-03-14', '20220314' 모두 받아서 Date로 바꿔요. 날짜가 아니면 null. */
export function parseBirth(text) {
  const m = String(text ?? '').replace(/\s/g, '').match(/^(\d{4})[.\-/]?(\d{1,2})[.\-/]?(\d{1,2})\.?$/);
  if (!m) return null;
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const date = new Date(y, mo - 1, d);
  return date.getFullYear() === y && date.getMonth() === mo - 1 && date.getDate() === d ? date : null;
}

/** 만 나이 — 돌 전이면 개월 수로 */
function ageOf(birth, today = new Date()) {
  let months = (today.getFullYear() - birth.getFullYear()) * 12 + today.getMonth() - birth.getMonth();
  if (today.getDate() < birth.getDate()) months -= 1;
  return months < 12 ? `${Math.max(months, 0)}개월` : `만 ${Math.floor(months / 12)}세`;
}

/** 폼에서 받은 값 → 화면에서 쓰는 아이 정보 */
function toChild({ name, birth, weight, allergies, note }) {
  const b = parseBirth(birth);
  const pad = (n) => String(n).padStart(2, '0');
  const list = allergies.filter((a) => a !== '없음');
  return {
    name: name.trim(),
    birth: `${b.getFullYear()}.${pad(b.getMonth() + 1)}.${pad(b.getDate())}`,
    age: ageOf(b),
    weight: String(weight ?? '').trim() ? `${Number(String(weight).replace(/[^\d.]/g, ''))}kg` : '',
    allergies: list,
    allergy: list.length ? `${list.join(', ')} 알레르기` : null,
    note: note.trim(),
  };
}

/** 서버 자녀(명세 3·4번 응답) → 화면에서 쓰는 아이 정보. id는 화면 전체가 문자열로 다뤄서 바꿔 둬요. */
function fromServerChild(c) {
  const b = parseBirth(c.birth_date);
  const pad = (n) => String(n).padStart(2, '0');
  const list = (c.allergies ?? '').split(',').map((a) => a.trim()).filter(Boolean);
  return {
    id: String(c.child_id),
    name: c.name,
    birth: `${b.getFullYear()}.${pad(b.getMonth() + 1)}.${pad(b.getDate())}`,
    age: ageOf(b),
    weight: c.weight_kg === null || c.weight_kg === undefined ? '' : `${c.weight_kg}kg`,
    allergies: list,
    allergy: list.length ? `${list.join(', ')} 알레르기` : null,
    note: c.notes ?? '',
  };
}

/**
 * 아이 목록과 지금 보는 아이. 아이 화면에서 고르면 기록·처방 올리기·메뉴가 모두 이 아이 기준으로 바뀌어요.
 * 목록은 로그인한 보호자의 자녀를 서버(GET /children)에서 받아 와요. 아이 추가는 POST /children으로 저장해요.
 * 새로고침해도 유지되도록 브라우저에는 고른 아이 id만 저장해요. 아이 정보(의료 정보)는 브라우저 저장소에 남기지 않아요.
 * TODO(API): 아이 수정·삭제 API는 명세상 1차 이후(9절)라, 수정·삭제는 아직 이번 방문 동안만 반영돼요.
 */
export function SelectedChildProvider({ children: content }) {
  const [childList, setChildList] = useState([]);
  const [childId, setChildId] = useState(readStored);
  // idle: 아직 안 불러옴(로그인 전) · loading · ready · error
  const [status, setStatus] = useState('idle');
  const [loadError, setLoadError] = useState('');
  // 앱 시작과 아이 화면 진입이 겹치면 같은 요청이 동시에 나가요. 진행 중인 요청이 있으면 그걸 같이 기다려요.
  const inflight = useRef(null);

  const selectChild = useCallback((id) => {
    setChildId(id);
    store(id);
  }, []);

  /** 서버에서 내 자녀 목록을 다시 받아요. 로그인 직후(아이 화면 진입)와 앱을 열 때 불러요. */
  const refreshChildren = useCallback(async () => {
    if (!hasLoginToken()) {
      setChildList([]);
      setStatus('idle');
      return;
    }
    if (inflight.current) {
      await inflight.current.catch(() => {}); // 실패 처리는 먼저 보낸 쪽이 해요.
      return;
    }
    setStatus('loading');
    setLoadError('');
    inflight.current = fetchChildren();
    try {
      const list = (await inflight.current).map(fromServerChild);
      setChildList(list);
      setChildId((current) => {
        const next = list.some((c) => c.id === current) ? current : (list[0]?.id ?? null);
        store(next);
        return next;
      });
      setStatus('ready');
    } catch (error) {
      setChildList([]);
      setLoadError(error.message);
      setStatus('error');
    } finally {
      inflight.current = null;
    }
  }, []);

  useEffect(() => {
    refreshChildren();
  }, [refreshChildren]);

  /** 아이를 목록에서 지워요. 지금 보던 아이였다면 남은 첫 아이로 바꿔요. */
  const removeChild = useCallback(
    (id) => {
      const rest = childList.filter((c) => c.id !== id);
      setChildList(rest);
      if (childId === id) selectChild(rest[0]?.id ?? null);
    },
    [childList, childId, selectChild],
  );

  /**
   * 서버에 아이를 등록하고, 성공하면 목록 끝에 넣어 바로 그 아이를 골라요.
   * request는 toChildCreateRequest() 결과(명세 3번 본문). 실패하면 서버 문구를 담은 오류를 던져요.
   */
  const addChild = useCallback(
    async (request) => {
      const child = fromServerChild(await createChild(request));
      setChildList((prev) => [...prev, child]);
      selectChild(child.id);
      return child;
    },
    [selectChild],
  );

  const updateChild = useCallback((id, data) => {
    setChildList((prev) => prev.map((c) => (c.id === id ? { ...c, ...toChild(data) } : c)));
  }, []);

  const value = useMemo(
    () => ({
      childList,
      childId,
      child: childList.find((c) => c.id === childId) ?? null,
      status,
      loadError,
      refreshChildren,
      selectChild,
      addChild,
      updateChild,
      removeChild,
    }),
    [childList, childId, status, loadError, refreshChildren, selectChild, addChild, updateChild, removeChild],
  );
  return <SelectedChildContext.Provider value={value}>{content}</SelectedChildContext.Provider>;
}

export function useSelectedChild() {
  const ctx = useContext(SelectedChildContext);
  if (!ctx) throw new Error('useSelectedChild는 SelectedChildProvider 안에서만 쓸 수 있어요.');
  return ctx;
}
