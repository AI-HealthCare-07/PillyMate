import { useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/Button.jsx';
import { AppShell, Header } from '../components/ui/layout.jsx';
import { AlarmTimeModal } from '../components/rx/AlarmTimeModal.jsx';
import { AlarmBar, DangerSignals, Disclaimer, GuideSummary, HowTo, LifeTips, Schedule } from '../components/rx/guide.jsx';
import { createGuide } from '../api/prescriptionGuide.js';
import { getPrescriptionDraft, setPrescriptionDraft } from './fe2Draft.js';
import { alarmSlots, hhmm, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';
import { BackLink } from './confirm.jsx';

/**
 * S-05 복약 가이드 — 방금 만든 가이드(또는 가이드 탭에서 고른 가이드)를 그 아이 이름으로 보여 줘요.
 * 어떤 가이드인지는 이동할 때 넘긴 guideId → 처방 올리기 임시 데이터의 guideId 순서로 찾아요.
 * 맨 위 처방 정보·복약 알림 카드는 가이드 탭(/guides) 카드와 같은 컴포넌트예요. 알림 설정도 처방(visitId)별로 같이 써요.
 * 모바일: 한 단 (처방·알림 카드 → 하루 복약 일정 → 위험 신호 → 복용법 → 생활 습관 → 면책)
 * 데스크톱: 본문 672px + 오른쪽 단(위험 신호, 알림, 처방 다시 보기)
 */

export function GuideScreen({ go, back, onTab }) {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { guideById, isAlarmOn, setAlarm, alarmTimeOf, courseStatus, visitsOf } = useRecords();
  const [editingTimes, setEditingTimes] = useState(false);
  // 휴대폰·브라우저의 뒤로가기도 홈으로 보내요. 그대로 두면 처방 확인 화면으로 돌아가요.
  useEffect(() => {
    const onPop = () => navigate('/home', { replace: true });
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [navigate]);
  const { childList } = useSelectedChild();
  const guide = guideById(state?.guideId ?? getPrescriptionDraft()?.guideId);
  const child = guide && childList.find((c) => c.id === guide.childId);
  // 찾을 가이드가 없으면(주소로 바로 들어온 경우 등) 가이드 목록으로 보내요.
  if (!guide || !child) return <Navigate to="/guides" replace />;

  // 이 처방의 복용 기간으로 판단해요(홈 '오늘 먹을 약'·알림과 같은 기준). 같은 아이가 처방을 여러 개 먹어도 각각 맞게 보여요.
  const { active, ended } = courseStatus(guide.visitId, guide.date);
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
 * 서버에 올린 처방은 가이드 만들기 API(8번)를 불러서, 받은 가이드를 저장하고 가이드 화면으로 가요. 실패하면 실패 화면으로 가요.
 * 예시 처방(서버 없음)은 확인 화면에서 만든 가이드로 2.5초 뒤 넘어가요.
 */
export function GuideLoadingScreen({ go, back, onTab }) {
  const draft = getPrescriptionDraft();
  const { saveServerGuide } = useRecords();
  const { childList } = useSelectedChild();
  const childName = childList.find((c) => c.id === draft?.childId)?.name ?? '아이';
  const prescriptionId = draft?.prescriptionId;
  useEffect(() => {
    if (!prescriptionId) {
      const t = setTimeout(() => go('guide', { guideId: draft?.guideId }, { replace: true }), 2500);
      return () => clearTimeout(t);
    }
    let cancelled = false;
    createGuide(prescriptionId)
      .then((response) => {
        if (cancelled) return;
        const guideId = saveServerGuide(prescriptionId, response);
        setPrescriptionDraft({ ...getPrescriptionDraft(), guideId });
        go('guide', { guideId }, { replace: true });
      })
      .catch(() => {
        if (!cancelled) go('guide-error', undefined, { replace: true });
      });
    return () => {
      cancelled = true;
    };
    // 화면에 들어올 때 한 번만 만들어요. 같은 처방을 두 번 부르면 createGuide가 한 번으로 합쳐요.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prescriptionId]);
  return (
    <AppShell tab="history" onTab={onTab} showTabs={false} width="reading" header={<Header title="" onBack={() => back('confirm')} />}>
      <div className="flex flex-1 flex-col gap-8 px-5 pb-8 pt-1 lg:px-0 lg:pb-12 lg:pt-4" aria-busy="true" aria-live="polite">
        <div className="flex flex-col gap-2">
          <h1 className="text-22 font-bold lg:text-28">가이드를 만들고 있어요</h1>
          <p className="text-15 text-muted">처방과 {childName}의 정보를 정리하는 중이에요. 20초쯤 걸릴 수 있어요.</p>
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
        <p className="max-w-[420px] text-15 text-muted">잠시 문제가 생겨 가이드를 만들지 못했어요. 확인한 처방 내용은 저장돼 있으니 다시 만들면 돼요.</p>
      </div>
    </AppShell>
  );
}
