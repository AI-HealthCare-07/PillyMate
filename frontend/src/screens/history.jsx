import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Check, ChevronLeft, ChevronRight, Minus, Pill, Plus, ScanLine, Trash2 } from 'lucide-react';
import { AlertDialog } from '../components/ui/AlertDialog.jsx';
import { Button } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Panel, Segmented, Tag } from '../components/ui/misc.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';
import { draftFromVisit } from './fe2Draft.js';
import { dateParts, fromKey, groupBySlot, shiftDays, todayKey, useRecords } from '../state/records.jsx';

/** 그 날짜가 들어 있는 주의 일요일 */
const weekStart = (key) => shiftDays(key, -fromKey(key).getDay());

const TABS = [
  { value: 'meds', label: '복약기록' },
  { value: 'health', label: '건강기록' },
];

/** S-07 기록 — 고른 아이의 복약기록(달력)과 건강기록(병원 방문 로그)을 탭으로 나눠 보여요. */
export function HistoryScreen({ go, onTab }) {
  const { child } = useSelectedChild();
  // 탭은 주소(?tab=health)에 남겨서, 가이드를 보고 뒤로 와도 보던 탭이 그대로 열려요.
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'health' ? 'health' : 'meds';
  const setTab = (next) => setParams(next === 'meds' ? {} : { tab: next }, { replace: true });

  return (
    <AppShell tab="history" onTab={onTab} header={<Header title={child ? `${child.name}의 기록` : '기록'} />}>
      <Body className="gap-4 pt-1">
        <Segmented label="기록 종류" value={tab} onChange={setTab} options={TABS} />
        {child && (tab === 'meds' ? <MedCalendar childId={child.id} /> : <HealthLog childId={child.id} go={go} />)}
      </Body>
    </AppShell>
  );
}

/* ───────────────────────── 복약기록: 달력 ───────────────────────── */

const WEEK = ['일', '월', '화', '수', '목', '금', '토'];

/** 하루 상태 — 모두 먹임 / 일부 / 빼먹음 / 앞으로 / 없음 */
function dayStatus(doses, date, today) {
  if (!doses.length) return 'none';
  const n = doses.filter((d) => d.given).length;
  if (n === doses.length) return 'done';
  // 오늘은 하루가 끝나지 않았으니, 다 먹이기 전까진 '먹일 예정'으로 보여요.
  if (date >= today) return 'upcoming';
  return n ? 'partial' : 'missed';
}

const DOT = {
  done: 'bg-brand',
  partial: 'bg-[#D99A00]',
  missed: 'bg-danger',
  upcoming: 'border-[1.5px] border-brand bg-surface',
};
const LEGEND = [
  ['done', '다 먹였어요'],
  ['partial', '일부 빼먹었어요'],
  ['missed', '못 먹였어요'],
  ['upcoming', '먹일 예정'],
];

