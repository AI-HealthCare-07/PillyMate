import { useEffect, useState } from 'react';
import { Bell, BellOff, Check, Clock, Pill } from 'lucide-react';
import { Avatar } from './misc.jsx';
import { Popover } from './Popover.jsx';
import { useSelectedChild } from '../../state/selectedChild.jsx';
import { NO_ALARM_SLOTS, hhmm, todayKey, useRecords } from '../../state/records.jsx';

/** 1분마다 다시 그려서, 시간이 되면 알림이 저절로 생겨요. */
function useNow() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(t);
  }, []);
  return now;
}

/**
 * 등록된 아이 모두의 오늘 약을 아이·먹는 때별로 묶어요.
 * due: 시간이 지났는데 아직 다 안 먹인 것(알림) / next: 아직 시간이 안 된 가장 가까운 것(예정)
 * byChild: 알림이 있는 아이별 묶음. 지금 보는 아이가 맨 위에 와요.
 */
function useDoseReminders() {
  const now = useNow();
  const { childList, childId } = useSelectedChild();
  const { dosesOn, isAlarmOn, alarmSince, alarmTimeOf } = useRecords();
  const today = todayKey();
  const minutes = now.getHours() * 60 + now.getMinutes();

  const groups = childList.flatMap((child) => {
    // 처방마다 알림 시각을 따로 정할 수 있어서, 아이·먹는 때·시각이 같은 약끼리 묶어요.
    const byTime = new Map();
    // 복약 가이드에서 알림을 끈 처방의 약은 빼요.
    // 자기 전처럼 알림을 보내지 않는 먹는 때도 빼요.
    for (const d of dosesOn(child.id, today).filter((x) => isAlarmOn(x.course.visitId) && !NO_ALARM_SLOTS.includes(x.slot))) {
      const time = alarmTimeOf(d.course.visitId, d.slot);
      const slotAt = new Date(now.getFullYear(), now.getMonth(), now.getDate(), time[0], time[1]).getTime();
      // 알림을 켠(또는 가이드를 만든) 뒤에 오는 시각만 알려요.
      const since = alarmSince(d.course.visitId);
      if (since != null && slotAt < since) continue;
      const key = `${d.slot}|${hhmm(time)}`;
      if (!byTime.has(key)) byTime.set(key, { id: `${child.id}|${key}`, child, slot: d.slot, time, at: time[0] * 60 + time[1], doses: [] });
      byTime.get(key).doses.push(d);
    }
    return [...byTime.values()];
  });
  const pending = groups.filter((g) => g.doses.some((d) => !d.given));
  const due = pending.filter((g) => g.at <= minutes).sort((a, b) => b.at - a.at);
  const next = pending.filter((g) => g.at > minutes).sort((a, b) => a.at - b.at)[0] ?? null;
  const byChild = childList
    .map((child) => ({ child, items: due.filter((g) => g.child.id === child.id) }))
    .filter((c) => c.items.length)
    .sort((a, b) => (a.child.id === childId ? -1 : b.child.id === childId ? 1 : 0));
  return { due, next, byChild };
}

/** 상단 바 알림 버튼 — 아이 모두의 약 먹일 시간 알림 수를 빨간 배지로 보여 줘요. */
export function NotificationMenu({ onNavigate }) {
  const { due, next, byChild } = useDoseReminders();
  const { selectChild } = useSelectedChild();
  const { toggleDose } = useRecords();
  const count = due.length;

  // 알림을 누르면 그 아이로 바꾸고 홈(오늘 먹을 약)으로 가요.
  const open = (g, close) => {
    selectChild(g.child.id);
    close();
    onNavigate?.('home');
  };
  const markGiven = (g) => g.doses.filter((d) => !d.given).forEach(toggleDose);

  return (
    <Popover
      label="알림"
      className="w-[340px]"
      trigger={({ open: isOpen, toggle, props }) => (
        <button
          type="button"
          onClick={toggle}
          aria-label={count ? `알림 ${count}개` : '알림'}
          className={`relative inline-flex size-11 items-center justify-center rounded-full transition-colors ${isOpen ? 'bg-brand-soft text-brand' : 'text-ink hover:bg-sunk'}`}
          {...props}
        >
          <Bell size={22} strokeWidth={1.75} aria-hidden />
          {count > 0 && (
            <span className="absolute right-0.5 top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-danger px-1 text-[11px] font-bold leading-none text-on-brand ring-2 ring-surface">
              {count}
            </span>
          )}
        </button>
      )}
    >
      {({ close }) => (
        <div className="flex max-h-[min(70vh,520px)] flex-col">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-16 font-bold">알림</h2>
            {count > 0 && <span className="text-13 font-semibold text-danger">확인할 알림 {count}개</span>}
          </div>
          <div className="flex flex-col overflow-y-auto p-2">
            {due.length === 0 && (
              <div className="flex flex-col items-center gap-2 px-4 py-6 text-center">
                <BellOff size={26} strokeWidth={1.5} className="text-faint" aria-hidden />
                <p className="text-15 font-semibold">지금 먹일 약이 없어요</p>
                <p className="text-13 text-muted">아이들 약 먹을 시간이 되면 여기에서 알려 드려요.</p>
              </div>
            )}
            {byChild.map(({ child, items }) => (
              <section key={child.id} aria-label={`${child.name} 알림`} className="flex flex-col gap-1 pb-2">
                <h3 className="flex items-center gap-2 px-2 pb-1 pt-2 text-14 font-semibold">
                  <Avatar name={child.name} size={24} />
                  {child.name}
                  <span className="text-13 font-medium text-danger">{items.length}개</span>
                </h3>
                <ul className="flex flex-col gap-1">
                  {items.map((g) => (
                    <li key={g.id} className="flex gap-3 rounded-lg bg-mark-soft p-3">
                      <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-mark text-mark-ink">
                        <Pill size={18} strokeWidth={2} aria-hidden />
                      </span>
                      <div className="flex min-w-0 flex-1 flex-col gap-2">
                        <button type="button" onClick={() => open(g, close)} className="flex flex-col gap-0.5 text-left">
                          <span className="flex items-center justify-between gap-2">
                            <span className="text-15 font-bold">{g.slot} 약 먹을 시간이에요</span>
                            <span className="shrink-0 text-12 text-muted">{hhmm(g.time)}</span>
                          </span>
                          <span className="text-13 text-muted">
                            {g.doses.filter((d) => !d.given).map((d) => `${d.name} ${d.dose}`).join(', ')}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => markGiven(g)}
                          aria-label={`${child.name} ${g.slot} 약 먹였어요`}
                          className="inline-flex min-h-9 items-center gap-1 self-start rounded-md bg-brand px-3 py-1.5 text-13 font-semibold text-on-brand hover:bg-brand-hover"
                        >
                          <Check size={15} strokeWidth={2.5} aria-hidden />먹였어요
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
            {next && (
              <div className="mt-1 flex items-center gap-3 rounded-lg px-3 py-3 text-14">
                <Clock size={18} strokeWidth={1.75} className="shrink-0 text-faint" aria-hidden />
                <span className="flex-1 text-muted">
                  다음 알림 <span className="font-semibold text-ink">{hhmm(next.time)}</span> · {next.child.name} {next.slot} 약
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </Popover>
  );
}
