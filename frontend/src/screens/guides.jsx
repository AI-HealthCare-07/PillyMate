import { useId, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Bell, BellOff, BookOpen, ChevronDown, Clock } from 'lucide-react';
import { Avatar, FilterChip, Switch } from '../components/ui/misc.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { AlarmTimeModal } from '../components/rx/AlarmTimeModal.jsx';
import { DangerSignals, Disclaimer, HowTo, LifeTips, Schedule } from '../components/rx/guide.jsx';
import { alarmSlots, dateParts, fromKey, hhmm, todayKey, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';

/**
 * 가이드 탭 — 저장된 복약 가이드를 접힌 카드로 쭉 늘어놓고, 누르면 카드가 펴져요.
 * 아이 모두의 가이드를 보여 주고, 위쪽 칩으로 아이별로 걸러 볼 수 있어요.
 */
export function GuidesScreen({ go, onTab }) {
  const { childList } = useSelectedChild();
  const { guidesOf, activeCourse, isAlarmOn, setAlarm, alarmTimeOf } = useRecords();
  const [editing, setEditing] = useState(null); // 알림 시간을 바꾸는 가이드
  // 보던 아이 칩은 주소(?child=c1)에 남겨요. 홈의 '가이드' 바로가기는 ?child=아이&open=가이드로 들어와서
  // 그 아이 가이드만 보여 주고, 지금 먹는 약의 가이드 카드를 펴 둬요.
  const [params, setParams] = useSearchParams();
  const wanted = params.get('child');
  const filter = childList.some((c) => c.id === wanted) ? wanted : 'all';
  const setFilter = (next) => setParams(next === 'all' ? {} : { child: next }, { replace: true });
  const [openIds, setOpenIds] = useState(() => new Set(params.get('open') ? [params.get('open')] : []));

  const childById = new Map(childList.map((c) => [c.id, c]));
  const list = guidesOf(filter === 'all' ? undefined : filter).filter((g) => childById.has(g.childId));
  const toggle = (id) =>
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <AppShell tab="guides" onTab={onTab} header={<Header title="복약 가이드" />}>
      <Body className="gap-4 pt-1">
        {childList.length > 1 && (
          <div className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1 lg:mx-0 lg:px-0" role="group" aria-label="아이별로 보기">
            <FilterChip selected={filter === 'all'} onClick={() => setFilter('all')}>전체</FilterChip>
            {childList.map((c) => (
              <FilterChip key={c.id} selected={filter === c.id} onClick={() => setFilter(c.id)}>{c.name}</FilterChip>
            ))}
          </div>
        )}

        {list.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-line bg-surface px-5 py-10 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-brand-soft text-brand">
              <BookOpen size={24} strokeWidth={1.75} aria-hidden />
            </span>
            <p className="text-17 font-semibold">저장된 가이드가 없어요</p>
            <p className="text-14 text-muted">처방전을 올리고 약 내용을 확인하면 가이드가 여기에 모여요.</p>
            <button type="button" onClick={() => go('upload')} className="mt-1 rounded-lg bg-brand px-5 py-3 text-15 font-semibold text-on-brand">
              처방 올리기
            </button>
          </div>
        ) : (
          <ul className="flex flex-col gap-3">
            {list.map((g) => {
              const course = activeCourse(g.childId);
              const active = course?.visitId === g.visitId ? course : null;
              return (
                <li key={g.id}>
                  <GuideCard
                    guide={g}
                    child={childById.get(g.childId)}
                    active={active}
                    open={openIds.has(g.id)}
                    onToggle={() => toggle(g.id)}
                    alarmOn={isAlarmOn(g.visitId)}
                    onAlarmChange={(on) => setAlarm(g.visitId, on)}
                    alarmTimes={alarmSlots(g.schedule).map((slot) => hhmm(alarmTimeOf(g.visitId, slot)))}
                    onEditTimes={() => setEditing(g)}
                  />
                </li>
              );
            })}
          </ul>
        )}

        {list.length > 0 && <Disclaimer />}
      </Body>
      <AlarmTimeModal
        open={!!editing}
        onClose={() => setEditing(null)}
        visitId={editing?.visitId}
        slots={editing ? alarmSlots(editing.schedule) : []}
        title={editing ? `${childById.get(editing.childId)?.name} · ${editing.title}` : ''}
      />
    </AppShell>
  );
}

