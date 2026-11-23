import { useEffect, useRef } from 'react';

const FOCUSABLE = 'button:not([disabled]), a[href], input, textarea, select, [tabindex]:not([tabindex="-1"])';

/**
 * 모달·드로어 공통 동작.
 * 열리면: 안쪽 첫 버튼에 포커스, 뒤 화면 스크롤 잠금, Esc로 닫기, Tab 이동을 안쪽에 가두기.
 * 닫히면: 열기 전 포커스가 있던 곳으로 돌려놔요.
 */
export function useDialog(open, onClose, panelRef) {
  // onClose는 렌더마다 새 함수일 수 있어요. 의존성에 넣으면 입력할 때마다 이 효과가 다시 돌면서
  // 포커스가 첫 버튼으로 튀어 버려요(입력칸에 글자가 안 써지는 문제). 그래서 최신 값만 ref로 들고 있어요.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    const panel = panelRef.current;
    const opener = document.activeElement;
    // data-autofocus가 붙은 칸이 있으면 그 칸부터, 없으면 첫 버튼에 포커스해요.
    (panel?.querySelector('[data-autofocus]') ?? panel?.querySelector(FOCUSABLE))?.focus();
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCloseRef.current();
        return;
      }
      if (e.key !== 'Tab' || !panel) return;
      const items = panel.querySelectorAll(FOCUSABLE);
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
      if (opener instanceof HTMLElement && document.contains(opener)) opener.focus();
    };
  }, [open, panelRef]);
}
