import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Check, ChevronRight, Clock, Minus, ScanLine } from 'lucide-react';
import { Button } from '../components/ui/Button.jsx';
import { Panel, Tag } from '../components/ui/misc.jsx';
import { AppShell, Body } from '../components/ui/layout.jsx';
import { dateParts, fromKey, groupBySlot, todayKey, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';
import { draftFromVisit } from './fe2Draft.js';
import { EFFICACY_PENDING_LABEL, efficacyOf } from '../data/efficacy.js';
import { useAddChildConsent } from '../components/child/AddChildConsent.jsx';

const H2 = ({ children, action }) => (
  <div className="flex items-center justify-between">
    <h2 className="text-16 font-bold text-muted">{children}</h2>
    {action}
  </div>
);

const MoreLink = ({ onClick, children }) => (
  <button type="button" onClick={onClick} className="flex items-center gap-0.5 rounded-md py-1 pl-2 text-14 font-semibold text-muted hover:text-ink">
    {children}<ChevronRight size={16} aria-hidden />
  </button>
);

/**
 * 약 이름 아래 약효 분류 배지. 확인된 분류가 없으면 짐작하지 않고 '약효 정보 확인 중'으로 보여 줘요.
 * inline-flex라서 먹인 약의 취소선이 배지까지 내려오지 않아요.
 */
const EfficacyBadge = ({ med, dim }) => {
  const info = efficacyOf(med);
  const tone = !info
    ? 'border-dashed border-line text-faint'
    : dim
      ? 'border-line text-faint'
      : 'border-brand/30 text-brand';
  return (
    <span className={`inline-flex max-w-full items-center rounded-pill border bg-surface px-2 py-px text-12 font-semibold ${tone}`}>
      <span className="sr-only">약효 분류: </span>
      <span className="break-keep">{info?.label ?? EFFICACY_PENDING_LABEL}</span>
    </span>
  );
};

/**
 * 홈 —지금 고른 아이 기준으로 오늘 먹을 약, 확인할 처방, 최근 기록을 한눈에 보여요.
 * 먹였어요 체크는 기록 탭의 복약 달력과 같은 데이터를 써요.
 */
export function HomeScreen({ go, onTab }) {
  const { childId, child } = useSelectedChild();
  const { activeCourse, dosesOn, guidesOf, toggleSlot, visitsOf } = useRecords();
  const navigate = useNavigate();
  const addFlow = useAddChildConsent(go);
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
  // 가이드 바로가기 — 가이드 탭을 지금 보는 아이로 걸러 열고, 지금 먹는 약의 가이드 카드를 펴 둬요.
  const careGuide = care ? guidesOf(childId).find((g) => g.visitId === care.visitId) : null;
  const careGuideId = careGuide?.id ?? null;
  const openGuides = () =>
    navigate(`/guides?${new URLSearchParams({ child: childId, ...(careGuideId ? { open: careGuideId } : {}) })}`);
  const careDay = care ? Math.round((fromKey(today) - fromKey(care.start)) / 86400000) + 1 : 0;

  if (!child) {
    return (
      <AppShell tab="home" onTab={onTab}>
        <Body className="items-center justify-center gap-4 text-center">
          <p className="text-17 font-semibold">먼저 아이를 등록해 주세요</p>
          <button type="button" onClick={addFlow.start} className="rounded-lg bg-brand px-5 py-3.5 text-16 font-semibold text-on-brand">아이 추가하기</button>
          {addFlow.modal}
        </Body>
      </AppShell>
    );
  }

  // 먹는 때(아침/점심/저녁/자기 전)별로 묶어서, 그때 먹을 약을 한 번에 체크해요.
  const slots = groupBySlot(doses);
  const slotsDone = slots.filter((g) => g.done).length;
  const nextSlot = slots.find((g) => !g.done)?.slot;
  const allDone = slots.length > 0 && slotsDone === slots.length;

  return (
    <AppShell tab="home" onTab={onTab}>
      <Body className="gap-6 pt-5 lg:pt-8">
        {/* 지금 보는 아이 — 아이 전환은 상단 바 칩에서 해요 */}
        <section className="flex flex-col gap-1.5">
          <h1 className="text-24 font-bold">{child.name}의 하루</h1>
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-14 text-muted">
            <span>{[child.age, child.weight, child.allergy ? '' : '알레르기 없음'].filter(Boolean).join(' · ')}</span>
            {child.allergy && (
              <span className="inline-flex items-center gap-1 rounded-pill bg-danger-soft px-2 py-0.5 text-13 font-semibold text-danger">
                <AlertTriangle size={13} strokeWidth={2.25} aria-hidden />{child.allergy}
              </span>
            )}
          </p>
        </section>

        {/* 확인 전 처방 — 가장 최근 것만 카드로 보여 주고, 나머지는 건강기록에서 확인해요. */}
        {pending.slice(0, 1).map((r) => (
          <button
            key={r.id}
            type="button"
            onClick={() => {
              draftFromVisit(r);
              go('confirm');
            }}
            className="flex items-center gap-3 rounded-xl border border-mark bg-mark-soft px-4 py-3.5 text-left"
          >
            <span className="flex flex-1 flex-col gap-0.5">
              <span className="text-15 font-semibold text-mark-ink">확인하지 않은 처방이 있어요</span>
              <span className="text-14 text-ink">{r.month} {r.day}일 {r.title}, 약 {r.medCount}개. 약 내용을 확인하면 가이드를 만들어요.</span>
            </span>
            <ChevronRight size={20} className="text-mark-ink" aria-hidden />
          </button>
        ))}
        {pending.length > 1 && (
          <button type="button" onClick={openHealthLog} className="-mt-2 flex items-center gap-0.5 self-end text-14 font-semibold text-mark-ink">
            확인하지 않은 처방 {pending.length - 1}개 더 보기<ChevronRight size={16} aria-hidden />
          </button>
        )}

        {/* 오늘 먹을 약 — 화면의 핵심 카드 */}
        {care ? (
          <Panel as="section" tone="raised" aria-labelledby="today-meds">
            <div className="flex flex-col gap-4 px-5 pb-4 pt-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-col gap-0.5">
                  <h2 id="today-meds" className="text-18 font-bold">오늘 먹을 약</h2>
                  <p className="text-13 text-muted">{care.title} · {care.hospital} · {care.days}일 중 {careDay}일째</p>
                </div>
                <MoreLink onClick={openGuides}>가이드</MoreLink>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-baseline justify-between">
                  <p className="text-15 font-semibold text-brand">
                    {allDone ? '오늘 약을 모두 먹였어요' : `${slots.length - slotsDone}번 남았어요`}
                  </p>
                  <p className="text-14 text-muted"><span className="text-17 font-bold text-ink">{slotsDone}</span> / {slots.length}</p>
                </div>
                <div
                  role="progressbar"
                  aria-label="오늘 복약 진행"
                  aria-valuemin={0}
                  aria-valuemax={slots.length}
                  aria-valuenow={slotsDone}
                  className="h-2 overflow-hidden rounded-pill bg-sunk"
                >
                  <div className="h-full rounded-pill bg-brand transition-[width] duration-300" style={{ width: `${slots.length ? (slotsDone / slots.length) * 100 : 0}%` }} />
                </div>
              </div>
            </div>
            <ul aria-label="오늘 먹을 약 목록" className="flex flex-col gap-1.5 px-3 pb-3">
              {slots.map((g) => {
                const on = g.done;
                const partial = !on && g.given > 0;
                const next = g.slot === nextSlot;
                return (
                  <li key={g.slot}>
                    <button
                      type="button"
                      aria-pressed={on}
                      aria-label={`${g.slot} 약 ${g.doses.length}개${on ? ', 먹였어요' : partial ? `, ${g.doses.length}개 중 ${g.given}개 먹였어요` : ', 아직 안 먹였어요'}`}
                      onClick={() => toggleSlot(g)}
                      className={`flex w-full items-center gap-3.5 rounded-lg px-3 py-3 text-left transition-colors ${next ? 'bg-brand-soft ring-1 ring-inset ring-brand/25' : 'hover:bg-paper'}`}
                    >
                      <span className={`flex w-14 shrink-0 flex-col self-start pt-0.5 text-14 font-semibold ${on ? 'text-faint' : 'text-brand'}`}>
                        {g.slot}
                        {next && <span className="text-12 font-medium text-brand/80">다음 복용</span>}
                      </span>
                      <ul className={`flex flex-1 flex-col gap-1.5 ${on ? 'text-faint line-through' : ''}`}>
                        {g.doses.map((d) => (
                          <li key={d.key} className={`flex items-start justify-between gap-2 ${d.given && !on ? 'text-faint line-through' : ''}`}>
                            <span className="flex min-w-0 flex-col items-start gap-1">
                              <span className="break-keep text-15 font-medium">{d.name}</span>
                              <EfficacyBadge med={d} dim={on || d.given} />
                            </span>
                            <span className={`shrink-0 pt-0.5 text-13 ${on || d.given ? '' : 'text-muted'}`}>{d.dose}</span>
                          </li>
                        ))}
                      </ul>
                      <span
                        className={`flex size-8 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${on ? 'border-brand bg-brand text-on-brand' : partial ? 'border-brand bg-surface text-brand' : next ? 'border-brand bg-surface text-transparent' : 'border-line bg-surface text-transparent'}`}
                        aria-hidden
                      >
                        {partial ? <Minus size={17} strokeWidth={3} /> : <Check size={17} strokeWidth={3} />}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            {careGuide?.asNeeded && (
              <p className="flex items-start gap-2.5 border-t border-line px-5 py-3.5 text-14 text-muted">
                <Clock size={18} strokeWidth={1.75} className="mt-0.5 shrink-0" aria-hidden />
                {careGuide.asNeeded}
              </p>
            )}
          </Panel>
        ) : (
          <Panel as="section" tone="raised" className="flex flex-col items-center gap-4 px-5 py-8 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-brand-soft text-brand">
              <ScanLine size={24} strokeWidth={1.75} aria-hidden />
            </span>
            <span className="flex flex-col gap-1">
              <span className="text-17 font-semibold">지금 먹고 있는 약이 없어요</span>
              <span className="text-14 text-muted">처방전 사진을 올리면 복약 일정과 가이드를 만들어 드려요.</span>
            </span>
            <Button onClick={() => go('upload')} className="w-full max-w-[280px]">처방 올리기</Button>
          </Panel>
        )}

        {/* 최근 기록 */}
        <section className="flex flex-col gap-2.5 pt-2">
          <H2 action={<MoreLink onClick={openHealthLog}>전체 보기</MoreLink>}>최근 병원 기록</H2>
          {rows.length ? (
            <Panel as="ul">
              {rows.slice(0, 3).map((r, j) => (
                <li key={r.id} className={j ? 'border-t border-line' : ''}>
                  <button
                    type="button"
                    onClick={() => {
                      const guideId = guidesOf(childId).find((g) => g.visitId === r.id)?.id;
                      if (r.status) {
                        draftFromVisit(r);
                        go('confirm');
                      }
                      else if (guideId) go('guide', { guideId });
                      else openHealthLog();
                    }}
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
