import { useId, useRef, useState } from 'react';
import { AlertTriangle, Bell, BellOff, Check, Clock, Moon, Sun, Sunrise, Sunset } from 'lucide-react';
import { Avatar, Switch } from '../ui/misc.jsx';
import { NO_ALARM_SLOTS, dateParts, fromKey, hhmm, todayKey } from '../../state/records.jsx';

const H2 = ({ children }) => <h2 className="text-18 font-bold lg:text-20">{children}</h2>;

export function GuideTitle({ childName, disease, hospital, date, large }) {
  return (
    <div className="flex flex-col gap-1.5">
      <h1 className={`font-bold ${large ? 'text-24 lg:text-32' : 'text-24'}`}>{childName}의 복약 가이드</h1>
      <p className="text-14 text-muted">{disease}, {date} {hospital} 처방</p>
    </div>
  );
}

/** 지금 먹는 처방이면 오늘이 며칠째인지(시작일이 1일째) */
export const courseDay = (active) => (active ? Math.round((fromKey(todayKey()) - fromKey(active.start)) / 86400000) + 1 : 0);

/**
 * 처방 정보 — 아이, 병명, 복용 중·복용 끝, 날짜·병원·약 개수.
 * /guides의 접는 카드 머리와 /guide의 맨 위 카드가 같이 써요. 감싸는 요소(버튼·div)는 쓰는 쪽이 정해요.
 * titleAs: 병명 글자의 태그(가이드 화면에서는 h1)
 */
export function GuideSummary({ guide: g, child, active, ended, titleAs: Title = 'span' }) {
  const p = dateParts(g.date);
  const day = courseDay(active);
  const medCount = g.howTo.length;
  return (
    <>
      <Avatar name={child.name} size={40} />
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Title className="text-17 font-bold lg:text-18">{g.title}</Title>
          {active ? (
            <span className="rounded-pill bg-brand-soft px-2 py-0.5 text-12 font-semibold text-brand">복용 중 · {day}일째</span>
          ) : (
            ended && <span className="rounded-pill bg-sunk px-2 py-0.5 text-12 font-semibold text-muted">복용 끝</span>
          )}
        </span>
        <span className="text-13 text-muted lg:text-14">
          {child.name} · {p.month}월 {p.day}일 · {g.hospital}{medCount ? ` · 약 ${medCount}개` : ''}
        </span>
      </span>
    </>
  );
}

/**
 * 복약 알림 줄 — 켜짐·꺼짐, 설정된 시간, 시간 바꾸기, 켜고 끄기.
 * /guides 카드와 /guide 맨 위 카드가 같이 써요. 끈 뒤에도 정해 둔 시간은 그대로 남아요.
 */
export function AlarmBar({ on, onChange, times, onEditTimes, label }) {
  return (
    <div className="flex items-center gap-2.5 border-t border-line bg-paper/60 py-1.5 pl-4 pr-3 lg:pl-6 lg:pr-5">
      {on ? (
        <Bell size={17} strokeWidth={1.75} className="shrink-0 text-brand" aria-hidden />
      ) : (
        <BellOff size={17} strokeWidth={1.75} className="shrink-0 text-faint" aria-hidden />
      )}
      <span className="flex min-w-0 flex-1 flex-col">
        <span aria-hidden className={`text-14 ${on ? 'font-medium text-ink' : 'text-muted'}`}>
          {on ? '복약 알림 켜짐' : '복약 알림 꺼짐'}
        </span>
        {on && <span className="text-12 tabular-nums text-muted">{times.join(' · ')}</span>}
      </span>
      <button
        type="button"
        onClick={onEditTimes}
        aria-label={`${label} 알림 시간 설정`}
        className="inline-flex min-h-11 shrink-0 items-center gap-1 rounded-md px-2.5 text-13 font-semibold text-brand hover:bg-brand-soft"
      >
        <Clock size={14} strokeWidth={2} aria-hidden />시간
      </button>
      <Switch checked={on} onChange={onChange} aria-label={`${label} 복약 알림`} />
    </div>
  );
}

const SLOT_ICON = { 아침: Sunrise, 점심: Sun, 저녁: Sunset, '자기 전': Moon };
const COLS = { 1: 'grid-cols-1', 2: 'grid-cols-2', 3: 'grid-cols-3', 4: 'grid-cols-4' };

