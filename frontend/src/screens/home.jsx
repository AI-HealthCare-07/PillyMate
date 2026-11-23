import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Check, ChevronRight, Clock, MessageCircle, ScanLine } from 'lucide-react';
import { Avatar, Panel, Tag } from '../components/ui/misc.jsx';
import { AppShell, Body } from '../components/ui/layout.jsx';
import { guide } from '../data/sample.js';
import { dateParts, fromKey, todayKey, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';

const H2 = ({ children, action }) => (
  <div className="flex items-center justify-between">
    <h2 className="text-18 font-bold">{children}</h2>
    {action}
  </div>
);

const MoreLink = ({ onClick, children }) => (
  <button type="button" onClick={onClick} className="flex items-center gap-0.5 rounded-md py-1 pl-2 text-14 font-semibold text-muted hover:text-ink">
    {children}<ChevronRight size={16} aria-hidden />
  </button>
);

/**
 * 홈 — 지금 고른 아이 기준으로 오늘 먹을 약, 확인할 처방, 최근 기록을 한눈에 보여요.
 * 먹였어요 체크는 기록 탭의 복약 달력과 같은 데이터를 써요.
 */
export function HomeScreen({ go, onTab }) {
  const { childId, child } = useSelectedChild();
  const { activeCourse, dosesOn, toggleDose, visitsOf } = useRecords();
  const navigate = useNavigate();
  const openHealthLog = () => navigate('/history?tab=health');
  const today = todayKey();
  const care = childId ? activeCourse(childId, today) : null;
  const rows = childId
    ? visitsOf(childId).map((v) => {
        const p = dateParts(v.date);
        return { ...v, month: `${p.month}월`, day: p.day, medCount: v.meds.length };
      })
    : [];
  const pending = rows.filter((r) => r.status);
  const doses = childId ? dosesOn(childId, today) : [];
  const doneCount = doses.filter((d) => d.given).length;
  const careDay = care ? Math.round((fromKey(today) - fromKey(care.start)) / 86400000) + 1 : 0;

  if (!child) {
    return (
      <AppShell tab="home" onTab={onTab}>
        <Body className="items-center justify-center gap-4 text-center">
          <p className="text-17 font-semibold">먼저 아이를 등록해 주세요</p>
          <button type="button" onClick={() => go('child-add')} className="rounded-lg bg-brand px-5 py-3.5 text-16 font-semibold text-on-brand">아이 추가하기</button>
        </Body>
      </AppShell>
    );
  }

  return (
    <AppShell tab="home" onTab={onTab}>
      <Body className="gap-7 pt-5 lg:pt-8">
        {/* 지금 보는 아이 */}
        <section className="flex flex-col gap-4">
          <h1 className="text-24 font-bold">{child.name}의 하루</h1>
          <Panel className="flex items-center gap-3.5 py-3.5 pl-4 pr-2">
            <Avatar name={child.name} size={44} />
            <div className="flex flex-1 flex-col gap-0.5">
              <p className="text-14 text-muted">{child.age}, {child.weight}</p>
              {child.allergy ? (
                <p className="flex items-center gap-1.5 text-14 font-medium text-danger">
                  <AlertTriangle size={15} strokeWidth={2} aria-hidden />{child.allergy}
                </p>
              ) : (
                <p className="text-14 text-muted">알레르기 없음</p>
              )}
            </div>
            <button type="button" onClick={() => go('children')} className="rounded-md px-2 py-1.5 text-14 font-semibold text-brand hover:bg-paper">
              아이 바꾸기
            </button>
          </Panel>
        </section>

        {/* 확인 전 처방 */}
        {pending.map((r) => (
          <button
            key={r.id}
            type="button"
            onClick={() => go('confirm')}
            className="flex items-center gap-3 rounded-xl border border-brand/30 bg-brand-soft px-4 py-3.5 text-left"
          >
            <span className="flex flex-1 flex-col gap-0.5">
              <span className="text-15 font-semibold text-brand">확인하지 않은 처방이 있어요</span>
              <span className="text-14 text-ink">{r.month} {r.day}일 {r.title}, 약 {r.medCount}개. 약 내용을 확인하면 가이드를 만들어요.</span>
            </span>
            <ChevronRight size={20} className="text-brand" aria-hidden />
          </button>
        ))}

        {/* 오늘 먹을 약 */}
        <section className="flex flex-col gap-3">
          <H2 action={care && <MoreLink onClick={() => go('guide')}>가이드 보기</MoreLink>}>오늘 먹을 약</H2>
          {care ? (
            <>
              <div className="flex items-center justify-between text-14">
                <span className="text-muted">{care.title}, {care.hospital} · {care.days}일 중 {careDay}일째</span>
                <span className="shrink-0 font-semibold text-brand">{doneCount}/{doses.length}</span>
              </div>
              <Panel as="ul" aria-label="오늘 먹을 약">
                {doses.map((d, j) => {
                  const on = d.given;
                  return (
                    <li key={d.key} className={j ? 'border-t border-line' : ''}>
                      <button
                        type="button"
                        aria-pressed={on}
                        onClick={() => toggleDose(d)}
                        className="flex w-full items-center gap-3.5 px-4 py-3 text-left hover:bg-paper"
                      >
                        <span className="w-14 shrink-0 text-14 font-semibold text-brand">{d.slot}</span>
                        <span className={`flex flex-1 flex-col ${on ? 'text-faint line-through' : ''}`}>
                          <span className="text-15 font-medium">{d.name}</span>
                          <span className="text-13 text-muted">{d.dose}</span>
                        </span>
                        <span
                          className={`flex size-7 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${on ? 'border-brand bg-brand text-on-brand' : 'border-line text-transparent'}`}
                          aria-hidden
                        >
                          <Check size={16} strokeWidth={3} />
                        </span>
                        <span className="sr-only">{on ? '먹였어요' : '아직 안 먹였어요'}</span>
                      </button>
                    </li>
                  );
                })}
              </Panel>
              {care.schedule === guide.schedule && (
                <p className="flex items-start gap-2.5 rounded-lg bg-sunk px-3.5 py-3 text-14">
                  <Clock size={20} strokeWidth={1.75} className="shrink-0" aria-hidden />
                  {guide.asNeeded}
                </p>
              )}
            </>
          ) : (
            <Panel className="px-4 py-6 text-center text-15 text-muted">
              지금 먹고 있는 약이 없어요.
            </Panel>
          )}
        </section>

        {/* 바로가기 */}
        <section className="grid grid-cols-2 gap-3">
          <button type="button" onClick={() => go('upload')} className="flex flex-col items-start gap-3 rounded-xl bg-brand p-4 text-left text-on-brand">
            <ScanLine size={26} strokeWidth={1.75} aria-hidden />
            <span className="flex flex-col gap-0.5">
              <span className="text-16 font-semibold">처방 올리기</span>
              <span className="text-13 opacity-80">처방전 사진으로 가이드 만들기</span>
            </span>
          </button>
          <button type="button" onClick={() => go('chat')} className="flex flex-col items-start gap-3 rounded-xl border border-line bg-surface p-4 text-left hover:bg-paper">
            <MessageCircle size={26} strokeWidth={1.75} className="text-brand" aria-hidden />
            <span className="flex flex-col gap-0.5">
              <span className="text-16 font-semibold">챗봇에 묻기</span>
              <span className="text-13 text-muted">약 먹이다 궁금한 것</span>
            </span>
          </button>
        </section>

        {/* 최근 기록 */}
        <section className="flex flex-col gap-3">
          <H2 action={<MoreLink onClick={openHealthLog}>전체 보기</MoreLink>}>최근 병원 기록</H2>
          {rows.length ? (
            <Panel as="ul">
              {rows.slice(0, 3).map((r, j) => (
                <li key={r.id} className={j ? 'border-t border-line' : ''}>
                  <button
                    type="button"
                    onClick={() => (r.source === 'ocr' ? go(r.status ? 'confirm' : 'guide') : openHealthLog())}
                    className="flex w-full items-center gap-3.5 py-3 pl-4 pr-3 text-left hover:bg-paper"
                  >
                    <span className="w-[72px] shrink-0 whitespace-nowrap text-14 text-muted">{r.month} {r.day}일</span>
                    <span className="flex flex-1 flex-col">
                      <span className="text-15 font-semibold">{r.title}</span>
                      <span className="text-13 text-muted">{r.hospital}{r.medCount ? ` · 약 ${r.medCount}개` : ''}</span>
                    </span>
                    {r.status && <Tag>{r.status}</Tag>}
                    <ChevronRight size={18} className="text-muted" aria-hidden />
                  </button>
                </li>
              ))}
            </Panel>
          ) : (
            <Panel className="px-4 py-6 text-center text-15 text-muted">아직 올린 처방이 없어요.</Panel>
          )}
        </section>
      </Body>
    </AppShell>
  );
}
