import { useCallback, useId, useRef, useState } from 'react';
import { useDialog } from './useDialog.js';

/**
 * 상단 바의 펼침 메뉴(아이 전환, 알림) 공통 틀.
 * trigger({ open, toggle, props })로 버튼을 그리고, children({ close })로 내용을 그려요.
 * 패널은 가장 가까운 relative 조상(상단 바) 오른쪽에 붙어서, 좁은 화면에서도 밖으로 넘치지 않아요.
 * Esc·바깥 누르기로 닫히고, 열려 있는 동안 Tab 이동을 패널 안에 가둬요.
 */
export function Popover({ label, trigger, children, className = '' }) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef(null);
  const id = useId();
  const close = useCallback(() => setOpen(false), []);
  useDialog(open, close, panelRef);

  return (
    <>
      {trigger({
        open,
        toggle: () => setOpen((v) => !v),
        props: { 'aria-haspopup': 'dialog', 'aria-expanded': open, 'aria-controls': id },
      })}
      {open && <div className="fixed inset-0 z-40" onClick={close} aria-hidden />}
      <div
        ref={panelRef}
        id={id}
        role="dialog"
        aria-label={label}
        inert={open ? undefined : ''}
        className={`absolute right-3 top-[calc(100%+8px)] z-50 max-w-[calc(100vw-24px)] origin-top-right rounded-xl border border-line bg-surface shadow-raised transition duration-150 lg:right-10 ${open ? 'scale-100 opacity-100' : 'pointer-events-none scale-95 opacity-0'} ${className}`}
      >
        {children({ close })}
      </div>
    </>
  );
}
