import { ChevronLeft, FileText, ScanLine, CircleUserRound } from 'lucide-react';
import { IconButton } from './Button.jsx';
import { ChildSwitcher, Logo } from './misc.jsx';

export const TABS = [
  { key: 'history', label: '기록', icon: FileText },
  { key: 'upload', label: '처방 올리기', icon: ScanLine },
  { key: 'children', label: '아이', icon: CircleUserRound },
];

/** 모바일 헤더 — 세로 패딩 8, 오른쪽 12, 왼쪽 20(뒤로가기 있으면 4). 제목 22 Bold, 뒤로가기 있으면 18 */
export function Header({ title, onBack, right, className = '' }) {
  return (
    <header className={`flex min-h-[60px] items-center gap-1 py-2 pr-3 ${onBack ? 'pl-1' : 'pl-5'} lg:pl-0 lg:pr-0 lg:pt-8 ${className}`}>
      {onBack && <IconButton icon={ChevronLeft} label="뒤로" onClick={onBack} />}
      <h1 className={`min-w-0 flex-1 truncate font-bold ${onBack ? 'text-18' : 'text-22'}`}>{title}</h1>
      {right}
    </header>
  );
}

/** Figma: TabBar — 높이 64, 위 6 / 아래 10, 아이콘 24 + 라벨 12. 선택 시 브랜드 색 SemiBold */
export function TabBar({ active, onChange }) {
  return (
    <nav aria-label="주요 메뉴" className="border-t border-line bg-surface pb-[max(10px,env(safe-area-inset-bottom))] pt-1.5 lg:hidden">
      <ul className="mx-auto flex max-w-[560px]">
        {TABS.map(({ key, label, icon: Icon }) => {
          const on = key === active;
          return (
            <li key={key} className="flex-1">
              <button
                type="button"
                aria-current={on ? 'page' : undefined}
                onClick={() => onChange?.(key)}
                className={`flex w-full flex-col items-center gap-1 py-1.5 text-12 ${on ? 'font-semibold text-brand' : 'font-medium text-muted'}`}
              >
                <Icon size={24} strokeWidth={on ? 2 : 1.75} aria-hidden />
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** 데스크톱 상단 바 — 높이 68, 가로 40, 간격 32. 1024px 이상에서만 보여요 */
export function TopBar({ active, onChange, childName = '지우' }) {
  return (
    <header className="sticky top-0 z-20 hidden h-17 items-center gap-8 border-b border-line bg-surface px-10 lg:flex">
      <Logo size={26} />
      <nav aria-label="주요 메뉴" className="flex items-center gap-1">
        {TABS.map(({ key, label }) => {
          const on = key === active;
          return (
            <button
              key={key}
              type="button"
              aria-current={on ? 'page' : undefined}
              onClick={() => onChange?.(key)}
              className={`rounded-md px-3.5 py-2.5 text-15 ${on ? 'bg-brand-soft font-semibold text-brand' : 'font-medium text-muted hover:bg-paper'}`}
            >
              {label}
            </button>
          );
        })}
      </nav>
      <div className="flex-1" />
      <ChildSwitcher name={childName} />
    </header>
  );
}

/**
 * 화면 틀.
 * 모바일: (헤더) + 본문 + 아래 고정 영역(주요 버튼, 탭 바)
 * 데스크톱(lg): 상단 바 + 가운데 정렬 본문. 주요 버튼은 본문 끝에 오른쪽 정렬로 놓여요.
 * width: 'form'은 데스크톱에서 480px 한 단, 'wide'는 1120px.
 */
export function AppShell({ tab, onTab, header, actions, showTabs = true, showTopBar = true, width = 'form', children }) {
  const inner = width === 'wide' ? 'lg:max-w-content' : 'lg:max-w-form';
  return (
    <div className="flex min-h-dvh flex-col bg-paper">
      {showTopBar && <TopBar active={tab} onChange={onTab} />}
      <div className={`mx-auto flex w-full max-w-[560px] flex-1 flex-col ${inner}`}>
        {header}
        <main className="flex flex-1 flex-col">{children}</main>
        {actions && ('desktop' in actions ? actions.desktop : actions.mobile) && (
          <div className="hidden lg:flex lg:justify-end lg:gap-3 lg:pb-16">{'desktop' in actions ? actions.desktop : actions.mobile}</div>
        )}
      </div>
      {(actions || showTabs) && (
        <div className="sticky bottom-0 z-10 lg:hidden">
          {actions && (
            <div className="border-t border-line bg-surface px-5 pb-5 pt-3">
              <div className="mx-auto flex max-w-[520px] flex-col gap-2">{actions.mobile}</div>
            </div>
          )}
          {showTabs && <TabBar active={tab} onChange={onTab} />}
        </div>
      )}
    </div>
  );
}

/** 본문 — 가로 20, 위 8, 아래 32, 간격 24(기본) */
export function Body({ className = '', children }) {
  return <div className={`flex flex-1 flex-col gap-6 px-5 pb-8 pt-2 lg:px-0 lg:pt-4 ${className}`}>{children}</div>;
}
