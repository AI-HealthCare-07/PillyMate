import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowRight, BookOpen, Check, ChevronRight, Clock, MessageCircle, Minus, ScanLine, UserPlus } from 'lucide-react';
import { AppShell } from '../components/ui/layout.jsx';
import { dateParts, fromKey, groupBySlot, todayKey, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';
import { draftFromVisit } from './fe2Draft.js';
import { EFFICACY_PENDING_LABEL, efficacyOf } from '../data/efficacy.js';
import { useAddChildConsent } from '../components/child/AddChildConsent.jsx';

/**
 * 약 이름 아래 약효 분류 배지. 확인된 분류가 없으면 짐작하지 않고 '약효 정보 확인 중'으로 보여 줘요.
 * inline-flex라서 먹인 약의 취소선이 배지까지 내려오지 않아요.
 */
const EfficacyBadge = ({ med, dim }) => {
  const info = efficacyOf(med);
  const tone = !info
    ? 'border-dashed border-edge/60 bg-surface text-muted'
    : dim
      ? 'border-line bg-surface text-muted'
      : 'border-transparent bg-lav text-lav-ink';
  return (
    <span className={`inline-flex max-w-full items-center rounded-pill border px-2 py-px text-12 font-semibold ${tone}`}>
      <span className="sr-only">약효 분류: </span>
      <span className="break-keep">{info?.label ?? EFFICACY_PENDING_LABEL}</span>
    </span>
  );
};

/** 한 때(아침 등)의 약을 처방별로 묶어요. 처방 순서는 오늘 일정에 나온 순서 그대로예요. */
function byCourse(doses) {
  const groups = new Map();
  for (const d of doses) {
    if (!groups.has(d.course.id)) groups.set(d.course.id, { course: d.course, doses: [] });
    groups.get(d.course.id).doses.push(d);
  }
  return [...groups.values()];
}

/** 오늘 먹을 약 한 줄씩 — 약 이름, 효능, 1회 양 */
function DoseList({ doses, on }) {
  return (
    <ul className={`flex min-w-0 flex-1 flex-col gap-1.5 ${on ? 'text-muted line-through' : ''}`}>
      {doses.map((d) => (
        <li key={d.key} className={`flex items-start justify-between gap-2 ${d.given && !on ? 'text-muted line-through' : ''}`}>
          <span className="flex min-w-0 flex-col items-start gap-1">
            <span className="break-keep text-15 font-medium">{d.name}</span>
            <EfficacyBadge med={d} dim={on || d.given} />
          </span>
          <span className="shrink-0 pt-0.5 text-13 text-muted">{d.dose}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * 홈 — 지금 고른 아이 기준으로 오늘 먹을 약, 확인할 처방, 최근 기록을 한눈에 보여요.
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
  const careGuide = care ? guidesOf(childId).find((g) => g.visitId === care.visitId) : null;
  const careGuideId = careGuide?.id ?? null;
  const openGuides = () =>
    navigate(`/guides?${new URLSearchParams({ child: childId, ...(careGuideId ? { open: careGuideId } : {}) })}`);
  const dayOf = (course) => Math.round((fromKey(today) - fromKey(course.start)) / 86400000) + 1;
  // 오늘 먹을 약이 나온 처방들(목록과 같은 순서). 약이 없으면 지금 먹는 처방 하나만 보여요.
  const todayCourses = [...new Map(doses.map((d) => [d.course.id, d.course])).values()];
  const headerCourses = todayCourses.length ? todayCourses : care ? [care] : [];
  const todayLabel = fromKey(today).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' });

  if (!child) {
    return (
      <AppShell tab="home" onTab={onTab} width="wide">
        <div className="flex flex-1 flex-col items-center justify-center gap-5 px-5 py-16 text-center">
          <Illustration className="w-[150px]" />
          <p className="text-20 font-bold">먼저 아이를 등록해 주세요</p>
          <button type="button" onClick={addFlow.start} className="inline-flex h-13 items-center gap-2 rounded-lg bg-brand px-6 text-16 font-semibold text-on-brand hover:bg-brand-hover">
            <UserPlus size={19} aria-hidden />아이 추가하기
          </button>
          {addFlow.modal}
        </div>
      </AppShell>
    );
  }

  const slots = groupBySlot(doses);
  // 오늘 먹을 약이 두 처방 이상에서 왔는지 — 그럴 때만 처방별로 칸을 나눠요.
  const multiCourse = new Set(doses.map((d) => d.course.id)).size > 1;
  const slotsDone = slots.filter((g) => g.done).length;
  const nextSlot = slots.find((g) => !g.done)?.slot;
  const allDone = slots.length > 0 && slotsDone === slots.length;

  // 처방 올리기는 약이 없을 때 빈 카드에 이미 버튼이 있어서 그땐 빼요.
  const shortcuts = [
    care && { key: 'upload', label: '처방 올리기', icon: ScanLine, tile: 'bg-mark', chip: 'bg-mark text-ink', onClick: () => go('upload') },
    { key: 'guide', label: '가이드', icon: BookOpen, tile: 'bg-brand-soft', chip: 'bg-brand-soft text-brand', onClick: openGuides },
    { key: 'chat', label: '챗봇', icon: MessageCircle, tile: 'bg-lav', chip: 'bg-lav text-lav-ink', onClick: () => onTab?.('chat') },
  ].filter(Boolean);

  return (
    <AppShell tab="home" onTab={onTab} width="wide">
      <div className="flex flex-col gap-4 px-4 pb-6 pt-1 min-[390px]:px-5 xl:grid xl:grid-cols-[minmax(0,1fr)_340px] xl:items-start xl:gap-x-8 xl:gap-y-6 xl:px-0 xl:pb-14 xl:pt-6">
        {/* ── 인사: 모바일은 크림 옐로 카드 + 일러스트, 데스크톱은 바탕 위 텍스트로 절제 ── */}
        <section className="relative overflow-hidden rounded-2xl bg-mark-soft px-5 pb-5 pt-5 xl:col-span-2 xl:flex xl:items-end xl:justify-between xl:rounded-none xl:bg-transparent xl:p-0">
          <div className="flex flex-col gap-1 pr-[104px] xl:pr-0">
            <p className="text-14 font-semibold text-terra-ink">{todayLabel}</p>
            <h1 className="text-[26px] font-bold leading-[1.3] tracking-[-0.02em] xl:text-32">{child.name}의 하루</h1>
          </div>
          <div className="mt-3.5 flex flex-wrap items-center gap-1.5 xl:hidden">
            <span className="rounded-pill bg-surface px-3 py-1.5 text-13 font-semibold">{[child.age, child.weight].filter(Boolean).join(' · ')}</span>
            <AllergyBadge allergy={child.allergy} />
          </div>
          <Illustration className="absolute -right-1 top-3 w-[118px] xl:hidden" />
        </section>

        {/* ── 왼쪽(모바일은 전체) 단 ── */}
        <div className="flex min-w-0 flex-col gap-4 xl:gap-6">
          {/* 확인 전 처방 — 가장 최근 것만 카드로 보여 주고, 나머지는 건강기록에서 확인해요. */}
          {pending.slice(0, 1).map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => {
                draftFromVisit(r);
                go('confirm');
              }}
              className="flex items-center gap-3.5 rounded-xl bg-mark px-4 py-3.5 text-left"
            >
              <span className="flex size-11 shrink-0 items-center justify-center rounded-pill bg-surface" aria-hidden>
                <ScanLine size={21} strokeWidth={1.9} />
              </span>
              <span className="flex flex-1 flex-col gap-0.5">
                <span className="text-15 font-bold">확인하지 않은 처방이 있어요</span>
                <span className="text-14">{r.month} {r.day}일 {r.title}, 약 {r.medCount}개. 약 내용을 확인하면 가이드를 만들어요.</span>
              </span>
              <ChevronRight size={20} className="shrink-0" aria-hidden />
            </button>
          ))}
          {pending.length > 1 && (
            <button type="button" onClick={openHealthLog} className="-mt-2 inline-flex min-h-11 items-center gap-0.5 self-end rounded-md px-2 text-14 font-semibold text-mark-ink hover:bg-mark-soft">
              확인하지 않은 처방 {pending.length - 1}개 더 보기<ChevronRight size={16} aria-hidden />
            </button>
          )}

          {/* 오늘 먹을 약 — 화면의 핵심. 세이지 계열 */}
          {care ? (
            <section aria-labelledby="today-meds" className="overflow-hidden rounded-2xl border border-line bg-surface">
              <div className="flex flex-col gap-4 bg-brand-soft px-5 pb-5 pt-5 xl:px-6">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <h2 id="today-meds" className="text-18 font-bold text-brand">오늘 먹을 약</h2>
                    {headerCourses.map((c) => (
                      <p key={c.id} className="text-13 text-ok">{c.title} · {c.hospital} · {c.days}일 중 {dayOf(c)}일째</p>
                    ))}
                  </div>
                  <button type="button" onClick={openGuides} className="inline-flex h-11 shrink-0 items-center gap-1 rounded-pill bg-surface pl-4 pr-3 text-14 font-semibold text-brand hover:bg-white">
                    가이드<ChevronRight size={16} aria-hidden />
                  </button>
                </div>
                <div className="flex items-end justify-between gap-3">
                  <p className="flex items-baseline gap-1 text-brand">
                    <span className="text-[40px] font-bold leading-none tracking-[-0.03em]">{slotsDone}</span>
                    <span className="text-17 font-semibold text-ok">/ {slots.length}</span>
                  </p>
                  <p className="pb-0.5 text-15 font-semibold text-brand">
                    {allDone ? '오늘 약을 모두 먹였어요' : `${slots.length - slotsDone}번 남았어요`}
                  </p>
                </div>
                <div role="progressbar" aria-label="오늘 복약 진행" aria-valuemin={0} aria-valuemax={slots.length} aria-valuenow={slotsDone} className="flex gap-1.5">
                  {slots.map((g) => (
                    <span key={g.slot} className={`h-2 flex-1 rounded-pill ${g.done ? 'bg-brand' : g.given ? 'bg-sage' : 'bg-surface'}`} />
                  ))}
                </div>
              </div>

              <ul aria-label="오늘 먹을 약 목록" className="divide-y divide-line xl:grid xl:grid-cols-2 xl:divide-y-0">
                {slots.map((g) => {
                  const on = g.done;
                  const partial = !on && g.given > 0;
                  const next = g.slot === nextSlot;
                  return (
                    <li key={g.slot} className="xl:border-b xl:border-line xl:odd:border-r xl:last:odd:col-span-2 xl:last:odd:border-r-0">
                      <button
                        type="button"
                        aria-pressed={on}
                        aria-label={`${g.slot} 약 ${g.doses.length}개${on ? ', 먹였어요' : partial ? `, ${g.doses.length}개 중 ${g.given}개 먹였어요` : ', 아직 안 먹였어요'}`}
                        onClick={() => toggleSlot(g)}
                        className="flex h-full w-full items-center gap-3 px-5 py-4 text-left hover:bg-paper/60"
                      >
                        <span className={`flex w-[62px] shrink-0 flex-col self-start text-14 font-bold ${on ? 'text-muted' : 'text-brand'}`}>
                          {g.slot}
                          {next && <span className="mt-1 w-fit rounded-pill bg-brand-soft px-2 py-px text-12 font-semibold text-brand">다음 복용</span>}
                        </span>
                        {multiCourse ? (
                          // 처방이 여러 개 겹친 날 — 같은 때 안에서도 처방(병원)별로 칸을 나눠 어디서 받은 약인지 보여요.
                          <ul className="flex min-w-0 flex-1 flex-col divide-y divide-line">
                            {byCourse(g.doses).map(({ course, doses: courseDoses }) => (
                              <li key={course.id} className="flex flex-col gap-1.5 py-2.5 first:pt-0 last:pb-0">
                                <span className={`break-keep text-12 font-semibold ${on ? 'text-faint' : 'text-muted'}`}>{course.hospital} · {course.title}</span>
                                <DoseList doses={courseDoses} on={on} />
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <DoseList doses={g.doses} on={on} />
                        )}
                        <span
                          className={`flex size-10 shrink-0 items-center justify-center rounded-pill ${on ? 'bg-brand text-on-brand' : partial ? 'border-2 border-brand bg-surface text-brand' : 'border-2 border-edge bg-surface text-transparent'}`}
                          aria-hidden
                        >
                          {partial ? <Minus size={18} strokeWidth={3} /> : <Check size={18} strokeWidth={3} />}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              {careGuide?.asNeeded && (
                <p className="flex items-start gap-2.5 border-t border-line bg-paper/50 px-5 py-3.5 text-14">
                  <Clock size={18} strokeWidth={1.75} className="mt-0.5 shrink-0 text-muted" aria-hidden />
                  {careGuide.asNeeded}
                </p>
              )}
            </section>
          ) : (
            <section className="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5 xl:flex-row xl:items-center xl:p-6">
              <span className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-mark" aria-hidden>
                <ScanLine size={26} strokeWidth={1.75} />
              </span>
              <span className="flex flex-1 flex-col gap-1">
                <span className="text-18 font-bold">지금 먹고 있는 약이 없어요</span>
                <span className="text-14 text-terra-ink">처방전 사진을 올리면 복약 일정과 가이드를 만들어 드려요.</span>
              </span>
              <button type="button" onClick={() => go('upload')} className="h-13 shrink-0 rounded-lg bg-brand px-6 text-16 font-semibold text-on-brand hover:bg-brand-hover">처방 올리기</button>
            </section>
          )}

          {/* 바로가기 — 모바일: 첫 칸은 넓게, 나머지는 반 칸 */}
          <nav aria-label="바로가기" className="grid grid-cols-2 gap-2.5 xl:hidden">
            {shortcuts.map((s, i) => {
              const wide = s.key === 'upload';
              return (
                <button
                  key={s.key}
                  type="button"
                  onClick={s.onClick}
                  className={`flex gap-3 rounded-xl px-4 text-left ${s.tile} ${wide ? 'col-span-2 min-h-[64px] items-center' : 'min-h-[88px] flex-col items-start justify-between py-3.5'}`}
                >
                  <span className={`flex size-9 items-center justify-center rounded-pill bg-surface/80 ${s.key === 'chat' ? 'text-lav-ink' : 'text-brand'}`} aria-hidden>
                    <s.icon size={19} strokeWidth={1.9} />
                  </span>
                  <span className="flex flex-1 items-center justify-between self-stretch">
                    <span className="text-15 font-bold">{s.label}</span>
                    <ArrowRight size={17} className="text-muted" aria-hidden />
                  </span>
                </button>
              );
            })}
          </nav>

          {/* 최근 병원 기록 — 카드 대신 줄로 나눈 목록 */}
          <section className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <h2 className="text-17 font-bold">최근 병원 기록</h2>
              <button type="button" onClick={openHealthLog} className="flex min-h-11 items-center gap-0.5 pl-2 text-14 font-semibold text-muted hover:text-ink">
                전체 보기<ChevronRight size={16} aria-hidden />
              </button>
            </div>
            {rows.length ? (
              <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
                {rows.slice(0, 3).map((r) => (
                  <li key={r.id}>
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
                      className="flex w-full items-center gap-3.5 px-4 py-3.5 text-left hover:bg-paper/60"
                    >
                      <span className="flex w-11 shrink-0 flex-col items-center rounded-xl bg-sunk py-1.5">
                        <span className="text-12 font-semibold leading-tight text-muted">{r.month}</span>
                        <span className="text-18 font-bold leading-tight">{r.day}<span className="text-12 font-semibold">일</span></span>
                      </span>
                      <span className="flex min-w-0 flex-1 flex-col">
                        <span className="truncate text-15 font-semibold">{r.title}</span>
                        <span className="truncate text-13 text-muted">{r.hospital}{r.medCount ? ` · 약 ${r.medCount}개` : ''}</span>
                      </span>
                      {r.status && <span className="shrink-0 rounded-pill bg-mark px-2.5 py-1 text-12 font-semibold">{r.status}</span>}
                      <ChevronRight size={18} className="shrink-0 text-muted" aria-hidden />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-15 text-muted">아직 올린 처방이 없어요.</p>
            )}
          </section>
        </div>

        {/* ── 데스크톱 오른쪽 단: 아이 정보 + 바로가기 (색 사용 절제) ── */}
        <aside className="hidden flex-col gap-4 xl:flex">
          <section aria-label="아이 정보" className="flex flex-col gap-4 overflow-hidden rounded-2xl border border-line bg-surface">
            <div className="flex items-center gap-3.5 bg-mark-soft px-5 pb-4 pt-5">
              <span className="flex size-12 items-center justify-center rounded-pill bg-surface text-20 font-bold text-terra-ink" aria-hidden>{child.name[0]}</span>
              <span className="flex flex-1 flex-col">
                <span className="text-17 font-bold">{child.name}</span>
                <span className="text-14 text-muted">{[child.age, child.weight].filter(Boolean).join(' · ')}</span>
              </span>
              <Illustration className="w-[72px]" />
            </div>
            <div className="px-5 pb-5">
              <AllergyBadge allergy={child.allergy} block />
            </div>
          </section>

          <nav aria-label="바로가기" className="divide-y divide-line rounded-2xl border border-line bg-surface">
            {shortcuts.map((s) => (
              <button key={s.key} type="button" onClick={s.onClick} className="flex min-h-[60px] w-full items-center gap-3 px-4 text-left first:rounded-t-2xl last:rounded-b-2xl hover:bg-paper/60">
                <span className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${s.chip}`} aria-hidden>
                  <s.icon size={18} strokeWidth={1.9} />
                </span>
                <span className="flex-1 text-15 font-semibold">{s.label}</span>
                <ChevronRight size={18} className="text-muted" aria-hidden />
              </button>
            ))}
          </nav>
        </aside>
      </div>
    </AppShell>
  );
}

/** 알레르기 — 의료 안전 정보라 팔레트와 별도의 위험 색 + 아이콘으로 구분해요. */
function AllergyBadge({ allergy, block }) {
  if (!allergy) {
    return <span className={`w-fit rounded-pill bg-sunk px-3 py-1.5 text-13 font-semibold text-muted ${block ? 'block' : ''}`}>알레르기 없음</span>;
  }
  return (
    <span className={`inline-flex items-center gap-1.5 border border-danger/30 bg-danger-soft font-semibold text-danger ${block ? 'w-full rounded-xl px-3 py-2.5 text-14' : 'rounded-pill px-3 py-1.5 text-13'}`}>
      <AlertTriangle size={block ? 16 : 14} strokeWidth={2.25} className="shrink-0" aria-hidden />
      {allergy}
    </span>
  );
}

/** 장식용 일러스트 — 햇살, 잎, 약병. 평면 색만 쓰고 그라데이션·그림자 없음. */
function Illustration({ className = '' }) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden>
      <circle cx="84" cy="30" r="20" className="fill-mark" />
      <path d="M22 88c4-24 16-40 34-46-2 20-14 38-34 46z" className="fill-sage" />
      <path d="M22 88c8-14 18-26 30-38" className="stroke-brand" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M40 90c2-14 10-24 22-28-1 13-9 24-22 28z" className="fill-brand-soft" />
      <rect x="62" y="50" width="30" height="40" rx="7" className="fill-surface stroke-brand" strokeWidth="1.6" />
      <rect x="65" y="42" width="24" height="10" rx="3" className="fill-terra" />
      <rect x="68" y="62" width="18" height="14" rx="3" className="fill-lav" />
      <path d="M77 65v8M73 69h8" className="stroke-lav-ink" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
