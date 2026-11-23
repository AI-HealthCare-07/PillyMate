import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { children } from '../data/sample.js';

const STORAGE_KEY = 'pillymate.selectedChildId';
const SelectedChildContext = createContext(null);

function readStored() {
  try {
    const id = localStorage.getItem(STORAGE_KEY);
    return children.some((c) => c.id === id) ? id : null;
  } catch {
    return null;
  }
}

/**
 * 지금 보는 아이. 아이 화면에서 고르면 기록·처방 올리기·메뉴가 모두 이 아이 기준으로 바뀌어요.
 * 새로고침해도 유지되도록 브라우저에 아이 id만 저장해요.
 */
export function SelectedChildProvider({ children: content }) {
  const [childId, setChildId] = useState(() => readStored() ?? children[0]?.id ?? null);

  const selectChild = useCallback((id) => {
    setChildId(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // 저장이 막힌 브라우저에서는 이번 방문 동안만 유지돼요.
    }
  }, []);

  const value = useMemo(
    () => ({ childId, child: children.find((c) => c.id === childId) ?? null, selectChild }),
    [childId, selectChild],
  );
  return <SelectedChildContext.Provider value={value}>{content}</SelectedChildContext.Provider>;
}

export function useSelectedChild() {
  const ctx = useContext(SelectedChildContext);
  if (!ctx) throw new Error('useSelectedChild는 SelectedChildProvider 안에서만 쓸 수 있어요.');
  return ctx;
}
