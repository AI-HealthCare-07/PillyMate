import { useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/Button.jsx';
import { AppShell, Header } from '../components/ui/layout.jsx';
import { AlarmTimeModal } from '../components/rx/AlarmTimeModal.jsx';
import { AlarmBar, DangerSignals, Disclaimer, GuideSummary, HowTo, LifeTips, Schedule } from '../components/rx/guide.jsx';
import { getPrescriptionDraft, setPrescriptionDraft } from './fe2Draft.js';
import { createGuide, getGuide } from '../api/prescriptionFlow.js';
import { alarmSlots, hhmm, todayKey, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';
import { BackLink } from './confirm.jsx';

/**
 * S-05 복약 가이드 — 방금 만든 가이드(또는 가이드 탭에서 고른 가이드)를 그 아이 이름으로 보여 줘요.
 * 어떤 가이드인지는 이동할 때 넘긴 guideId → 처방 올리기 임시 데이터의 guideId 순서로 찾아요.
 * 맨 위 처방 정보·복약 알림 카드는 가이드 탭(/guides) 카드와 같은 컴포넌트예요. 알림 설정도 처방(visitId)별로 같이 써요.
 * 모바일: 한 단 (처방·알림 카드 → 하루 복약 일정 → 위험 신호 → 복용법 → 생활 습관 → 면책)
 * 데스크톱: 본문 672px + 오른쪽 단(위험 신호, 알림, 처방 다시 보기)
 */

/** 건강기록 id('rx305') → 서버 처방 id(305). 예시 기록('p…', 'v…')이면 null */
const prescriptionIdOf = (visitId) => (/^rx\d+$/.test(visitId ?? '') ? Number(visitId.slice(2)) : null);

/**
 * 화면 기록의 가이드(처방 숫자로 만든 것)에 서버 가이드(guide_content)를 덮어써요.
 * - 복용법·생활 습관·위험 신호·필요할 때 먹는 약: 서버(AI-2) 값
 * - 하루 복약 일정(schedule): 화면 기록 값 그대로 — 복약 달력·알림이 이 값을 써요
 * - 복용법 표의 숫자(dose·perDay·days·timing): 화면 기록 값 그대로, 설명(how·note)만 서버 값
 */
function withServerGuide(guide, server) {
  if (!server) return guide;
  const serverHowTo = server.howTo ?? [];
  const howTo = guide.howTo.length
    ? guide.howTo.map((item, i) => {
        const s = serverHowTo.find((h) => h.name === item.name) ?? serverHowTo[i];
        return s ? { ...item, how: s.how || item.how, note: s.note || item.note } : item;
      })
    : serverHowTo;
  return {
    ...guide,
    asNeeded: server.asNeeded || guide.asNeeded,
    howTo,
    life: server.life?.length ? server.life : guide.life,
    danger: server.danger?.length ? server.danger : guide.danger,
    summary: server.summary ?? guide.summary,
    serverStatus: server.status ?? null, // 'ok' | 'fallback'
  };
}

/** 서버 가이드 불러오기 — 방금 만든 것은 임시 데이터에서, 없으면(가이드 탭에서 연 경우 등) GET으로 */
function useServerGuide(prescriptionId) {
  const [server, setServer] = useState(() => {
    const draft = getPrescriptionDraft();
    return prescriptionId && draft?.prescriptionId === prescriptionId ? draft.serverGuide ?? null : null;
  });
  useEffect(() => {
    if (!prescriptionId || server) return undefined;
    let cancelled = false;
    getGuide(prescriptionId)
      .then((res) => !cancelled && setServer(res.guide_content))
      .catch(() => {}); // 404(아직 없음)·연결 실패면 화면 기록 가이드를 그대로 보여요
    return () => {
      cancelled = true;
    };
  }, [prescriptionId, server]);
  return server;
}

export function GuideScreen({ go, back, onTab }) {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { guideById, isAlarmOn, setAlarm, alarmTimeOf, activeCourse, visitsOf } = useRecords();
  const [editingTimes, setEditingTimes] = useState(false);
  // 휴대폰·브라우저의 뒤로가기도 홈으로 보내요. 그대로 두면 처방 확인 화면으로 돌아가요.
  useEffect(() => {
    const onPop = () => navigate('/home', { replace: true });
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [navigate]);
  const { childList } = useSelectedChild();
  const localGuide = guideById(state?.guideId ?? getPrescriptionDraft()?.guideId);
  const serverGuide = useServerGuide(prescriptionIdOf(localGuide?.visitId));
  const guide = localGuide && withServerGuide(localGuide, serverGuide);
  const child = guide && childList.find((c) => c.id === guide.childId);
  // 찾을 가이드가 없으면(주소로 바로 들어온 경우 등) 가이드 목록으로 보내요.
  if (!guide || !child) return <Navigate to="/guides" replace />;

  const course = activeCourse(guide.childId);
  const active = course?.visitId === guide.visitId ? course : null;
  const ended = !active && guide.date < todayKey();
  const slots = alarmSlots(guide.schedule);
  const alarmOn = isAlarmOn(guide.visitId);
  const timeOf = (slot) => alarmTimeOf(guide.visitId, slot);
  const visitMeds = visitsOf(guide.childId).find((v) => v.id === guide.visitId)?.meds;
  // 처방 정보 + 복약 알림 — /guides의 가이드 카드 머리와 같은 모양(펼치기 버튼만 없어요)
  const summary = (
    <article className="overflow-hidden rounded-xl border border-line bg-surface">
      <div className="flex min-h-[72px] items-center gap-3.5 px-4 py-4 lg:gap-4 lg:px-6 lg:py-5">
        <GuideSummary guide={guide} child={child} active={active} ended={ended} titleAs="h1" />
      </div>
      {slots.length > 0 && !ended && (
        <AlarmBar
          on={alarmOn}
          onChange={(on) => setAlarm(guide.visitId, on)}
          times={slots.map((slot) => hhmm(timeOf(slot)))}
          onEditTimes={() => setEditingTimes(true)}
          label={`${child.name} ${guide.title}`}
        />
      )}
    </article>
  );
  const danger = guide.danger.length > 0 && <DangerSignals items={guide.danger} />;
  // 가이드에서 뒤로 가면 항상 홈으로 가요(만드는 중·확인 화면으로 되돌아가지 않게).
  const toHome = () => go('home', undefined, { replace: true });
  return (
    <AppShell tab="guides" onTab={onTab} width="wide"
      header={<Header title="" onBack={toHome} className="lg:hidden" />}>
      <div className="flex flex-col gap-8 px-5 pb-10 pt-1 lg:gap-4 lg:px-0 lg:pb-[72px] lg:pt-6">
        <BackLink onClick={toHome}>홈으로</BackLink>
        <div className="flex flex-col gap-8 lg:grid lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start lg:gap-12 xl:grid-cols-[minmax(0,680px)_320px] xl:gap-16">
          <div className="flex w-full min-w-0 flex-col gap-8 lg:gap-10">
            {summary}
            {guide.schedule.length > 0 && <Schedule schedule={guide.schedule} asNeeded={guide.asNeeded} timeOf={timeOf} />}
            {danger && <div className="lg:hidden">{danger}</div>}
            {guide.howTo.length > 0 && <HowTo items={guide.howTo} schedule={guide.schedule} asNeeded={guide.asNeeded} visitMeds={visitMeds} />}
            {guide.life.length > 0 && <LifeTips items={guide.life} />}
            <Disclaimer />
          </div>
          <aside className="hidden min-w-0 flex-col gap-4 lg:sticky lg:top-[88px] lg:flex">
            {danger}
            <Button variant="secondary" className="w-full" onClick={() => go('guides')}>저장된 가이드 모두 보기</Button>
          </aside>
        </div>
      </div>
      <AlarmTimeModal
        open={editingTimes}
        onClose={() => setEditingTimes(false)}
        visitId={guide.visitId}
        slots={slots}
        title={`${child.name} · ${guide.title}`}
      />
    </AppShell>
  );
}

const Sk = ({ className }) => <div className={`animate-pulse rounded-md bg-sunk ${className}`} />;

/**
 * S-05 만드는 중 — 실제 가이드와 같은 모양의 뼈대.
 * 서버 처방이면 가이드 생성 API(POST /prescriptions/{id}/guide, 약 20초)를 부르고, 끝나면 가이드로 넘어가요.
 * 예시 데이터(처방 id 없음)는 2.5초 뒤 넘어가요.
 */
export function GuideLoadingScreen({ go, back, onTab }) {
  const draft = getPrescriptionDraft();
  const { childList } = useSelectedChild();
  const childName = childList.find((c) => c.id === draft?.childId)?.name ?? '아이';
  const prescriptionId = draft?.prescriptionId;
  const guideId = draft?.guideId;
  useEffect(() => {
    const toGuide = () => go('guide', { guideId }, { replace: true });
    if (!prescriptionId) {
      const t = setTimeout(toGuide, 2500);
      return () => clearTimeout(t);
    }
    let cancelled = false;
    // 서버는 같은 처방으로 다시 불러도 새로 만들지 않고 기존 가이드를 돌려줘요(개발 모드에서 두 번 불려도 안전).
    createGuide(prescriptionId)
      .then((res) => {
        if (cancelled) return;
        setPrescriptionDraft({ ...getPrescriptionDraft(), serverGuide: res.guide_content });
        toGuide();
      })
      .catch(() => {
        if (!cancelled) go('guide-error', undefined, { replace: true });
      });
    return () => {
      cancelled = true;
    };
  }, [go, prescriptionId, guideId]);
  return (
    <AppShell tab="history" onTab={onTab} showTabs={false} width="reading" header={<Header title="" onBack={() => back('confirm')} />}>
      <div className="flex flex-1 flex-col gap-8 px-5 pb-8 pt-1 lg:px-0 lg:pb-12 lg:pt-4" aria-busy="true" aria-live="polite">
        <div className="flex flex-col gap-2">
          <h1 className="text-22 font-bold lg:text-28">가이드를 만들고 있어요</h1>
          <p className="text-15 text-muted">처방과 {childName}의 정보를 정리하는 중이에요. 20초쯤 걸릴 수 있어요. 화면을 닫지 말고 기다려 주세요.</p>
        </div>
        <div className="flex flex-col gap-3">
          <Sk className="h-[18px] w-[120px]" />
          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-4">{[0, 1, 2, 3].map((i) => <Sk key={i} className="h-12 rounded-lg sm:h-24" />)}</div>
          <Sk className="h-12 rounded-lg" />
        </div>
        <div className="flex flex-col gap-2.5">
          <Sk className="h-[18px] w-[140px]" />
          {['w-full', 'w-[90%]', 'w-[75%]', 'w-full', 'w-[60%]'].map((w, i) => <Sk key={i} className={`h-3 ${w}`} />)}
        </div>
        <Sk className="h-[120px] rounded-xl" />
      </div>
    </AppShell>
  );
}

/** S-05 실패 — 무엇이 실패했는지, 데이터는 안전한지, 다음에 할 일 */
export function GuideErrorScreen({ go, back, onTab }) {
  const actions = {
    mobile: (
      <>
        <Button className="w-full lg:w-auto lg:min-w-[200px]" onClick={() => go('guide-loading')}>가이드 다시 만들기</Button>
        <Button variant="secondary" className="w-full lg:w-auto lg:min-w-[200px]" onClick={() => go('confirm')}>처방 내용 다시 보기</Button>
      </>
    ),
  };
  return (
    <AppShell tab="history" onTab={onTab} showTabs={false} header={<Header title="" onBack={() => back('confirm')} />} actions={actions}>
      <div role="alert" className="flex flex-1 flex-col items-center justify-center gap-4 px-7 pb-10 text-center lg:items-start lg:justify-start lg:px-0 lg:pb-12 lg:pt-10 lg:text-left">
        <span className="mb-1 flex size-14 items-center justify-center rounded-pill bg-danger-soft text-danger">
          <AlertTriangle size={28} strokeWidth={2} aria-hidden />
        </span>
        <h1 className="text-22 font-bold lg:text-28">가이드를 만들지 못했어요</h1>
        <p className="max-w-[420px] text-15 text-muted">응답이 너무 오래 걸려 중간에 멈췄어요. 확인한 처방 내용은 저장돼 있으니 다시 만들면 돼요.</p>
      </div>
    </AppShell>
  );
}
