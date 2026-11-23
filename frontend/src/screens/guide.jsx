import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/Button.jsx';
import { ChildSwitcher } from '../components/ui/misc.jsx';
import { AppShell, Header } from '../components/ui/layout.jsx';
import { AlarmCard, DangerSignals, Disclaimer, GuideTitle, HowTo, LifeTips, Schedule } from '../components/rx/guide.jsx';
import { guide, prescription as rx } from '../data/sample.js';
import { BackLink } from './confirm.jsx';

/**
 * S-05 복약 가이드
 * 모바일: 한 단 (제목 → 하루 먹는 때 → 위험 신호 → 복용법 → 생활 습관 → 알림 → 면책)
 * 데스크톱: 본문 672px + 오른쪽 단(위험 신호, 알림, 처방 다시 보기)
 */
export function GuideScreen({ go, back, onTab }) {
  const title = <GuideTitle childName="지우" disease={rx.disease} hospital={rx.hospital} date={rx.shortDate} large />;
  return (
    <AppShell tab="history" onTab={onTab} showTabs={false} width="wide"
      header={<Header title="" onBack={() => back('history')} right={<ChildSwitcher name="지우" />} className="lg:hidden" />}>
      <div className="flex flex-col gap-8 px-5 pb-10 pt-1 lg:gap-5 lg:px-0 lg:pb-[72px] lg:pt-8">
        <BackLink onClick={() => back('history')}>돌아가기</BackLink>
        <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:gap-14">
          <div className="flex w-full flex-col gap-8 lg:w-[672px] lg:shrink-0 lg:gap-9">
            {title}
            <Schedule schedule={guide.schedule} asNeeded={guide.asNeeded} />
            <div className="lg:hidden"><DangerSignals items={guide.danger} /></div>
            <HowTo items={guide.howTo} />
            <LifeTips items={guide.life} />
            <div className="lg:hidden"><AlarmCard /></div>
            <Disclaimer />
          </div>
          <aside className="hidden min-w-0 flex-1 flex-col gap-4 lg:sticky lg:top-[100px] lg:flex">
            <DangerSignals items={guide.danger} />
            <AlarmCard />
            <Button variant="secondary" className="w-full" onClick={() => go('confirm')}>처방 내용 다시 보기</Button>
          </aside>
        </div>
      </div>
    </AppShell>
  );
}

const Sk = ({ className }) => <div className={`animate-pulse rounded-md bg-sunk ${className}`} />;

/** S-05 만드는 중 — 실제 가이드와 같은 모양의 뼈대. 데모에서는 2.5초 뒤 가이드로 넘어가요 */
export function GuideLoadingScreen({ go, back, onTab }) {
  useEffect(() => {
    const t = setTimeout(() => go('guide', undefined, { replace: true }), 2500);
    return () => clearTimeout(t);
  }, [go]);
  return (
    <AppShell tab="history" onTab={onTab} showTabs={false} header={<Header title="" onBack={() => back('confirm')} />}>
      <div className="flex flex-1 flex-col gap-6 px-5 pb-8 pt-1 lg:px-0" aria-busy="true" aria-live="polite">
        <div className="flex flex-col gap-2">
          <h1 className="text-22 font-bold">가이드를 만들고 있어요</h1>
          <p className="text-15 text-muted">처방과 지우의 정보를 정리하는 중이에요. 10초쯤 걸릴 수 있어요.</p>
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
