import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { courses as sampleCourses, sampleMissed, visits as sampleVisits } from '../data/sample.js';

/* ── 날짜 도우미: 'YYYY-MM-DD' 문자열을 기준으로 다뤄요(시간대 영향 없음) ── */
const pad = (n) => String(n).padStart(2, '0');
export const toKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const fromKey = (key) => {
  const [y, m, d] = key.split('-').map(Number);
  return new Date(y, m - 1, d);
};
export const todayKey = () => toKey(new Date());
export const shiftDays = (key, n) => {
  const d = fromKey(key);
  d.setDate(d.getDate() + n);
  return toKey(d);
};
const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
/** '2026-11-18' → { year, month: 11, day: 18, weekday: '수' } */
export const dateParts = (key) => {
  const d = fromKey(key);
  return { year: d.getFullYear(), month: d.getMonth() + 1, day: d.getDate(), weekday: WEEKDAYS[d.getDay()] };
};

const doseKey = (childId, date, slot, name) => `${childId}|${date}|${slot}|${name}`;
/** 같은 아이가 같은 날 같은 병원에서 받은 처방은 하나로 봐요(다시 올리면 덮어써요). */
const visitKey = (v) => `${v.childId}|${v.date}|${v.hospital}`;

/* ── 처방전 약 목록 → 하루 먹는 때 ── */
const SLOTS_BY_COUNT = { 1: ['아침'], 2: ['아침', '저녁'], 3: ['아침', '점심', '저녁'], 4: ['아침', '점심', '저녁', '자기 전'] };
const SLOT_ORDER = ['아침', '점심', '저녁', '자기 전'];
const firstNumber = (text) => Number(String(text ?? '').match(/\d+/)?.[0] ?? 0);
const isAsNeeded = (m) => /열|필요|아플|통증/.test(`${m.perDay?.value ?? ''} ${m.days?.value ?? ''}`);

/**
 * 확인한 약 목록(OCR 결과)으로 복약 일정을 만들어요.
 * 하루 N번 → 아침/점심/저녁/자기 전에 나눠 넣고, "자기 전"이라고 적힌 약은 자기 전에 넣어요.
 * 열날 때·필요할 때 먹는 약은 정해진 때가 없으니 달력에서 빼요.
 * TODO(API): 서버가 복약 시간표를 내려주면 이 추정 대신 그 값을 써요.
 */
export function scheduleFromMeds(meds) {
  const bySlot = new Map(SLOT_ORDER.map((s) => [s, []]));
  for (const m of meds) {
    if (isAsNeeded(m)) continue;
    const count = Math.min(firstNumber(m.perDay?.value), 4);
    const days = firstNumber(m.days?.value);
    if (!count || !days) continue;
    const slots = count === 1 && /자기\s*전|취침/.test(m.timing?.value ?? '') ? ['자기 전'] : SLOTS_BY_COUNT[count];
    for (const slot of slots) bySlot.get(slot).push([m.name, m.dose?.value ?? '', days]);
  }
  return [...bySlot].filter(([, items]) => items.length).map(([slot, items]) => ({ slot, items }));
}

/** 그날 먹여야 하는 약(체크 여부 빼고). 약마다 기간이 다르면 그 약의 기간만큼만 넣어요. */
function scheduledOn(courseList, childId, date) {
  return courseList
    .filter((c) => c.childId === childId && date >= c.start && date < shiftDays(c.start, c.days))
    .flatMap((c) =>
      c.schedule.flatMap(({ slot, items }) =>
        items
          .filter(([, , days]) => !days || date < shiftDays(c.start, days))
          .map(([name, dose]) => ({ key: doseKey(childId, date, slot, name), slot, name, dose, course: c })),
      ),
    );
}

/** 예시 체크 상태 — 예시 처방의 지난 일정은 먹인 것으로, sampleMissed만 빼먹은 것으로 봐요.
 * 새로 올린 처방은 보호자가 체크하기 전까지 모두 안 먹인 것으로 시작해요. */
const sampleCourseIds = new Set(sampleCourses.map((c) => c.id));
const seeded = (key, course) =>
  sampleCourseIds.has(course.id) && key.split('|')[1] < todayKey() && !sampleMissed.includes(key);

