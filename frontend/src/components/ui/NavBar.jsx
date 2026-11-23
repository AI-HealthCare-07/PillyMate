import { useCallback, useId, useRef, useState } from 'react';
import { ChevronRight, CircleUserRound, FileText, House, LogOut, Menu, MessageCircle, ScanLine, X } from 'lucide-react';
import { IconButton } from './Button.jsx';
import { Avatar, Logo } from './misc.jsx';
import { useDialog } from './useDialog.js';
import { useSelectedChild } from '../../state/selectedChild.jsx';

/** 모바일 하단 탭 바 메뉴 */
export const TABS = [
  { key: 'home', label: '홈', icon: House },
  { key: 'history', label: '기록', icon: FileText },
  { key: 'upload', label: '처방 올리기', icon: ScanLine },
  { key: 'chat', label: '챗봇', icon: MessageCircle },
];

/** 드로어 메뉴 — 하단 탭 + 드로어에만 있는 항목(아이) */
export const MENU = [...TABS, { key: 'children', label: '아이', icon: CircleUserRound }];

/**
 * 상단 네비게이션 바 — 왼쪽 로고, 오른쪽 메뉴(드로어) 버튼.
 * 높이: 모바일 56, 데스크톱(lg) 68. 가로 패딩: 모바일 왼쪽 20 / 오른쪽 8, 데스크톱 40.
 */
export function NavBar({ active, onNavigate }) {
  const childName = useSelectedChild().child?.name ?? '아이 없음';
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);
  const drawerId = useId();

  const close = useCallback(() => {
    setOpen(false);
    triggerRef.current?.focus();
  }, []);
  const navigate = (key) => {
    setOpen(false);
    onNavigate?.(key);
  };

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-line bg-surface">
        <div className="flex h-14 items-center justify-between pl-5 pr-2 lg:h-17 lg:px-10">
          <button type="button" onClick={() => onNavigate?.('home')} aria-label="PillyMate 홈으로" className="rounded-md">
            <Logo size={26} />
          </button>
          <IconButton
            ref={triggerRef}
            icon={Menu}
            label="메뉴 열기"
            aria-haspopup="dialog"
            aria-expanded={open}
            aria-controls={drawerId}
            onClick={() => setOpen(true)}
          />
        </div>
      </header>
      <Drawer id={drawerId} open={open} onClose={close} active={active} onNavigate={navigate} childName={childName} />
    </>
  );
}

/**
 * 오른쪽에서 열리는 드로어 — 폭 320(화면의 최대 85%), 바탕 surface, 왼쪽 그림자.
 * Esc·바깥 누르기로 닫히고, 열려 있는 동안 뒤 화면 스크롤과 Tab 이동을 막아요.
 */
export function Drawer({ id, open, onClose, active, onNavigate, childName }) {
  const panelRef = useRef(null);
  const titleId = `${id}-title`;

  useDialog(open, onClose, panelRef);

  return (
    <div className={`fixed inset-0 z-40 ${open ? '' : 'pointer-events-none'}`} aria-hidden={!open}>
      <div
        className={`absolute inset-0 bg-ink/40 transition-opacity duration-200 ${open ? 'opacity-100' : 'opacity-0'}`}
        onClick={onClose}
      />
      <div
        ref={panelRef}
        id={id}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        inert={open ? undefined : ''}
        className={`absolute inset-y-0 right-0 flex w-[320px] max-w-[85vw] flex-col bg-surface transition-transform duration-200 ease-out ${open ? 'translate-x-0 shadow-[-8px_0_24px_rgba(13,51,41,0.14)]' : 'translate-x-full'}`}
      >
        <div className="flex h-14 items-center justify-between pl-5 pr-2 lg:h-17 lg:pr-6">
          <h2 id={titleId} className="text-17 font-bold">메뉴</h2>
          <IconButton icon={X} label="메뉴 닫기" onClick={onClose} />
        </div>

        <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-4 pb-6 pt-2">
          {/* 지금 고른 아이 */}
          <button
            type="button"
            onClick={() => onNavigate('children')}
            className="flex items-center gap-3 rounded-xl border border-line px-4 py-3.5 text-left hover:bg-paper"
          >
            <Avatar name={childName} size={40} />
            <span className="flex flex-1 flex-col gap-0.5">
              <span className="text-13 text-muted">지금 보는 아이</span>
              <span className="text-16 font-semibold">{childName}</span>
            </span>
            <span className="text-14 font-semibold text-brand">바꾸기</span>
          </button>

          <nav aria-label="주요 메뉴">
            <ul className="flex flex-col gap-1">
              {MENU.map(({ key, label, icon: Icon }) => {
                const on = key === active;
                return (
                  <li key={key}>
                    <button
                      type="button"
                      aria-current={on ? 'page' : undefined}
                      onClick={() => onNavigate(key)}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-3.5 text-16 ${on ? 'bg-brand-soft font-semibold text-brand' : 'font-medium text-ink hover:bg-paper'}`}
                    >
                      <Icon size={22} strokeWidth={on ? 2 : 1.75} aria-hidden />
                      <span className="flex-1 text-left">{label}</span>
                      <ChevronRight size={18} className={on ? 'text-brand' : 'text-faint'} aria-hidden />
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          <div className="mt-auto border-t border-line pt-4">
            <button
              type="button"
              onClick={() => onNavigate('login')}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-15 font-medium text-muted hover:bg-paper"
            >
              <LogOut size={20} strokeWidth={1.75} aria-hidden />
              로그아웃
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