function MedCalendar({ childId }) {
  const { dosesOn, toggleSlot } = useRecords();
  const today = todayKey();
  const [selected, setSelected] = useState(today);
  // 한 주(일~토)씩 보여요. 화살표로 넘기면 같은 요일이 선택돼요.
  const thisWeek = weekStart(today);
  const [week, setWeek] = useState(thisWeek);
  const cells = Array.from({ length: 7 }, (_, i) => shiftDays(week, i));
  const move = (delta) => {
    setWeek((w) => shiftDays(w, delta * 7));
    setSelected((d) => shiftDays(d, delta * 7));
  };
  const goToday = () => {
    setWeek(thisWeek);
    setSelected(today);
  };

  // 이번 주 요약: 오늘까지 먹일 횟수 중 먹인 횟수
  // 먹는 때 단위로 세요(아침에 약 3개를 먹어도 1번).
  const weekDoses = cells.filter((d) => d <= today).flatMap((d) => groupBySlot(dosesOn(childId, d)));
  const givenCount = weekDoses.filter((g) => g.done).length;
  const a = dateParts(cells[0]);
  const b = dateParts(cells[6]);
  const range = `${a.month}월 ${a.day}일 – ${b.month === a.month ? '' : `${b.month}월 `}${b.day}일`;
  const yearLabel = b.year !== dateParts(today).year ? `${b.year}년 ` : '';

  const sel = dateParts(selected);
  const selDoses = dosesOn(childId, selected);
  const selSlots = groupBySlot(selDoses);
  const future = selected > today;
  const courseNames = [...new Set(selDoses.map((d) => `${d.course.title}, ${d.course.hospital}`))];

  return (
    <div className="flex flex-col gap-4">
      <Panel className="flex flex-col gap-3 px-3 pb-4 pt-3">
        <div className="flex items-center justify-between">
          <button type="button" onClick={() => move(-1)} aria-label="이전 주" className="rounded-md p-2 text-muted hover:bg-paper hover:text-ink">
            <ChevronLeft size={20} aria-hidden />
          </button>
          <div className="flex items-center gap-2">
            <h2 className="text-17 font-bold" aria-live="polite">{yearLabel}{range}</h2>
            {week !== thisWeek && (
              <button type="button" onClick={goToday} className="rounded-pill border border-line px-2.5 py-1 text-12 font-semibold text-brand hover:bg-paper">
                오늘
              </button>
            )}
          </div>
          <button type="button" onClick={() => move(1)} aria-label="다음 주" className="rounded-md p-2 text-muted hover:bg-paper hover:text-ink">
            <ChevronRight size={20} aria-hidden />
          </button>
        </div>

        <div className="grid grid-cols-7 text-center" role="grid" aria-label={`${range} 복약 달력`}>
          {WEEK.map((w, i) => (
            <span key={w} className={`pb-1.5 text-12 font-semibold ${i === 0 ? 'text-danger' : 'text-muted'}`}>{w}</span>
          ))}
          {cells.map((date) => {
            const status = dayStatus(dosesOn(childId, date), date, today);
            const on = date === selected;
            const isToday = date === today;
            const { month, day } = dateParts(date);
            return (
              <button
                key={date}
                type="button"
                onClick={() => setSelected(date)}
                aria-pressed={on}
                aria-label={`${month}월 ${day}일${isToday ? ', 오늘' : ''}${status !== 'none' ? `, ${LEGEND.find(([k]) => k === status)[1]}` : ''}`}
                className={`flex h-14 flex-col items-center justify-center gap-1 rounded-lg transition-colors ${on ? 'bg-brand-soft' : 'hover:bg-paper'}`}
              >
                <span
                  className={`flex size-7 items-center justify-center rounded-full text-14 ${
                    isToday ? 'bg-ink font-bold text-on-brand' : on ? 'font-bold text-brand' : 'font-medium'
                  }`}
                >
                  {day}
                </span>
                <span className={`size-1.5 rounded-full ${DOT[status] ?? ''}`} aria-hidden />
              </button>
            );
          })}
        </div>

        <ul className="flex flex-wrap gap-x-3.5 gap-y-1.5 border-t border-line px-1 pt-3">
          {LEGEND.map(([k, label]) => (
            <li key={k} className="flex items-center gap-1.5 text-12 text-muted">
              <span className={`size-2 rounded-full ${DOT[k]}`} aria-hidden />{label}
            </li>
          ))}
        </ul>
      </Panel>

      {weekDoses.length > 0 && (
        <p className="px-1 text-14 text-muted">
          {week === thisWeek ? '이번 주' : '이 주에'} 먹일 약 <span className="font-semibold text-ink">{weekDoses.length}번</span> 중{' '}
          <span className="font-semibold text-brand">{givenCount}번</span> 먹였어요.
        </p>
      )}

      <section className="flex flex-col gap-2.5">
        <div className="flex flex-col gap-0.5 px-1">
          <h3 className="text-17 font-bold">{sel.month}월 {sel.day}일 ({sel.weekday}){selected === today && ' · 오늘'}</h3>
          {courseNames.length > 0 && <p className="text-13 text-muted">{courseNames.join(' / ')}</p>}
        </div>
        {selDoses.length ? (
          <Panel as="ul" aria-label="이 날 먹일 약">
            {selSlots.map((g, j) => {
              const partial = !g.done && g.given > 0;
              return (
                <li key={g.slot} className={j ? 'border-t border-line' : ''}>
                  <button
                    type="button"
                    disabled={future}
                    aria-pressed={g.done}
                    aria-label={`${g.slot} 약 ${g.doses.length}개, ${future ? '먹일 예정' : g.done ? '먹였어요' : partial ? `${g.doses.length}개 중 ${g.given}개 먹였어요` : '안 먹였어요'}`}
                    onClick={() => toggleSlot(g)}
                    className="flex w-full items-center gap-3.5 px-4 py-3 text-left enabled:hover:bg-paper disabled:cursor-default"
                  >
                    <span className="w-14 shrink-0 self-start pt-0.5 text-14 font-semibold text-brand">{g.slot}</span>
                    <ul className="flex flex-1 flex-col gap-1.5">
                      {g.doses.map((d) => (
                        <li key={d.key} className={`flex items-baseline justify-between gap-2 ${!future && d.given ? 'text-faint' : ''}`}>
                          <span className="text-15 font-medium">{d.name}</span>
                          <span className={`shrink-0 text-13 ${!future && d.given ? '' : 'text-muted'}`}>{d.dose}</span>
                        </li>
                      ))}
                    </ul>
                    {future ? (
                      <span className="text-13 text-faint">예정</span>
                    ) : (
                      <span
                        className={`flex size-7 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
                          g.done ? 'border-brand bg-brand text-on-brand' : partial ? 'border-brand text-brand' : 'border-line text-transparent'
                        }`}
                        aria-hidden
                      >
                        {partial ? <Minus size={16} strokeWidth={3} /> : <Check size={16} strokeWidth={3} />}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </Panel>
        ) : (
          <Panel className="px-4 py-6 text-center text-15 text-muted">이 날은 먹일 약이 없어요.</Panel>
        )}
        {!future && selDoses.length > 0 && <p className="px-1 text-13 text-muted">먹는 때를 누르면 그때 먹을 약을 한 번에 고칠 수 있어요.</p>}
      </section>
    </div>
  );
}

/* ───────────────────────── 건강기록: 병원 방문 로그 ───────────────────────── */

function HealthLog({ childId, go }) {
  const { visitsOf, addVisit, removeVisit } = useRecords();
  const [adding, setAdding] = useState(false);
  // 지울지 묻는 중인 서버 처방 기록. 지우면 되돌릴 수 없어서 한 번 더 물어요.
  const [deleting, setDeleting] = useState(null);
  const list = visitsOf(childId);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start gap-3 rounded-lg bg-sunk px-3.5 py-3">
        <ScanLine size={20} strokeWidth={1.75} className="mt-0.5 shrink-0 text-brand" aria-hidden />
        <p className="flex-1 text-14">
          처방 올리기에서 처방전을 확인하면 <span className="font-semibold">병원, 날짜, 병명, 약과 며칠분</span>이 여기에 자동으로 남아요.
        </p>
      </div>
      {adding ? (
        <VisitForm
          onCancel={() => setAdding(false)}
          onSave={(v) => {
            addVisit({ ...v, childId });
            setAdding(false);
          }}
        />
      ) : (
        <Button variant="secondary" className="w-full gap-1.5" onClick={() => setAdding(true)}>
          <Plus size={18} strokeWidth={2} aria-hidden />직접 기록 남기기
        </Button>
      )}

      {list.length === 0 && !adding && (
        <p className="py-10 text-center text-15 text-muted">아직 남긴 건강기록이 없어요.</p>
      )}

      <ol className="flex flex-col" aria-label="건강기록">
        {list.map((v, i) => {
          const p = dateParts(v.date);
          const newYear = i === 0 || dateParts(list[i - 1].date).year !== p.year;
          return (
            <li key={v.id} className="flex flex-col">
              {newYear && <h3 className="px-1 pb-2 pt-1 text-14 font-semibold text-muted">{p.year}년</h3>}
              <div className="flex gap-3">
                {/* 날짜 + 세로 선 */}
                <div className="flex w-12 shrink-0 flex-col items-center">
                  <span className="text-13 font-semibold text-muted">{p.month}월</span>
                  <span className="text-20 font-bold leading-tight">{p.day}</span>
                  <span className="text-12 text-muted">{p.weekday}</span>
                  {i < list.length - 1 && <span className="mt-1.5 w-px flex-1 bg-line" aria-hidden />}
                </div>
                <Panel className="mb-3 flex flex-1 flex-col gap-2.5 px-4 py-3.5">
                  <div className="flex items-start gap-2">
                    <div className="flex flex-1 flex-col gap-0.5">
                      <p className="text-16 font-semibold">{v.title}</p>
                      <p className="text-14 text-muted">{v.hospital}</p>
                    </div>
                    {v.status ? <Tag>{v.status}</Tag> : <Tag tone="faint">{v.source === 'ocr' ? '처방전 자동 기록' : '직접 기록'}</Tag>}
                  </div>
                  {v.meds.length > 0 ? (
                    <ul className="flex flex-wrap gap-1.5" aria-label="처방받은 약">
                      {v.meds.map((m) => (
                        <li key={m.name} className="flex items-center gap-1 rounded-md bg-sunk px-2 py-1 text-13">
                          <Pill size={13} strokeWidth={2} className="text-brand" aria-hidden />{m.name}
                          {m.days && <span className="text-muted">· {m.days}{/^\d+일$/.test(m.days) ? '분' : ''}</span>}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-13 text-faint">처방받은 약 없음</p>
                  )}
                  {v.note && <p className="text-14 text-muted">{v.note}</p>}
                  <VisitActions
                    visit={v}
                    onConfirm={() => {
                      draftFromVisit(v);
                      go('confirm');
                    }}
                    onRemove={() => (v.prescriptionId ? setDeleting(v) : removeVisit(v.id))}
                  />
                </Panel>
              </div>
            </li>
          );
        })}
      </ol>
      <DeletePrescriptionDialog visit={deleting} onClose={() => setDeleting(null)} />
    </div>
  );
}

/**
 * 건강기록 카드 아래 버튼.
 * - 확인 전 처방: 처방 확인하기 (복약 가이드는 가이드 탭에서 봐요)
 * - 서버에 올린 처방: 지우기 (서버에서 지워요)
 * - 직접 남긴 기록: 지우기 (이번 방문에서만 있는 기록이라 바로 지워요). 예시 기록(v…)은 못 지워요.
 */
function VisitActions({ visit: v, onConfirm, onRemove }) {
  const canConfirm = v.source === 'ocr' && Boolean(v.status);
  const canRemove = Boolean(v.prescriptionId) || (v.source === 'manual' && !v.id.startsWith('v'));
  if (!canConfirm && !canRemove) return null;

  return (
    <div className="flex items-center gap-3">
      {canConfirm && (
        <button type="button" onClick={onConfirm} className="flex items-center gap-0.5 text-14 font-semibold text-brand">
          처방 확인하기<ChevronRight size={16} aria-hidden />
        </button>
      )}
      {canRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`${dateParts(v.date).month}월 ${dateParts(v.date).day}일 ${v.hospital} 기록 지우기`}
          className={`flex items-center gap-1 text-13 font-medium text-muted hover:text-danger ${canConfirm ? 'ml-auto' : ''}`}
        >
          <Trash2 size={14} aria-hidden />지우기
        </button>
      )}
    </div>
  );
}

/** 서버 처방 기록 지우기 확인 — 지우면 약·복약 일정·가이드도 함께 사라지고 되돌릴 수 없어요. */
function DeletePrescriptionDialog({ visit, onClose }) {
  const { deletePrescription } = useRecords();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!visit) return null;

  const { month, day } = dateParts(visit.date);
  const close = () => {
    setError('');
    onClose();
  };
  const confirm = async () => {
    setBusy(true);
    setError('');
    try {
      await deletePrescription(visit);
      close();
    } catch (e) {
      setError(e.message || '처방 기록을 지우지 못했어요. 잠시 후 다시 시도해 주세요.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AlertDialog
      open
      title="이 처방 기록을 지울까요?"
      description={`${month}월 ${day}일 ${visit.hospital} 처방이에요. 약 목록, 복약 일정, 복약 가이드도 함께 지워지고 되돌릴 수 없어요.`}
    >
      {error && <p role="alert" className="text-13 text-danger">{error}</p>}
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={confirm}
          disabled={busy}
          className="inline-flex h-13 w-full items-center justify-center rounded-lg bg-danger px-5 text-16 font-semibold text-white transition-opacity disabled:opacity-60"
        >
          {busy ? '지우는 중…' : '지우기'}
        </button>
        <Button variant="secondary" className="w-full" onClick={close} disabled={busy}>
          취소
        </Button>
      </div>
    </AlertDialog>
  );
}

/** 병원 기록 남기기 — 날짜, 병원, 이유, 처방받은 약(칩으로 하나씩 추가), 메모 */
function VisitForm({ onSave, onCancel }) {
  const [date, setDate] = useState(todayKey());
  const [hospital, setHospital] = useState('');
  const [title, setTitle] = useState('');
  const [note, setNote] = useState('');
  const [meds, setMeds] = useState([]);
  const [med, setMed] = useState('');
  const [error, setError] = useState('');

  const addMed = () => {
    const name = med.trim();
    if (name && !meds.includes(name)) setMeds((prev) => [...prev, name]);
    setMed('');
  };
  const submit = () => {
    if (!hospital.trim() || !title.trim()) {
      setError('병원과 진료 이유를 적어 주세요.');
      return;
    }
    const pending = med.trim();
    onSave({
      date,
      hospital: hospital.trim(),
      title: title.trim(),
      note: note.trim(),
      meds: (pending && !meds.includes(pending) ? [...meds, pending] : meds).map((name) => ({ name })),
    });
  };

  return (
    <Panel className="flex flex-col gap-4 p-4">
      <div className="flex flex-col gap-0.5">
        <h3 className="text-17 font-bold">직접 기록 남기기</h3>
        <p className="text-13 text-muted">처방전이 없는 진료(예방접종, 검진 등)를 적어 두세요.</p>
      </div>
      <Field label="다녀온 날" type="date" value={date} max={todayKey()} onChange={(e) => setDate(e.target.value)} />
      <Field label="병원" placeholder="예: 튼튼소아청소년과" value={hospital} onChange={(e) => setHospital(e.target.value)} />
      <Field label="진료 이유" placeholder="예: 감기, 예방접종, 정기 검진" value={title} onChange={(e) => setTitle(e.target.value)} />
      <div className="flex flex-col gap-2">
        <label htmlFor="visit-med" className="text-14 font-medium text-muted">처방받은 약</label>
        {meds.length > 0 && (
          <ul className="flex flex-wrap gap-1.5">
            {meds.map((m) => (
              <li key={m}>
                <button
                  type="button"
                  onClick={() => setMeds((prev) => prev.filter((x) => x !== m))}
                  aria-label={`${m} 빼기`}
                  className="flex items-center gap-1 rounded-md bg-brand-soft px-2 py-1 text-13 font-medium text-brand"
                >
                  {m}<span aria-hidden>×</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          <input
            id="visit-med"
            value={med}
            onChange={(e) => setMed(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); addMed(); }
            }}
            placeholder="약 이름을 적고 추가"
            className="h-11 min-w-0 flex-1 rounded-md border border-line bg-surface px-3.5 text-15 placeholder:text-faint focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
          />
          <button type="button" onClick={addMed} disabled={!med.trim()} className="shrink-0 rounded-md border border-line bg-surface px-4 text-14 font-semibold hover:bg-paper disabled:opacity-40">
            추가
          </button>
        </div>
      </div>
      <Field label="메모" multiline placeholder="예: 열 38.5도, 일주일 뒤 다시 오래요" value={note} onChange={(e) => setNote(e.target.value)} />
      {error && <p role="alert" className="text-13 text-danger">{error}</p>}
      <div className="flex gap-2">
        <Button variant="secondary" className="flex-1" onClick={onCancel}>취소</Button>
        <Button className="flex-1" onClick={submit}>저장하기</Button>
      </div>
    </Panel>
  );
}
