import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { children as sampleChildren } from '../data/sample.js';

const STORAGE_KEY = 'pillymate.selectedChildId';
const SelectedChildContext = createContext(null);

function readStored(list) {
  try {
    const id = localStorage.getItem(STORAGE_KEY);
    return list.some((c) => c.id === id) ? id : null;
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
    weight: `${Number(String(weight).replace(/[^\d.]/g, ''))}kg`,
    allergies: list,
    allergy: list.length ? `${list.join(', ')} 알레르기` : null,
    note: note.trim(),
  };
}

/**
 * 아이 목록과 지금 보는 아이. 아이 화면에서 고르면 기록·처방 올리기·메뉴가 모두 이 아이 기준으로 바뀌어요.
 * 새로고침해도 유지되도록 브라우저에는 고른 아이 id만 저장해요.
 * 아이 정보(의료 정보)는 브라우저 저장소에 남기지 않아요. 그래서 추가·수정·삭제는 지금은 이번 방문 동안만 반영돼요.
 * TODO(API): 아이 목록 조회·추가·수정·삭제 API 연결.
 */
export function SelectedChildProvider({ children: content }) {
  const [childList, setChildList] = useState(sampleChildren);
  const [childId, setChildId] = useState(() => readStored(sampleChildren) ?? sampleChildren[0]?.id ?? null);

  const selectChild = useCallback((id) => {
    setChildId(id);
    store(id);
  }, []);

  /** 아이를 목록에서 지워요. 지금 보던 아이였다면 남은 첫 아이로 바꿔요. */
  const removeChild = useCallback(
    (id) => {
      const rest = childList.filter((c) => c.id !== id);
      setChildList(rest);
      if (childId === id) selectChild(rest[0]?.id ?? null);
    },
    [childList, childId, selectChild],
  );

  /** 새 아이를 목록 끝에 넣고, 바로 그 아이를 보도록 골라요. 새 아이 정보를 돌려줘요. */
  const addChild = useCallback(
    (data) => {
      const child = { id: `c${Date.now()}`, ...toChild(data) };
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
      selectChild,
      addChild,
      updateChild,
      removeChild,
    }),
    [childList, childId, selectChild, addChild, updateChild, removeChild],
  );
  return <SelectedChildContext.Provider value={value}>{content}</SelectedChildContext.Provider>;
}

export function useSelectedChild() {
  const ctx = useContext(SelectedChildContext);
  if (!ctx) throw new Error('useSelectedChild는 SelectedChildProvider 안에서만 쓸 수 있어요.');
  return ctx;
}
