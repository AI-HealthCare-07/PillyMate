import { ChevronLeft } from 'lucide-react';
import { IconButton } from './Button.jsx';
import { NavBar, TABS } from './NavBar.jsx';
import { Logo } from './misc.jsx';

export { TABS };

/** 화면 머리 — 모바일: 높이 60, 제목 22 Bold(뒤로가기 있으면 18). 데스크톱: 위 여백을 두고 제목 26 */
export function Header({ title, onBack, right, className = '' }) {
  return (
    <header className={`flex min-h-[60px] items-center gap-1 py-2 pr-3 ${onBack ? 'pl-1' : 'pl-5'} lg:min-h-0 lg:gap-2 lg:px-0 lg:pb-2 lg:pt-8 ${className}`}>
      {onBack && <IconButton icon={ChevronLeft} label="뒤로" onClick={onBack} className="lg:-ml-2.5" />}
      <h1 className={`min-w-0 flex-1 truncate font-bold tracking-[-0.02em] ${onBack ? 'text-18 lg:text-24' : 'text-22 lg:text-28'}`}>{title}</h1>
      {right}
    </header>
  );
}

/** 모바일 하단 탭 바 — 칸마다 56px 이상. 지금 화면은 라이트 세이지 알약, 처방 올리기는 버터 옐로 원으로 늘 눈에 띄게 */
export function TabBar({ active, onChange }) {
  return (
    <nav aria-label="주요 메뉴" className="border-t border-line bg-surface pb-[max(6px,env(safe-area-inset-bottom))] pt-1 lg:hidden">
      <ul className="mx-auto flex max-w-[560px]">
        {TABS.map(({ key, label, icon: Icon }) => {
          const on = key === active;
          const center = key === 'upload';
          return (
            <li key={key} className="flex-1">
              <button
                type="button"
                aria-current={on ? 'page' : undefined}
                onClick={() => onChange?.(key)}
                className={`flex min-h-[56px] w-full flex-col items-center justify-center gap-1 text-12 ${on ? 'font-semibold text-brand' : 'font-medium text-muted'}`}
              >
                <span className={`flex items-center justify-center rounded-pill transition-colors ${center ? `size-9 bg-mark text-ink ${on ? 'ring-2 ring-brand' : ''}` : on ? 'h-7 w-12 bg-brand-soft' : 'h-7 w-12'}`}>
                  <Icon size={center ? 20 : 21} strokeWidth={on || center ? 2 : 1.75} aria-hidden />
                </span>
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** 데스크톱(lg) 왼쪽 사이드 메뉴 — 기존 주요 메뉴(TABS)를 그대로 세로로 놓아요. */
function SideNav({ active, onChange }) {
  return (
    <aside className="sticky top-0 hidden h-dvh w-[232px] shrink-0 flex-col gap-9 border-r border-line bg-surface px-4 py-6 lg:flex">
      <button type="button" onClick={() => onChange?.('home')} aria-label="PillyMate 홈으로" className="self-start rounded-md px-2 py-1">
        <Logo size={26} />
      </button>
      <nav aria-label="주요 메뉴">
        <ul className="flex flex-col gap-0.5">
          {TABS.map(({ key, label, icon: Icon }) => {
            const on = key === active;
            return (
              <li key={key}>
                <button
                  type="button"
                  aria-current={on ? 'page' : undefined}
                  onClick={() => onChange?.(key)}
                  className={`flex h-11 w-full items-center gap-3 rounded-lg px-3 text-15 transition-colors ${on ? 'bg-brand-soft font-semibold text-brand' : 'font-medium text-muted hover:bg-paper hover:text-ink'}`}
                >
                  <Icon size={20} strokeWidth={on ? 2 : 1.75} aria-hidden />
                  {label}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}

const WIDTHS = {
  form: 'lg:max-w-form',      // 입력·확인 화면 — 한 단
  reading: 'lg:max-w-reading', // 읽는 화면(가이드, 챗봇)
  wide: 'lg:max-w-content',    // 목록·대시보드
};

/**
 * 화면 틀 — 모든 화면이 같이 써요.
 * 모바일: 위 NavBar(로고·알림·아이 칩) + 본문 + 아래 고정 영역(주요 버튼, 탭 바)
 * 데스크톱(lg): 왼쪽 사이드 메뉴 + 오른쪽 위 알림·아이 칩 + 본문(화면 성격에 맞는 최대 폭, 왼쪽 정렬)
 * width: 'form'(560) · 'reading'(720) · 'wide'(1120)
 * actionsBar: false면 모바일 아래 버튼 영역의 흰 바탕과 윗줄을 빼고 버튼만 띄워요.
 */
export function AppShell({ tab, onTab, header, actions, actionsBar = true, showTabs = true, showTopBar = true, width = 'form', children }) {
  const inner = WIDTHS[width] ?? WIDTHS.form;
  return (
    <div className="flex min-h-dvh bg-paper">
      {showTopBar && <SideNav active={tab} onChange={onTab} />}
      <div className="flex min-w-0 flex-1 flex-col">
        {showTopBar && <NavBar active={tab} onNavigate={onTab} />}
        <div className="flex w-full flex-1 flex-col lg:px-10 xl:px-14">
          <div className={`mx-auto flex w-full max-w-[560px] flex-1 flex-col ${showTopBar ? 'lg:mx-0' : ''} ${inner}`}>
            {header}
            <main className="flex flex-1 flex-col">{children}</main>
            {actions && ('desktop' in actions ? actions.desktop : actions.mobile) && (
              <div className="hidden lg:sticky lg:bottom-0 lg:z-10 lg:flex lg:justify-end lg:gap-3 lg:border-t lg:border-line lg:bg-paper lg:pb-8 lg:pt-5">{'desktop' in actions ? actions.desktop : actions.mobile}</div>
            )}
          </div>
        </div>
        {(actions || showTabs) && (
          <div className="sticky bottom-0 z-10 lg:hidden">
            {actions && (
              <div className={`px-5 pb-[max(16px,env(safe-area-inset-bottom))] pt-3 ${actionsBar ? 'border-t border-line bg-surface' : ''} ${showTabs ? 'pb-3' : ''}`}>
                <div className="mx-auto flex max-w-[520px] flex-col gap-2">{actions.mobile}</div>
              </div>
            )}
            {showTabs && <TabBar active={tab} onChange={onTab} />}
          </div>
        )}
      </div>
    </div>
  );
}

/** 본문 — 가로 20, 위 8, 아래 32, 간격 24(기본). 데스크톱은 틀이 좌우 여백을 줘요. */
export function Body({ className = '', children }) {
  return <div className={`flex flex-1 flex-col gap-6 px-5 pb-8 pt-2 lg:px-0 lg:pb-12 lg:pt-4 ${className}`}>{children}</div>;
}
