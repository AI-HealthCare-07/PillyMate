import { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { FilterChip, Panel, Tag } from '../components/ui/misc.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { history } from '../data/sample.js';

/** S-07 기록 — 달별로 묶은 목록, 날짜 칸 40px */
export function HistoryScreen({ go, onTab }) {
  const [filter, setFilter] = useState('전체');
  const rows = (list) => (filter === '전체' ? list : list.filter((r) => r.sub.startsWith(filter)));
  const groups = history.map((g) => ({ ...g, rows: rows(g.rows) })).filter((g) => g.rows.length);
  return (
    <AppShell tab="history" onTab={onTab} header={<Header title="기록" />}>
      <Body className="gap-4 pt-1">
        <div className="flex gap-2" role="group" aria-label="아이로 거르기">
          {['전체', '지우', '서준'].map((f) => (
            <FilterChip key={f} selected={filter === f} onClick={() => setFilter(f)}>{f}</FilterChip>
          ))}
        </div>
        {groups.length === 0 && (
          <p className="py-10 text-center text-15 text-muted">아직 올린 처방이 없어요. 처방 올리기에서 첫 처방전을 찍어 보세요.</p>
        )}
        {groups.map((g) => (
          <section key={g.month} className="flex flex-col gap-2">
            <h2 className="text-14 font-semibold text-muted">{g.month}</h2>
            <Panel as="ul">
              {g.rows.map((r, j) => (
                <li key={r.id} className={j ? 'border-t border-line' : ''}>
                  <button
                    type="button"
                    onClick={() => go(r.status ? 'confirm' : 'guide')}
                    className="flex w-full items-center gap-3.5 py-3 pl-3.5 pr-3 text-left hover:bg-paper"
                  >
                    <span className="flex w-10 shrink-0 flex-col items-center">
                      <span className="text-20 font-bold">{r.day}</span>
                      <span className="text-12 text-muted">{r.weekday}</span>
                    </span>
                    <span className="flex flex-1 flex-col gap-0.5">
                      <span className="text-16 font-semibold">{r.title}</span>
                      <span className="text-13 text-muted">{r.sub}</span>
                    </span>
                    {r.status && <Tag>{r.status}</Tag>}
                    <ChevronRight size={20} className="text-muted" aria-hidden />
                  </button>
                </li>
              ))}
            </Panel>
          </section>
        ))}
      </Body>
    </AppShell>
  );
}