/** 접었다 펴는 가이드 카드. 접힌 상태에선 병명·날짜·병원만, 펴면 가이드 전체를 보여 줘요. */
function GuideCard({ guide: g, child, active, open, onToggle, alarmOn, onAlarmChange, alarmTimes, onEditTimes }) {
  const id = useId();
  const p = dateParts(g.date);
  const day = active ? Math.round((fromKey(todayKey()) - fromKey(active.start)) / 86400000) + 1 : 0;
  const ended = !active && g.date < todayKey();
  const medCount = g.howTo.length;

  return (
    <article className={`overflow-hidden rounded-xl border bg-surface transition-shadow ${open ? 'border-brand/40 shadow-card' : 'border-line'}`}>
      <h2>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={`${id}-body`}
          onClick={onToggle}
          className="flex w-full items-center gap-3.5 px-4 py-4 text-left hover:bg-paper"
        >
          <Avatar name={child.name} size={40} />
          <span className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="text-17 font-bold">{g.title}</span>
              {active ? (
                <span className="rounded-pill bg-brand px-2 py-0.5 text-12 font-semibold text-on-brand">복용 중 · {day}일째</span>
              ) : (
                ended && <span className="rounded-pill bg-sunk px-2 py-0.5 text-12 font-semibold text-muted">복용 끝</span>
              )}
            </span>
            <span className="text-13 text-muted">
              {child.name} · {p.month}월 {p.day}일 · {g.hospital}{medCount ? ` · 약 ${medCount}개` : ''}
            </span>
          </span>
          <ChevronDown
            size={22}
            className={`shrink-0 text-muted transition-transform duration-200 ${open ? 'rotate-180 text-brand' : ''}`}
            aria-hidden
          />
        </button>
      </h2>

      {/* 복약 알림 — 접힌 채로도 바로 켜고 끌 수 있어요. 아직 먹는 중인 처방에만 보여요(끝난 처방은 알릴 약이 없어요). */}
      {alarmSlots(g.schedule).length > 0 && !ended && (
        <div className="flex items-center gap-2.5 border-t border-line px-4 py-2.5">
          {alarmOn ? (
            <Bell size={17} strokeWidth={1.75} className="shrink-0 text-brand" aria-hidden />
          ) : (
            <BellOff size={17} strokeWidth={1.75} className="shrink-0 text-faint" aria-hidden />
          )}
          <span className="flex min-w-0 flex-1 flex-col">
            <span aria-hidden className={`text-14 ${alarmOn ? 'font-medium text-ink' : 'text-muted'}`}>
              {alarmOn ? '복약 알림 켜짐' : '복약 알림 꺼짐'}
            </span>
            {alarmOn && <span className="text-12 tabular-nums text-muted">{alarmTimes.join(' · ')}</span>}
          </span>
          <button
            type="button"
            onClick={onEditTimes}
            aria-label={`${child.name} ${g.title} 알림 시간 설정`}
            className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1.5 text-13 font-semibold text-brand hover:bg-brand-soft"
          >
            <Clock size={14} strokeWidth={2} aria-hidden />시간
          </button>
          <Switch checked={alarmOn} onChange={onAlarmChange} aria-label={`${child.name} ${g.title} 복약 알림`} />
        </div>
      )}

      {/* grid-rows 0fr ↔ 1fr로 높이를 부드럽게 펼쳐요 */}
      <div
        id={`${id}-body`}
        role="region"
        aria-label={`${g.title} 가이드`}
        inert={open ? undefined : ''}
        className={`grid transition-[grid-template-rows] duration-300 ease-out ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="flex flex-col gap-7 border-t border-line px-4 pb-5 pt-5">
            {g.schedule.length > 0 && <Schedule schedule={g.schedule} asNeeded={g.asNeeded} />}
            {g.danger.length > 0 && <DangerSignals items={g.danger} />}
            {g.howTo.length > 0 && <HowTo items={g.howTo} />}
            {g.life.length > 0 && <LifeTips items={g.life} />}
          </div>
        </div>
      </div>
    </article>
  );
}