const RecordsContext = createContext(null);

/**
 * 복약 체크, 건강기록, 복약 일정.
 * 처방 올리기에서 처방 내용을 확인하면 recordPrescription으로 병원기록과 복약 일정이 자동으로 생겨요.
 * 의료 정보라서 브라우저 저장소에는 남기지 않아요(fe2Draft.js와 같은 원칙). 새로고침하면 예시 데이터로 돌아가요.
 * TODO(API): 처방 확정 API 응답으로 건강기록·복약 일정을 받아오고, 복약 체크도 서버에 저장.
 */
export function RecordsProvider({ children }) {
  const [state, setState] = useState({ doses: {}, visits: [], courses: [] });

  const value = useMemo(() => {
    const addedKeys = new Set(state.visits.map(visitKey));
    // 다시 올린 처방이 예시 기록과 같은 날·같은 병원이면 예시 기록 대신 새 기록을 보여요.
    const hiddenSampleIds = new Set(sampleVisits.filter((v) => addedKeys.has(visitKey(v))).map((v) => v.id));
    const allVisits = [...state.visits, ...sampleVisits.filter((v) => !hiddenSampleIds.has(v.id))];
    const allCourses = [...state.courses, ...sampleCourses.filter((c) => !hiddenSampleIds.has(c.visitId))];
    const isGiven = (key, course) => (key in state.doses ? state.doses[key] : seeded(key, course));

    return {
      /** 그날 먹일 약 + 먹였는지 */
      dosesOn: (childId, date) => scheduledOn(allCourses, childId, date).map((d) => ({ ...d, given: isGiven(d.key, d.course) })),
      /** dose는 dosesOn이 돌려준 항목 */
      toggleDose: (dose) => setState((prev) => ({ ...prev, doses: { ...prev.doses, [dose.key]: !dose.given } })),
      /** 지금 먹고 있는 처방(오늘이 일정 안에 있는 것) */
      activeCourse: (childId, date = todayKey()) =>
        allCourses.find((c) => c.childId === childId && date >= c.start && date < shiftDays(c.start, c.days)) ?? null,
      /** 아이의 건강기록, 최근 날짜부터 */
      visitsOf: (childId) =>
        allVisits.filter((v) => v.childId === childId).sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)),
      /** 처방전 확인이 끝났을 때 — 병원기록과 복약 일정을 자동으로 남겨요. 같은 처방을 다시 올리면 덮어써요. */
      recordPrescription: ({ childId, date, hospital, title, meds }) => {
        const id = `p${Date.now()}`;
        const visit = {
          id, childId, date, hospital, title, note: '', source: 'ocr',
          meds: meds.map((m) => ({ name: m.name, days: m.days?.value ?? '' })),
        };
        const schedule = scheduleFromMeds(meds);
        const days = Math.max(0, ...schedule.flatMap((s) => s.items.map(([, , d]) => d)));
        const course = schedule.length ? { id: `k${id}`, childId, visitId: id, title, hospital, start: date, days, schedule } : null;
        setState((prev) => {
          const replaced = prev.visits.filter((v) => visitKey(v) === visitKey(visit)).map((v) => v.id);
          return {
            ...prev,
            visits: [visit, ...prev.visits.filter((v) => !replaced.includes(v.id))],
            courses: [...(course ? [course] : []), ...prev.courses.filter((c) => !replaced.includes(c.visitId))],
          };
        });
        return visit;
      },
      /** 처방전 없이 다녀온 진료(예방접종, 검진 등)를 직접 남겨요. */
      addVisit: (visit) =>
        setState((prev) => ({ ...prev, visits: [{ id: `u${Date.now()}`, source: 'manual', ...visit }, ...prev.visits] })),
      removeVisit: (id) => setState((prev) => ({ ...prev, visits: prev.visits.filter((v) => v.id !== id) })),
    };
  }, [state]);

  return <RecordsContext.Provider value={value}>{children}</RecordsContext.Provider>;
}

export function useRecords() {
  const ctx = useContext(RecordsContext);
  if (!ctx) throw new Error('useRecords는 RecordsProvider 안에서만 쓸 수 있어요.');
  return ctx;
}
