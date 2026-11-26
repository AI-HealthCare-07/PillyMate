import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { hasLoginToken } from '../api/children.js';
import { fetchChildAlarms, updatePrescriptionAlarms } from '../api/medicationAlarms.js';
import { fetchChildDoses, saveDoses } from '../api/medicationDoses.js';
import { fetchGuide } from '../api/prescriptionGuide.js';
import { deletePrescription, fetchChildPrescriptions, fetchPrescriptionDetail } from '../api/prescriptionRecords.js';
import { toConfirmMed } from '../api/prescriptionRegistration.js';
import { courses as sampleCourses, guides as sampleGuides, sampleMissed, visits as sampleVisits } from '../data/sample.js';
import { useSelectedChild } from './selectedChild.jsx';

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

/** 먹는 때별 기본 복약 알림 시각. 보호자가 바꾼 시각은 서버(MEDICATION_ALARM)에 저장돼요. */
export const SLOT_TIME = { 아침: [8, 0], 점심: [12, 30], 저녁: [18, 30], '자기 전': [21, 0] };
/** 알림을 보내지 않는 먹는 때 — 자기 전 약은 재우면서 챙기니 따로 알리지 않아요. */
export const NO_ALARM_SLOTS = ['자기 전'];
/** 복약 일정에서 알림을 보내는 먹는 때만 골라요. */
export const alarmSlots = (schedule) => schedule.map((s) => s.slot).filter((slot) => !NO_ALARM_SLOTS.includes(slot));
export const hhmm = ([h, m]) => `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;

/**
 * 그날 먹일 약을 먹는 때(아침/점심/저녁/자기 전)별로 묶어요. 한 번에 체크할 때 써요.
 * 같은 날 처방이 여러 개여도 같은 때의 약은 한 칸으로 모으고, 아침 → 점심 → 저녁 → 자기 전 순서로 보여요.
 * 결과: [{ slot, doses, given(먹인 수), done(모두 먹였는지) }]
 */
export function groupBySlot(doses) {
  const bySlot = new Map();
  for (const d of doses) {
    if (!bySlot.has(d.slot)) bySlot.set(d.slot, { slot: d.slot, doses: [] });
    bySlot.get(d.slot).doses.push(d);
  }
  // 정해진 순서에 없는 때는 맨 뒤로 보내요.
  const order = (slot) => (SLOT_ORDER.includes(slot) ? SLOT_ORDER.indexOf(slot) : SLOT_ORDER.length);
  const slots = [...bySlot.values()].sort((a, b) => order(a.slot) - order(b.slot));
  return slots.map((g) => {
    const given = g.doses.filter((d) => d.given).length;
    return { ...g, given, done: given === g.doses.length };
  });
}

/* ── 처방전 약 목록 → 하루 먹는 때 ── */
const SLOTS_BY_COUNT = { 1: ['아침'], 2: ['아침', '저녁'], 3: ['아침', '점심', '저녁'], 4: ['아침', '점심', '저녁', '자기 전'] };
const SLOT_ORDER = ['아침', '점심', '저녁', '자기 전'];
const firstNumber = (text) => Number(String(text ?? '').match(/\d+/)?.[0] ?? 0);
/** 열날 때·필요할 때 먹는 약인지 — 정해진 때와 기간이 없어요. 용법을 '필요시'로 고른 약도 여기에 들어요. */
export const isAsNeeded = (m) => /열|필요|아플|통증/.test(`${m.perDay?.value ?? ''} ${m.days?.value ?? ''} ${m.timing?.value ?? ''}`);

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
    // 네 번째 값은 서버 약 번호(복약 체크 저장용). 화면은 [이름, 양, 기간]만 써요.
    for (const slot of slots) bySlot.get(slot).push([m.name, m.dose?.value ?? '', days, m.medicationId ?? null]);
  }
  return [...bySlot].filter(([, items]) => items.length).map(([slot, items]) => ({ slot, items }));
}

/**
 * 확인한 약 목록으로 가이드를 만들어요. 처방전에 적힌 값(양·횟수·때·기간)만 옮겨 적고,
 * 위험 신호·생활 습관처럼 처방전에 없는 내용은 지어내지 않고 비워 둬요.
 * TODO(API): 가이드 생성 API 응답(복용법·위험 신호·생활 습관)을 그대로 저장해요.
 */
function guideFromMeds({ meds, ...base }) {
  const v = (f) => String(f?.value ?? '').trim();
  const asNeeded = meds.filter(isAsNeeded).map((m) => [m.name, v(m.dose), v(m.perDay), v(m.timing)].filter(Boolean).join(' · '));
  return {
    ...base,
    asNeeded: asNeeded.length ? `필요할 때 먹는 약: ${asNeeded.join(' / ')}` : null,
    howTo: meds.map((m) => ({
      name: m.name,
      how: [v(m.dose) && `한 번에 ${v(m.dose)}`, v(m.perDay) && (/^\d/.test(v(m.perDay)) ? `하루 ${v(m.perDay)}` : v(m.perDay)), v(m.timing)].filter(Boolean).join(', ') + ' 먹여요.',
      note: v(m.days) ? `복용 기간: ${v(m.days)}` : '',
      // 약별 복용법 표에 쓰는 처방전 값 그대로(1회 양·하루 횟수·기간·용법). 빈 값은 화면에서 '—'로 보여요.
      dose: v(m.dose), perDay: v(m.perDay), days: v(m.days), timing: v(m.timing), asNeeded: isAsNeeded(m),
    })),
    life: [],
    danger: [],
  };
}

/**
 * 처방 확인이 끝났을 때 남기는 건강기록·복약 일정·가이드. 확정한 약 목록(S-04 약 카드 형식)으로 만들어요.
 * prescriptionId가 있으면 서버 처방과 같은 id(rx{번호})를 써서, 서버에서 다시 불러와도 한 기록으로 보여요.
 */
function buildPrescriptionRecord({ prescriptionId, childId, date, hospital, title, meds }) {
  const id = prescriptionId ? `rx${prescriptionId}` : `p${Date.now()}`;
  const visit = {
    id, prescriptionId: prescriptionId ?? null, childId, date, hospital, title, note: '', source: 'ocr',
    meds: meds.map((m) => ({ name: m.name, days: m.days?.value ?? '' })),
  };
  const schedule = scheduleFromMeds(meds);
  const days = Math.max(0, ...schedule.flatMap((s) => s.items.map(([, , d]) => d)));
  const course = schedule.length ? { id: `k${id}`, childId, visitId: id, title, hospital, start: date, days, schedule } : null;
  const guide = guideFromMeds({ id: `g${id}`, childId, visitId: id, title, hospital, date, schedule, meds });
  return { visit, course, guide };
}

/**
 * 서버가 만든 가이드(명세 8·9번 응답의 guide_content) → 가이드 탭 형식.
 * 서버가 이미 화면 형식(schedule·asNeeded·howTo·life·danger)으로 저장해 둬서 이름만 맞춰요.
 * visit은 그 처방의 건강기록이에요. 가이드 id는 g{건강기록 id}라서 처방마다 하나예요.
 */
function guideFromServer(visit, guideResponse) {
  const content = guideResponse.guide_content ?? {};
  return {
    id: `g${visit.id}`, childId: visit.childId, visitId: visit.id, title: visit.title, hospital: visit.hospital, date: visit.date,
    summary: content.summary ?? '',
    schedule: content.schedule ?? [],
    asNeeded: content.asNeeded || null,
    howTo: content.howTo ?? [],
    life: content.life ?? [],
    danger: content.danger ?? [],
    checklist: content.checklist ?? [],
    disclaimer: content.disclaimer ?? '',
    fromServer: true,
  };
}

const SOURCE_LABEL = { PRESCRIPTION: '처방전', PILL_BAG: '약봉투' };
/** 서버가 확정한 처방(7번 확정 API 이후 상태) — 그때부터 복약 일정과 가이드가 생겨요. */
const CONFIRMED_STATUSES = ['CONFIRMED', 'GUIDE_DONE'];

/**
 * 서버 처방 상세(명세 6번) → 건강기록. 확정 전(OCR_DONE)이면 '확인 전' 기록이라 일정·가이드 없이
 * 읽어 둔 약(ocrMeds)만 들고 있다가, 보호자가 '처방 확인하기'로 확인하면 recordPrescription이 대신해요.
 * 확정한 처방은 복약 일정을 만들고, 가이드는 서버가 만든 것(guideResponse)이 있을 때만 보여요(지어내지 않아요).
 * 약봉투의 날짜는 조제일자(약 받은 날)예요. 날짜를 못 읽은 처방은 올린 날(created_at, KST)을 날짜로 써요.
 */
function recordFromServerPrescription(detail, guideResponse) {
  const ocrMeds = detail.medications.map(toConfirmMed);
  const base = {
    prescriptionId: detail.prescription_id,
    childId: String(detail.child_id),
    date: detail.prescription_date ?? detail.created_at.slice(0, 10),
    hospital: detail.hospital_name ?? '병원 이름 없음',
    title: detail.diagnosis_user_input || `${SOURCE_LABEL[detail.source_type] ?? '처방'} 기록`,
  };
  if (CONFIRMED_STATUSES.includes(detail.status)) {
    const record = buildPrescriptionRecord({ ...base, meds: ocrMeds });
    const visit = { ...record.visit, sourceType: detail.source_type };
    return { visit, course: record.course, guide: guideResponse ? guideFromServer(visit, guideResponse) : null };
  }
  return {
    visit: {
      id: `rx${detail.prescription_id}`, ...base, note: detail.symptom_notes ?? '', source: 'ocr', status: '확인 전',
      // 날짜를 못 읽었으면(null) 확인 화면에서 약 받은 날을 다시 고르게 해요.
      sourceType: detail.source_type, prescriptionDate: detail.prescription_date, disease: detail.diagnosis_user_input ?? '',
      diagnosisCodes: detail.diagnosis_extracted ?? '', ocrMeds,
      meds: ocrMeds.map((m) => ({ name: m.name, days: m.days.value })),
    },
    course: null,
    guide: null,
  };
}

const EMPTY_SERVER_RECORDS = { visits: [], courses: [], guides: [], alarms: {}, doses: {} };

/** 서버 알림 설정 하나 → { enabled, times: { 아침: [8, 0] } }. 건강기록 id(rx{번호})로 찾아요. */
const fromServerAlarm = (a) => ({
  enabled: a.enabled,
  times: Object.fromEntries(Object.entries(a.times ?? {}).map(([slot, text]) => [slot, text.split(':').map(Number)])),
});
/** 서버에 올린 처방의 건강기록이면 처방 번호, 아니면(예시·이번 방문 기록) null */
const prescriptionIdOf = (visitId) => Number(String(visitId).match(/^rx(\d+)$/)?.[1]) || null;
/** 서버 기록을 다시 불러오는 화면 — 들어올 때마다 새 처방이 있는지 봐요. */
const RECORD_PATHS = ['/home', '/history', '/guides'];

/**
 * 로그인한 보호자의 모든 아이 처방을 서버에서 불러와요(목록 → 상세 → 가이드가 있으면 가이드).
 * 상세는 처방 번호·상태가 같으면 다시 받지 않아요. 가이드는 한 번 만들면 바뀌지 않아서 처방마다 한 번만 받아요.
 * 목록·상세가 실패하면 직전 기록을 그대로 둬요. 가이드만 실패하면 그 처방은 가이드 없이 보여요.
 */
function useServerPrescriptionRecords() {
  const { childList } = useSelectedChild();
  const { pathname } = useLocation();
  const [records, setRecords] = useState(EMPTY_SERVER_RECORDS);
  const detailCache = useRef(new Map());
  const guideCache = useRef(new Map());
  const childIds = childList.map((c) => c.id).join(',');
  const watching = RECORD_PATHS.includes(pathname);

  useEffect(() => {
    if (!hasLoginToken() || !childIds) {
      detailCache.current.clear();
      guideCache.current.clear();
      setRecords(EMPTY_SERVER_RECORDS);
      return undefined;
    }
    if (!watching) return undefined;
    let cancelled = false;
    (async () => {
      try {
        // 알림 설정은 따로 받아요. 실패해도 처방 기록은 보여 주고, 알림은 직전 값(처음이면 기본값)을 써요.
        const alarmLists = Promise.all(childIds.split(',').map(fetchChildAlarms)).catch(() => null);
        // 복약 체크 기록도 따로 받아요. 실패하면 직전 기록을 그대로 둬요.
        const doseLists = Promise.all(childIds.split(',').map(fetchChildDoses)).catch(() => null);
        const lists = await Promise.all(childIds.split(',').map(fetchChildPrescriptions));
        const details = await Promise.all(
          lists.flat().map(async (summary) => {
            const key = `${summary.prescription_id}|${summary.status}`;
            if (!detailCache.current.has(key)) detailCache.current.set(key, fetchPrescriptionDetail(summary.prescription_id));
            try {
              return await detailCache.current.get(key);
            } catch (error) {
              detailCache.current.delete(key);
              throw error;
            }
          }),
        );
        const guides = await Promise.all(
          details.map(async (detail) => {
            if (detail.status !== 'GUIDE_DONE' && !detail.has_guide) return null;
            const id = detail.prescription_id;
            if (!guideCache.current.has(id)) guideCache.current.set(id, fetchGuide(id));
            try {
              return await guideCache.current.get(id);
            } catch {
              guideCache.current.delete(id);
              return null;
            }
          }),
        );
        const alarms = await alarmLists;
        const doseLogs = await doseLists;
        if (cancelled) return;
        const built = details.map((detail, i) => recordFromServerPrescription(detail, guides[i]));
        setRecords((prev) => ({
          visits: built.map((r) => r.visit),
          courses: built.map((r) => r.course).filter(Boolean),
          guides: built.map((r) => r.guide).filter(Boolean),
          alarms: alarms ? Object.fromEntries(alarms.flat().map((a) => [`rx${a.prescription_id}`, fromServerAlarm(a)])) : prev.alarms,
          // 체크 기록 → { '아이|날짜|때|약 이름': 먹였는지 }. 키가 없으면 '기록 없음'이에요.
          doses: doseLogs
            ? Object.fromEntries(
                childIds.split(',').flatMap((childId, i) =>
                  doseLogs[i].map((d) => [doseKey(childId, d.dose_date, d.slot, d.medication_name), d.is_taken]),
                ),
              )
            : prev.doses,
        }));
      } catch {
        // 서버에 닿지 않으면 직전 기록을 그대로 보여요. 다음에 화면을 옮길 때 다시 불러요.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [childIds, watching, pathname]);

  return records;
}

/** 그날 먹여야 하는 약(체크 여부 빼고). 약마다 기간이 다르면 그 약의 기간만큼만 넣어요. */
function scheduledOn(courseList, childId, date) {
  return courseList
    .filter((c) => c.childId === childId && date >= c.start && date < shiftDays(c.start, c.days))
    .flatMap((c) =>
      c.schedule.flatMap(({ slot, items }) =>
        items
          .filter(([, , days]) => !days || date < shiftDays(c.start, days))
          .map(([name, dose, , medicationId]) => ({ key: doseKey(childId, date, slot, name), date, slot, name, dose, medicationId, course: c })),
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
 * 서버에 올린 처방(명세 6·10번)도 불러와서 함께 보여요. 이번 방문에서 확인한 기록이 같은 처방이면 그쪽을 보여요.
 * 의료 정보라서 브라우저 저장소에는 남기지 않아요(fe2Draft.js와 같은 원칙). 새로고침하면 서버 기록과 예시 데이터로 돌아가요.
 * 서버 처방의 알림 켜기/끄기·시각은 서버에 저장해서 새로고침·재로그인 뒤에도 그대로예요(alarmEnabled·alarmTimes는 저장 직후 값).
 * 서버 처방의 복약 체크(먹였어요·취소)도 서버(MEDICATION_DOSE_LOG)에 저장해요. 체크 기록이 없는 지난 때는 '기록 없음'이에요.
 */
export function RecordsProvider({ children }) {
  const [state, setState] = useState({ doses: {}, visits: [], courses: [], guides: [], alarmEnabled: {}, alarmSince: {}, alarmTimes: {}, removedChildIds: [], deletedPrescriptionIds: [] });
  const server = useServerPrescriptionRecords();

  const value = useMemo(() => {
    // 이번 방문에서 확인한 기록 > 서버 기록 > 예시 기록. 같은 처방(id)이거나 같은 날·같은 병원이면 앞의 것만 보여요.
    const localIds = new Set(state.visits.map((v) => v.id));
    const localKeys = new Set(state.visits.map(visitKey));
    // 지운 처방은 서버 기록을 다시 불러오기 전에도 바로 숨겨요.
    const deleted = new Set(state.deletedPrescriptionIds);
    const serverVisits = server.visits.filter(
      (v) => !deleted.has(v.prescriptionId) && !localIds.has(v.id) && !localKeys.has(visitKey(v)),
    );
    const shownServerIds = new Set(serverVisits.map((v) => v.id));
    const addedKeys = new Set([...state.visits, ...serverVisits].map(visitKey));
    // 다시 올린 처방이 예시 기록과 같은 날·같은 병원이면 예시 기록 대신 새 기록을 보여요.
    const hiddenSampleIds = new Set(sampleVisits.filter((v) => addedKeys.has(visitKey(v))).map((v) => v.id));
    const removed = new Set(state.removedChildIds);
    const allVisits = [...state.visits, ...serverVisits, ...sampleVisits.filter((v) => !hiddenSampleIds.has(v.id))].filter((v) => !removed.has(v.childId));
    const allCourses = [
      ...state.courses,
      ...server.courses.filter((c) => shownServerIds.has(c.visitId)),
      ...sampleCourses.filter((c) => !hiddenSampleIds.has(c.visitId)),
    ].filter((c) => !removed.has(c.childId));
    // 저장된 가이드 — 이번에 올린 처방으로 만든 가이드 + 서버 확정 처방의 가이드 + 예시 가이드
    const visibleIds = new Set(allVisits.map((v) => v.id));
    // 이번 방문에서 받은 가이드와 같은 처방(같은 id)의 서버 가이드는 겹쳐 보이지 않아요.
    const localGuideIds = new Set(state.guides.map((g) => g.id));
    const allGuides = [...state.guides, ...server.guides.filter((g) => !localGuideIds.has(g.id)), ...sampleGuides]
      .filter((g) => visibleIds.has(g.visitId))
      .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
    const isGiven = (key, course) =>
      key in state.doses ? state.doses[key] : key in server.doses ? server.doses[key] : seeded(key, course);
    // 체크했거나 취소한 기록이 있는지. 예시 처방의 지난 일정은 기록이 있는 것으로 봐요.
    const isRecorded = (key, course) =>
      key in state.doses || key in server.doses || (sampleCourseIds.has(course.id) && key.split('|')[1] < todayKey());
    /** 서버 약 번호 — 일정에 없으면(이번 방문에 확정하며 새로 넣은 약) 서버 일정, 그다음 처방 상세에서 이름으로 찾아요. */
    const medicationIdOf = async (prescriptionId, dose) => {
      if (dose.medicationId) return dose.medicationId;
      const known = server.courses
        .find((c) => c.visitId === dose.course.visitId)
        ?.schedule.flatMap((s) => s.items)
        .find(([name, , , id]) => name === dose.name && id)?.[3];
      if (known) return known;
      const detail = await fetchPrescriptionDetail(prescriptionId);
      return detail.medications.find((m) => m.name === dose.name)?.medication_id ?? null;
    };
    /**
     * 복약 체크·취소 — 화면에 먼저 반영하고, 서버 처방이면 처방·날짜별로 묶어 저장해요.
     * 저장에 실패하면 그 체크만 이전 상태로 되돌려요(예시 처방·이번 방문 기록은 화면에만 남아요).
     */
    const setGiven = (doses, given) => {
      const before = Object.fromEntries(doses.map((d) => [d.key, state.doses[d.key]]));
      setState((prev) => ({ ...prev, doses: { ...prev.doses, ...Object.fromEntries(doses.map((d) => [d.key, given])) } }));
      const groups = new Map();
      for (const d of doses) {
        const prescriptionId = prescriptionIdOf(d.course.visitId);
        if (!prescriptionId) continue;
        const groupKey = `${prescriptionId}|${d.date}`;
        if (!groups.has(groupKey)) groups.set(groupKey, { prescriptionId, date: d.date, doses: [] });
        groups.get(groupKey).doses.push(d);
      }
      for (const g of groups.values()) {
        (async () => {
          const items = await Promise.all(
            g.doses.map(async (d) => ({ medication_id: await medicationIdOf(g.prescriptionId, d), slot: d.slot, is_taken: given })),
          );
          if (items.some((item) => !item.medication_id)) throw new Error('약 번호를 찾지 못했어요.');
          await saveDoses(g.prescriptionId, { dose_date: g.date, items });
        })().catch(() => {
          setState((prev) => {
            const next = { ...prev.doses };
            for (const d of g.doses) {
              if (before[d.key] === undefined) delete next[d.key];
              else next[d.key] = before[d.key];
            }
            return { ...prev, doses: next };
          });
        });
      }
    };
    // 처방 하나의 복용 기간 — 홈·알림(dosesOn)과 같은 기준: 시작일 ≤ 날짜 < 시작일 + 기간
    const courseOfVisit = (visitId) => allCourses.find((c) => c.visitId === visitId) ?? null;
    const inCourse = (c, date) => date >= c.start && date < shiftDays(c.start, c.days);
    const isAlarmOn = (visitId) => state.alarmEnabled[visitId] ?? server.alarms[visitId]?.enabled ?? true;
    const alarmTimeOf = (visitId, slot) =>
      state.alarmTimes[visitId]?.[slot] ?? server.alarms[visitId]?.times?.[slot] ?? SLOT_TIME[slot] ?? [9, 0];
    /**
     * 알림 설정을 화면에 먼저 반영하고, 서버 처방이면 저장해요. 저장된 값으로 맞추고, 실패하면 되돌린 뒤 오류를 던져요.
     * local: 화면에 바로 넣을 값 { enabled?, times? } / body: 서버로 보낼 값
     */
    const saveAlarm = async (visitId, local, body) => {
      const before = { enabled: state.alarmEnabled[visitId], times: state.alarmTimes[visitId] };
      const put = ({ enabled, times }) =>
        setState((prev) => {
          const alarmEnabled = { ...prev.alarmEnabled };
          const alarmTimes = { ...prev.alarmTimes };
          if (enabled === undefined) delete alarmEnabled[visitId];
          else alarmEnabled[visitId] = enabled;
          if (times === undefined) delete alarmTimes[visitId];
          else alarmTimes[visitId] = times;
          return { ...prev, alarmEnabled, alarmTimes };
        });
      put({ enabled: local.enabled ?? before.enabled, times: local.times ?? before.times });
      const prescriptionId = prescriptionIdOf(visitId);
      if (!prescriptionId) return;
      try {
        put(fromServerAlarm(await updatePrescriptionAlarms(prescriptionId, body)));
      } catch (error) {
        put(before);
        throw error;
      }
    };

    return {
      /** 저장된 가이드, 최근 처방부터. childId를 주면 그 아이 것만 */
      guidesOf: (childId) => (childId ? allGuides.filter((g) => g.childId === childId) : allGuides),
      /** 처방(건강기록 id)별 복약 알림을 켰는지. 처음엔 모두 켜져 있어요. 서버 처방은 저장된 값이에요. */
      isAlarmOn,
      /** 알림을 켠 시각(ms). 이 시각 전에 지난 먹는 때는 알리지 않아요. 예시 처방처럼 기록이 없으면 null(제한 없음). */
      alarmSince: (visitId) => state.alarmSince[visitId] ?? null,
      /** 알림 켜기/끄기. 서버 처방은 저장하고, 저장에 실패하면 스위치를 되돌려요. */
      setAlarm: (visitId, on) => {
        if (on) setState((prev) => ({ ...prev, alarmSince: { ...prev.alarmSince, [visitId]: Date.now() } }));
        saveAlarm(visitId, { enabled: on }, { enabled: on }).catch(() => {});
      },
      /** 그 처방의 먹는 때 알림 시각 [시, 분]. 보호자가 바꾼 값이 없으면 기본 시각이에요. */
      alarmTimeOf,
      /**
       * times: { 아침: [8, 0], ... } — 바꾼 먹는 때만 넣어도 돼요. null이면 slots의 먹는 때를 기본 시각으로 되돌려요.
       * 서버 처방은 저장이 끝날 때까지 기다리고, 실패하면 서버 문구를 담은 오류를 던져요.
       */
      setAlarmTimes: (visitId, times, slots = Object.keys(times ?? {})) => {
        const next = times ?? Object.fromEntries(slots.map((slot) => [slot, SLOT_TIME[slot] ?? [9, 0]]));
        const body = { times: Object.fromEntries(Object.entries(next).map(([slot, time]) => [slot, hhmm(time)])) };
        return saveAlarm(visitId, { times: { ...state.alarmTimes[visitId], ...next } }, body);
      },
      /** 가이드 하나 */
      guideById: (id) => allGuides.find((g) => g.id === id) ?? null,
      /** 그날 먹일 약 + 먹였는지(given) + 체크 기록이 있는지(recorded — 없으면 '기록 없음') */
      dosesOn: (childId, date) =>
        scheduledOn(allCourses, childId, date).map((d) => ({ ...d, given: isGiven(d.key, d.course), recorded: isRecorded(d.key, d.course) })),
      /** dose는 dosesOn이 돌려준 항목 */
      toggleDose: (dose) => setGiven([dose], !dose.given),
      /** group은 groupBySlot 결과 하나 — 다 먹였으면 모두 되돌리고, 아니면 모두 먹인 것으로 */
      toggleSlot: (group) => setGiven(group.doses, !group.done),
      /**
       * 처방(건강기록 id) 하나의 복용 상태 — 홈·알림과 같은 기준이에요.
       * active: 그날이 복용 기간 안이면 그 일정, 아니면 null
       * ended: 복용 기간이 끝났는지. 일정이 없는 처방(필요시 약만 등)은 fallbackDate(처방일)가 지났는지로 봐요.
       */
      courseStatus: (visitId, fallbackDate, date = todayKey()) => {
        const course = courseOfVisit(visitId);
        if (!course) return { active: null, ended: Boolean(fallbackDate) && fallbackDate < date };
        return { active: inCourse(course, date) ? course : null, ended: date >= shiftDays(course.start, course.days) };
      },
      /** 지금 먹고 있는 처방(오늘이 일정 안에 있는 것) */
      activeCourse: (childId, date = todayKey()) =>
        allCourses.find((c) => c.childId === childId && date >= c.start && date < shiftDays(c.start, c.days)) ?? null,
      /** 아이의 건강기록, 최근 날짜부터 */
      visitsOf: (childId) =>
        allVisits.filter((v) => v.childId === childId).sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)),
      /**
       * 처방전 확인이 끝났을 때 — 병원기록과 복약 일정을 자동으로 남겨요. 같은 처방을 다시 올리면 덮어써요.
       * 서버에 올린 처방(prescriptionId)은 가이드를 서버가 만들어요. 그래서 여기서는 가이드를 짐작해 만들지 않고
       * 가이드가 오면 saveServerGuide로 넣어요. 예시 처방(서버 없음)만 약 목록으로 가이드를 만들어요.
       */
      recordPrescription: ({ prescriptionId, childId, date, hospital, title, meds }) => {
        const record = buildPrescriptionRecord({ prescriptionId, childId, date, hospital, title, meds });
        const { visit, course } = record;
        const guide = prescriptionId ? null : record.guide;
        const { id } = visit;
        setState((prev) => {
          const replaced = prev.visits.filter((v) => v.id === id || visitKey(v) === visitKey(visit)).map((v) => v.id);
          return {
            ...prev,
            visits: [visit, ...prev.visits.filter((v) => !replaced.includes(v.id))],
            courses: [...(course ? [course] : []), ...prev.courses.filter((c) => !replaced.includes(c.visitId))],
            guides: [...(guide ? [guide] : []), ...prev.guides.filter((g) => !replaced.includes(g.visitId) && g.visitId !== id)],
            // 새 처방의 알림은 가이드를 만든 지금부터 시작해요.
            alarmSince: { ...prev.alarmSince, [id]: Date.now() },
          };
        });
        return { visit, guide };
      },
      /**
       * 서버가 만든 가이드(명세 8번 응답)를 그 처방의 건강기록에 붙여요. 돌려주는 값은 가이드 id(g rx{번호})예요.
       * recordPrescription으로 건강기록을 먼저 남긴 다음에 불러요.
       */
      saveServerGuide: (prescriptionId, guideResponse) => {
        const visitId = `rx${prescriptionId}`;
        setState((prev) => {
          const visit = prev.visits.find((v) => v.id === visitId);
          if (!visit) return prev;
          const guide = guideFromServer(visit, guideResponse);
          return { ...prev, guides: [guide, ...prev.guides.filter((g) => g.id !== guide.id)] };
        });
        return `g${visitId}`;
      },
      /** 처방전 없이 다녀온 진료(예방접종, 검진 등)를 직접 남겨요. */
      addVisit: (visit) =>
        setState((prev) => ({ ...prev, visits: [{ id: `u${Date.now()}`, source: 'manual', ...visit }, ...prev.visits] })),
      removeVisit: (id) => setState((prev) => ({ ...prev, visits: prev.visits.filter((v) => v.id !== id) })),
      /**
       * 서버에 올린 처방을 지워요(9절 DELETE). 성공하면 그 처방의 건강기록·복약 일정·가이드를 화면에서도 지워요.
       * 이미 지워진 처방(404)도 지운 것으로 봐요. 그 밖의 실패는 PrescriptionRecordsError를 그대로 던져요.
       */
      deletePrescription: async (visit) => {
        try {
          await deletePrescription(visit.prescriptionId);
        } catch (error) {
          if (error.status !== 404) throw error;
        }
        setState((prev) => ({
          ...prev,
          visits: prev.visits.filter((v) => v.id !== visit.id),
          courses: prev.courses.filter((c) => c.visitId !== visit.id),
          guides: prev.guides.filter((g) => g.visitId !== visit.id),
          deletedPrescriptionIds: [...prev.deletedPrescriptionIds, visit.prescriptionId],
        }));
      },
      /** 아이를 삭제할 때 — 그 아이의 복약 체크·건강기록·복약 일정을 모두 지워요. */
      forgetChild: (childId) =>
        // ...prev로 알림 설정(alarmEnabled·alarmSince·alarmTimes)처럼 여기서 안 건드리는 값도 그대로 남겨요.
        // 빠뜨리면 알림 메뉴가 없는 값을 읽다가 앱 전체가 빈 화면이 돼요.
        setState((prev) => ({
          ...prev,
          doses: Object.fromEntries(Object.entries(prev.doses).filter(([key]) => !key.startsWith(`${childId}|`))),
          visits: prev.visits.filter((v) => v.childId !== childId),
          courses: prev.courses.filter((c) => c.childId !== childId),
          guides: prev.guides.filter((g) => g.childId !== childId),
          removedChildIds: [...prev.removedChildIds, childId],
        })),
    };
  }, [state, server]);

  return <RecordsContext.Provider value={value}>{children}</RecordsContext.Provider>;
}

export function useRecords() {
  const ctx = useContext(RecordsContext);
  if (!ctx) throw new Error('useRecords는 RecordsProvider 안에서만 쓸 수 있어요.');
  return ctx;
}
