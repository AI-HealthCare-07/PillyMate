import { useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/Button.jsx';
import { AppShell, Header } from '../components/ui/layout.jsx';
import { AlarmTimeModal } from '../components/rx/AlarmTimeModal.jsx';
import { AlarmCard, DangerSignals, Disclaimer, GuideTitle, HowTo, LifeTips, Schedule } from '../components/rx/guide.jsx';
import { getPrescriptionDraft } from './fe2Draft.js';
import { alarmSlots, dateParts, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';
import { BackLink } from './confirm.jsx';

/**
 * S-05 복약 가이드 — 방금 만든 가이드(또는 가이드 탭에서 고른 가이드)를 그 아이 이름으로 보여 줘요.
 * 어떤 가이드인지는 이동할 때 넘긴 guideId → 처방 올리기 임시 데이터의 guideId 순서로 찾아요.
 * 모바일: 한 단 (제목 → 하루 먹는 때 → 위험 신호 → 복용법 → 생활 습관 → 알림 → 면책)
 * 데스크톱: 본문 672px + 오른쪽 단(위험 신호, 알림, 처방 다시 보기)
 */

// 복약 가이드 생성 및 조회 API
async function requestGuide(prescriptionId, method = 'POST') {
  const token = sessionStorage.getItem('access_token');

  if (!token) {
    throw new Error('로그인이 필요합니다.');
  }

  if (!prescriptionId) {
    throw new Error('처방전 ID가 없습니다.');
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);

  try {
    const response = await fetch(
      `/api/v1/prescriptions/${encodeURIComponent(prescriptionId)}/guide`,
      {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      }
    );

    if (response.status === 401) {
      sessionStorage.removeItem('access_token');
      throw new Error('로그인이 만료되었습니다.');
    }

    if (!response.ok) {
      throw new Error('복약 가이드 요청에 실패했습니다.');
    }

    const data = await response.json();
    return data;

  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('응답 시간이 초과되었습니다.');
    }

    throw error;

  } finally {
    clearTimeout(timeout);
  }
}

export function GuideScreen({ go, back, onTab }) {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { guideById, isAlarmOn, setAlarm, alarmTimeOf } = useRecords();
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

  const p = dateParts(guide.date);
  const title = <GuideTitle childName={child.name} disease={guide.title} hospital={guide.hospital} date={`${p.month}월 ${p.day}일`} large />;
  const danger = guide.danger.length > 0 && <DangerSignals items={guide.danger} />;
  const alarm = (
    <AlarmCard
      on={isAlarmOn(guide.visitId)}
      onChange={(on) => setAlarm(guide.visitId, on)}
      slots={alarmSlots(guide.schedule)}
      timeOf={(slot) => alarmTimeOf(guide.visitId, slot)}
      onEditTimes={() => setEditingTimes(true)}
    />
  );
  // 가이드에서 뒤로 가면 항상 홈으로 가요(만드는 중·확인 화면으로 되돌아가지 않게).
  const toHome = () => go('home', undefined, { replace: true });
  return (
    <AppShell tab="guides" onTab={onTab} width="wide"
      header={<Header title="" onBack={toHome} className="lg:hidden" />}>
      <div className="flex flex-col gap-8 px-5 pb-10 pt-1 lg:gap-5 lg:px-0 lg:pb-[72px] lg:pt-8">
        <BackLink onClick={toHome}>홈으로</BackLink>
        <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:gap-14">
          <div className="flex w-full flex-col gap-8 lg:w-[672px] lg:shrink-0 lg:gap-9">
            {title}
            {guide.schedule.length > 0 && <Schedule schedule={guide.schedule} asNeeded={guide.asNeeded} />}
            {danger && <div className="lg:hidden">{danger}</div>}
            {guide.howTo.length > 0 && <HowTo items={guide.howTo} />}
            {guide.life.length > 0 && <LifeTips items={guide.life} />}
            <div className="lg:hidden">{alarm}</div>
            <Disclaimer />
          </div>
          <aside className="hidden min-w-0 flex-1 flex-col gap-4 lg:sticky lg:top-[100px] lg:flex">
            {danger}
            {alarm}
            <Button variant="secondary" className="w-full" onClick={() => go('guides')}>저장된 가이드 모두 보기</Button>
          </aside>
        </div>
      </div>
      <AlarmTimeModal
        open={editingTimes}
        onClose={() => setEditingTimes(false)}
        visitId={guide.visitId}
        slots={alarmSlots(guide.schedule)}
        title={`${child.name} · ${guide.title}`}
      />
    </AppShell>
  );
}

const Sk = ({ className }) => <div className={`animate-pulse rounded-md bg-sunk ${className}`} />;

/** S-05 만드는 중 — 실제 가이드와 같은 모양의 뼈대. 데모에서는 2.5초 뒤 가이드로 넘어가요 */
export function GuideLoadingScreen({ go, back, onTab }) {
  const draft = getPrescriptionDraft();
  const { childList } = useSelectedChild();
  const childName = childList.find((c) => c.id === draft?.childId)?.name ?? '아이';
  useEffect(() => {
    const t = setTimeout(() => go('guide', { guideId: draft?.guideId }, { replace: true }), 2500);
    return () => clearTimeout(t);
  }, [go, draft?.guideId]);
  return (
    <AppShell tab="history" onTab={onTab} showTabs={false} header={<Header title="" onBack={() => back('confirm')} />}>
      <div className="flex flex-1 flex-col gap-6 px-5 pb-8 pt-1 lg:px-0" aria-busy="true" aria-live="polite">
        <div className="flex flex-col gap-2">
          <h1 className="text-22 font-bold">가이드를 만들고 있어요</h1>
          <p className="text-15 text-muted">처방과 {childName}의 정보를 정리하는 중이에요. 10초쯤 걸릴 수 있어요.</p>
        </div>
        <div className="flex flex-col gap-3">
          <Sk className="h-[18px] w-[120px]" />
          <div className="grid grid-cols-4 gap-1.5">{[0, 1, 2, 3].map((i) => <Sk key={i} className="h-24 rounded-lg" />)}</div>
          <Sk className="h-12 rounded-lg" />
        </div>
        <div className="flex flex-col gap-2.5">
          <Sk className="h-[18px] w-[140px]" />
          {['w-full', 'w-[90%]', 'w-[75%]', 'w-full', 'w-[60%]'].map((w, i) => <Sk key={i} className={`h-3 ${w}`} />)}
        </div>
        <Sk className="h-[140px] rounded-xl" />
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
      <div role="alert" className="flex flex-1 flex-col items-center justify-center gap-4 px-7 pb-10 text-center lg:px-0">
        <span className="flex size-16 items-center justify-center rounded-full bg-danger-soft text-danger">
          <AlertTriangle size={28} strokeWidth={2} aria-hidden />
        </span>
        <h1 className="text-22 font-bold">가이드를 만들지 못했어요</h1>
        <p className="text-15 text-muted">응답이 너무 오래 걸려 중간에 멈췄어요. 확인한 처방 내용은 저장돼 있으니 다시 만들면 돼요.</p>
      </div>
    </AppShell>
  );
}
