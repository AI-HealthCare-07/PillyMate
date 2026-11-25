import { useId, useRef } from 'react';
import { X } from 'lucide-react';
import { IconButton } from './Button.jsx';
import { useDialog } from './useDialog.js';

/**
 * 가운데 모달 — 바탕 surface, 모서리 14, 최대 폭 560(모바일은 좌우 16 여백).
 * 머리: 제목 18 Bold + 닫기 버튼. 본문은 길면 안쪽에서 스크롤돼요.
 * Esc·바깥 누르기·닫기 버튼으로 닫혀요.
 */
export function Modal({ open, onClose, title, description, children, className = '' }) {
  const panelRef = useRef(null);
  const id = useId();
  useDialog(open, onClose, panelRef);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <div className="absolute inset-0 bg-ink/50" onClick={onClose} aria-hidden />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${id}-title`}
        aria-describedby={description ? `${id}-desc` : undefined}
        className={`relative flex max-h-[92dvh] w-full max-w-[560px] flex-col overflow-hidden rounded-t-2xl bg-surface pb-[env(safe-area-inset-bottom)] shadow-raised sm:max-h-full sm:rounded-2xl sm:pb-0 ${className}`}
      >
        <div className="flex items-center gap-2 border-b border-line py-2.5 pl-5 pr-2">
          <div className="flex min-w-0 flex-1 flex-col">
            <h2 id={`${id}-title`} className="truncate text-18 font-bold">{title}</h2>
            {description && <p id={`${id}-desc`} className="truncate text-13 text-muted">{description}</p>}
          </div>
          <IconButton icon={X} label="닫기" onClick={onClose} />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
