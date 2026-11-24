import { BookOpen, Check, ChevronDown, FileText, House, LogOut, MessageCircle, ScanLine, Settings2 } from 'lucide-react';
import { Avatar, Logo } from './misc.jsx';
import { Popover } from './Popover.jsx';
import { NotificationMenu } from './Notifications.jsx';
import { useSelectedChild } from '../../state/selectedChild.jsx';

/** 주요 메뉴 — 모바일은 하단 탭 바, 데스크톱(lg)은 상단 바 가운데에 놓여요. */
export const TABS = [
  { key: 'home', label: '홈', icon: House },
  { key: 'history', label: '기록', icon: FileText },
  { key: 'upload', label: '처방 올리기', icon: ScanLine },
  { key: 'guides', label: '가이드', icon: BookOpen },
  { key: 'chat', label: '챗봇', icon: MessageCircle },
];

/**
 * 상단 바 — 왼쪽 로고, (데스크톱) 가운데 주요 메뉴, 오른쪽 알림 버튼과 아이 전환 칩.
 * 아이 관리·로그아웃처럼 탭에 없는 메뉴는 아이 전환 칩을 눌러 여는 메뉴에 모았어요.
 * 높이: 모바일 56, 데스크톱(lg) 68.
 */
export function NavBar({ active, onNavigate }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
      <div className="relative mx-auto flex h-14 max-w-content items-center gap-6 pl-5 pr-3 lg:h-17 lg:px-10">
        <button type="button" onClick={() => onNavigate?.('home')} aria-label="PillyMate 홈으로" className="rounded-md">
          <Logo size={26} />
        </button>
        <nav aria-label="주요 메뉴" className="hidden flex-1 lg:block">
          <ul className="flex gap-1">
            {TABS.map(({ key, label }) => {
              const on = key === active;
              return (
                <li key={key}>
                  <button
                    type="button"
                    aria-current={on ? 'page' : undefined}
                    onClick={() => onNavigate?.(key)}
                    className={`rounded-md px-3 py-2 text-15 ${on ? 'bg-brand-soft font-semibold text-brand' : 'font-medium text-muted hover:bg-paper hover:text-ink'}`}
                  >
                    {label}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="ml-auto flex items-center gap-1.5">
          <NotificationMenu onNavigate={onNavigate} />
          <ChildMenu active={active} onNavigate={onNavigate} />
        </div>
      </div>
    </header>
  );
}

/** 아이 전환 칩 + 펼침 메뉴. 아이를 바로 바꾸고, 아이 관리·추가·로그아웃으로 갈 수 있어요. */
function ChildMenu({ active, onNavigate }) {
  const { childList, childId, child, selectChild } = useSelectedChild();
  const name = child?.name ?? '아이 없음';

  return (
    <Popover
      label="아이 선택과 메뉴"
      className="w-[280px] p-2"
      trigger={({ open, toggle, props }) => (
        <button
          type="button"
          onClick={toggle}
          aria-label={`아이 바꾸기, 지금은 ${name}`}
          className={`inline-flex h-10 items-center gap-1.5 rounded-pill border py-1.5 pl-1.5 pr-2.5 transition-colors ${open || active === 'children' ? 'border-brand bg-brand-soft' : 'border-line bg-surface hover:bg-paper'}`}
          {...props}
        >
          {child ? <Avatar name={name} size={28} /> : <span className="size-7 rounded-full bg-sunk" aria-hidden />}
          <span className="text-15 font-semibold">{name}</span>
          <ChevronDown size={16} className={`text-muted transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
        </button>
      )}
    >
      {({ close }) => {
        const go = (key) => {
          close();
          onNavigate?.(key);
        };
        return (
          <>
            <p className="px-3 pb-1 pt-2 text-13 font-medium text-faint">지금 볼 아이</p>
            {!childList.length && <p className="px-3 py-2 text-14 text-muted">등록된 아이가 없어요.</p>}
            <ul>
              {childList.map((c) => {
                const on = c.id === childId;
                return (
                  <li key={c.id}>
                    <button
                      type="button"
                      aria-pressed={on}
                      onClick={() => {
                        selectChild(c.id);
                        close();
                      }}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left ${on ? 'bg-brand-soft' : 'hover:bg-paper'}`}
                    >
                      <Avatar name={c.name} size={34} />
                      <span className="flex flex-1 flex-col">
                        <span className={`text-15 font-semibold ${on ? 'text-brand' : ''}`}>{c.name}</span>
                        <span className="text-13 text-muted">{c.age}, {c.weight}</span>
                      </span>
                      {on && <Check size={18} strokeWidth={2.5} className="text-brand" aria-hidden />}
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className="my-2 border-t border-line" />
            <MenuItem icon={Settings2} onClick={() => go('children')}>아이 정보 관리</MenuItem>
            <MenuItem icon={LogOut} onClick={() => go('login')} muted>로그아웃</MenuItem>
          </>
        );
      }}
    </Popover>
  );
}

function MenuItem({ icon: Icon, muted, children, ...props }) {
  return (
    <button
      type="button"
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-15 font-medium hover:bg-paper ${muted ? 'text-muted' : 'text-ink'}`}
      {...props}
    >
      <Icon size={19} strokeWidth={1.75} aria-hidden />
      {children}
    </button>
  );
}