/**
 * 하루 복약 일정 — 먹는 때(아침·점심·저녁·자기 전)를 같은 크기 탭으로 놓고, 고른 때의 약만 아래에 보여요.
 * 탭의 시간은 이 처방에 저장된 알림 시간(timeOf)이라, 알림 시간을 바꾸면 같이 바뀌어요.
 * 알림을 보내지 않는 때(자기 전)는 '알림 없음'으로 보여요. 필요할 때 먹는 약은 아래 별도 카드에 둬요.
 */
export function Schedule({ schedule, asNeeded, timeOf }) {
  const baseId = useId();
  const [picked, setPicked] = useState(0);
  const tabs = useRef([]);
  const index = Math.min(picked, schedule.length - 1);
  const current = schedule[index];
  const move = (e) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
    let next = step === undefined ? null : (index + step + schedule.length) % schedule.length;
    if (e.key === 'Home') next = 0;
    if (e.key === 'End') next = schedule.length - 1;
    if (next === null) return;
    e.preventDefault();
    setPicked(next);
    tabs.current[next]?.focus();
  };

  return (
    <section className="flex flex-col gap-3">
      <H2>하루 복약 일정</H2>
      <div role="tablist" aria-label="먹는 때" onKeyDown={move} className={`grid gap-2 ${COLS[schedule.length] ?? 'grid-cols-4'}`}>
        {schedule.map(({ slot, items }, j) => {
          const on = j === index;
          const Icon = SLOT_ICON[slot] ?? Clock;
          const time = NO_ALARM_SLOTS.includes(slot) ? null : timeOf?.(slot);
          return (
            <button
              key={slot}
              ref={(el) => { tabs.current[j] = el; }}
              type="button"
              role="tab"
              id={`${baseId}-tab-${j}`}
              aria-selected={on}
              aria-controls={`${baseId}-panel`}
              tabIndex={on ? 0 : -1}
              onClick={() => setPicked(j)}
              className={`flex min-h-[104px] min-w-0 flex-col items-center justify-center gap-1 rounded-xl border px-1 py-3 text-center transition-colors ${on ? 'border-brand bg-brand text-on-brand' : 'border-line bg-surface text-ink hover:bg-paper'}`}
            >
              <Icon size={20} strokeWidth={1.75} className={on ? 'text-on-brand' : 'text-brand'} aria-hidden />
              <span className="text-15 font-semibold">{slot}</span>
              <span className={`text-13 tabular-nums ${on ? 'text-on-brand/85' : 'text-muted'}`}>{time ? hhmm(time) : '알림 없음'}</span>
              <span className={`text-12 ${on ? 'text-on-brand/85' : 'text-muted'}`}>약 {items.length}개</span>
            </button>
          );
        })}
      </div>
      {current && (
        <ul
          id={`${baseId}-panel`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-${index}`}
          className="flex flex-col divide-y divide-line rounded-xl border border-line bg-surface"
        >
          {current.items.map(([name, dose]) => (
            <li key={name} className="flex min-h-[52px] items-center justify-between gap-4 px-4 py-3">
              <span className="min-w-0 flex-1 break-words text-15 font-medium">{name}</span>
              <span className="shrink-0 text-15 tabular-nums text-muted">{dose}</span>
            </li>
          ))}
        </ul>
      )}
      {asNeeded && (
        <p className="flex items-start gap-2.5 rounded-lg bg-sunk/60 px-4 py-3 text-14">
          <Clock size={20} strokeWidth={1.75} className="shrink-0 text-muted" aria-hidden />
          {asNeeded}
        </p>
      )}
    </section>
  );
}

/**
 * 약별 복용법 표에 넣을 값 — 가이드에 처방전 값(dose·perDay·days·timing)이 있으면 그대로 쓰고,
 * 없는 예전 가이드는 복약 일정(약 이름이 같거나 '이름 ' 으로 시작하는 한 가지)과 건강기록의 기간에서만 가져와요.
 * 어디에도 없으면 비워 둬요(지어내지 않아요). 원래 약 이름·처방 데이터는 바꾸지 않아요.
 */
function medFacts(m, schedule, asNeededText, visitMeds) {
  const slots = [];
  let dose = '';
  let days = '';
  for (const { slot, items } of schedule) {
    const hits = items.filter(([name]) => name === m.name || m.name.startsWith(`${name} `));
    if (hits.length !== 1) continue;
    slots.push(slot);
    dose ||= hits[0][1] ?? '';
    // 기간은 화면에서 만든 일정이면 숫자(5), 서버 가이드 일정이면 이미 '5일'이에요. 숫자일 때만 '일'을 붙여요.
    const itemDays = hits[0][2];
    if (!days && itemDays) days = /^\d+$/.test(String(itemDays)) ? `${itemDays}일` : String(itemDays);
  }
  const visitDays = visitMeds?.find((v) => v.name === m.name || m.name.startsWith(`${v.name} `))?.days ?? '';
  const structured = 'dose' in m;
  const asNeeded = structured ? !!m.asNeeded : !slots.length && !!asNeededText?.includes(m.name.split(' ')[0]);
  return {
    dose: structured ? m.dose : dose,
    perDay: structured ? m.perDay : slots.length ? `${slots.length}번` : '',
    days: structured ? m.days : days || visitDays,
    // 먹는 때 지시: 처방전 값이 있으면 그 값, 없으면 일정에 들어간 때(아침·점심…)
    timing: structured ? m.timing : slots.join('·'),
    asNeeded,
  };
}

/** 약별 복용법 — 약 이름, 1회 양·하루·기간을 같은 칸에 맞추고, 먹는 때·필요할 때는 따로 표시. 아래에 가이드 설명과 주의사항 */
export function HowTo({ items, schedule = [], asNeeded, visitMeds }) {
  return (
    <section className="flex flex-col gap-3">
      <H2>약별 복용법</H2>
      <ul className="flex flex-col divide-y divide-line rounded-xl border border-line bg-surface">
        {items.map((m) => {
          const f = medFacts(m, schedule, asNeeded, visitMeds);
          const cells = [['1회 복용량', f.dose], ['하루', f.perDay], ['기간', f.days]];
          return (
            <li key={m.name}>
              <article className="flex flex-col gap-3 px-4 py-4 lg:px-5">
                <div className="flex flex-col gap-2">
                  <h3 className="break-words text-16 font-bold">{m.name}</h3>
                  {(f.asNeeded || f.timing) && (
                    <p className="flex flex-wrap gap-1.5">
                      {f.asNeeded && (
                        <span className="rounded-pill bg-mark-soft px-2.5 py-0.5 text-12 font-semibold text-terra-ink">필요할 때</span>
                      )}
                      {f.timing && (
                        <span className="rounded-pill bg-brand-soft px-2.5 py-0.5 text-12 font-semibold text-brand">
                          <span className="sr-only">먹는 때: </span>{f.timing}
                        </span>
                      )}
                    </p>
                  )}
                </div>
                <dl className="grid grid-cols-3 divide-x divide-line rounded-lg bg-paper py-2.5">
                  {cells.map(([k, v]) => (
                    <div key={k} className="flex min-w-0 flex-col gap-0.5 px-3">
                      <dt className="text-12 text-muted">{k}</dt>
                      <dd className="break-words text-15 font-semibold">{v || <><span className="text-muted" aria-hidden>—</span><span className="sr-only">정보 없음</span></>}</dd>
                    </div>
                  ))}
                </dl>
                <p className="text-15">{m.how}</p>
                {m.note && <p className="text-14 text-muted">{m.note}</p>}
              </article>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function LifeTips({ items }) {
  return (
    <section className="flex flex-col gap-2.5">
      <H2>생활 습관</H2>
      <ul className="flex flex-col gap-2.5">
        {items.map((l) => (
          <li key={l} className="flex items-start gap-2.5 text-15">
            <Check size={20} strokeWidth={2.25} className="mt-0.5 shrink-0 text-brand" aria-hidden />
            {l}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** 위험 신호 — 패딩 16, 모서리 14, 연빨강 바탕 */
export function DangerSignals({ items }) {
  const titleId = useId();
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-danger/25 bg-danger-soft p-4 lg:p-5" aria-labelledby={titleId}>
      <h2 id={titleId} className="flex items-center gap-2 text-16 font-bold text-danger">
        <AlertTriangle size={22} strokeWidth={2} className="shrink-0" aria-hidden />
        이럴 땐 바로 병원에 가세요
      </h2>
      <ul className="flex flex-col gap-2.5">
        {items.map((l) => (
          <li key={l} className="flex items-start gap-2.5 pl-1 text-15">
            <span aria-hidden className="mt-[9px] size-[5px] shrink-0 rounded-full bg-danger" />
            {l}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Disclaimer() {
  return (
    <p className="border-t border-line pt-4 text-13 text-muted">
      이 가이드는 처방 내용을 쉽게 풀어 쓴 참고 자료이고, 진단이나 처방을 대신하지 않아요. 양을 바꾸거나 약을 끊기 전에는 꼭 약사나 의사에게 물어봐 주세요.
    </p>
  );
}
