import { AlertTriangle, Bell, Check, Clock } from 'lucide-react';
import { Tag } from '../ui/misc.jsx';

const H2 = ({ children }) => <h2 className="text-18 font-bold">{children}</h2>;

export function GuideTitle({ childName, disease, hospital, date, large }) {
  return (
    <div className="flex flex-col gap-1.5">
      <h1 className={`font-bold ${large ? 'text-24 lg:text-32' : 'text-24'}`}>{childName}의 복약 가이드</h1>
      <p className="text-14 text-muted">{disease}, {date} {hospital} 처방</p>
    </div>
  );
}

/** 하루 먹는 때 — 4칸 (패딩 12/10/14, 모서리 12, 간격 6) + 필요할 때 안내 */
export function Schedule({ schedule, asNeeded }) {
  return (
    <section className="flex flex-col gap-3">
      <H2>하루 먹는 때</H2>
      <ol className="grid grid-cols-4 gap-1.5">
        {schedule.map(({ slot, items }) => (
          <li key={slot} className="flex flex-col gap-2.5 rounded-lg border border-line bg-surface px-2 pb-3.5 pt-3 sm:px-2.5">
            <span className="text-14 font-semibold text-brand">{slot}</span>
            {items.map(([name, dose]) => (
              <span key={name} className="flex flex-col">
                <span className="text-13 font-medium">{name}</span>
                <span className="text-13 text-muted">{dose}</span>
              </span>
            ))}
          </li>
        ))}
      </ol>
      <p className="flex items-start gap-2.5 rounded-lg bg-sunk px-3.5 py-3 text-14">
        <Clock size={20} strokeWidth={1.75} className="shrink-0" aria-hidden />
        {asNeeded}
      </p>
    </section>
  );
}

/** 약별 복용법 — 카드 대신 구분선으로 나눈 목록 */
export function HowTo({ items }) {
  return (
    <section className="flex flex-col gap-1">
      <H2>약별 복용법</H2>
      {items.map((m, j) => (
        <article key={m.name} className={`flex flex-col gap-1 py-3.5 ${j ? 'border-t border-line' : ''}`}>
          <h3 className="text-16 font-semibold">{m.name}</h3>
          <p className="text-15">{m.how}</p>
          <p className="text-14 text-muted">{m.note}</p>
        </article>
      ))}
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
  return (
    <section className="flex flex-col gap-2.5 rounded-xl bg-danger-soft p-4" aria-labelledby="danger-title">
      <h2 id="danger-title" className="flex items-center gap-2 text-16 font-bold text-danger">
        <AlertTriangle size={22} strokeWidth={2} aria-hidden />
        이럴 땐 바로 병원에 가세요
      </h2>
      <ul className="flex flex-col gap-2.5">
        {items.map((l) => (
          <li key={l} className="flex items-center gap-2 pl-0.5 text-15">
            <span aria-hidden className="size-[5px] shrink-0 rounded-full bg-danger" />
            {l}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** 복약 알림 — 1차 MVP에서는 UI만 두고 '준비 중' */
export function AlarmCard() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-surface p-4">
      <Bell size={22} strokeWidth={1.75} className="shrink-0 text-muted" aria-hidden />
      <div className="flex flex-1 flex-col gap-0.5">
        <p className="text-15 font-semibold">복약 알림</p>
        <p className="text-13 text-muted">먹일 시간에 알려 주는 기능을 준비하고 있어요.</p>
      </div>
      <Tag tone="faint">준비 중</Tag>
    </div>
  );
}

export function Disclaimer() {
  return (
    <p className="border-t border-line pt-4 text-13 text-muted">
      이 가이드는 처방 내용을 쉽게 풀어 쓴 참고 자료이고, 진단이나 처방을 대신하지 않아요. 양을 바꾸거나 약을 끊기 전에는 꼭 약사나 의사에게 물어봐 주세요.
    </p>
  );
}
