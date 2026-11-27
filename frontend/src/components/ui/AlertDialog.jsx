import { useId, useRef } from 'react';
import { useDialog } from './useDialog.js';

const ignore = () => {};

/**
 * 알럿 다이얼로그 — 사용자가 안의 버튼을 눌러야만 닫혀요.
 * Modal과 달리 닫기 버튼이 없고, Esc·바깥 누르기로도 닫히지 않아요.
 * 열려 있는 동안 뒤 화면은 덮개가 클릭을 막고, Tab 이동은 다이얼로그 안에 갇혀요.
 * 그래서 children에는 포커스할 수 있는 요소로 보이는 버튼만 넣어 주세요 (숨긴 input은 바깥에 두기).
 */
export function AlertDialog({ open, title, description, children }) {
  const panelRef = useRef(null);
  const id = useId();
  useDialog(open, ignore, panelRef);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink/50" aria-hidden />
      <div
        ref={panelRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={`${id}-title`}
        aria-describedby={`${id}-desc`}
        className="relative flex max-h-full w-full max-w-[480px] flex-col gap-5 overflow-y-auto rounded-2xl border border-line bg-surface p-6 shadow-raised"
      >
        <div className="flex flex-col gap-1.5">
          <h2 id={`${id}-title`} className="text-20 font-bold">{title}</h2>
          <p id={`${id}-desc`} className="text-15 text-muted">{description}</p>
        </div>
        {children}
      </div>
    </div>
  );
}
