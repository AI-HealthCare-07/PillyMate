import { Camera, ChevronLeft, Eye } from 'lucide-react';
import { Button, SmallButton } from '../components/ui/Button.jsx';
import { Panel } from '../components/ui/misc.jsx';
import { AppShell, Header } from '../components/ui/layout.jsx';
import { RxPaper } from '../components/rx/RxPaper.jsx';
import { LowConfidenceBanner } from '../components/rx/Highlight.jsx';
import { MedList, MedTable } from '../components/rx/meds.jsx';
import { meds, prescription as rx } from '../data/sample.js';

const MARKS = [[140, 186, 30], [190, 226, 22]];
const lowCount = meds.reduce((n, m) => n + ['dose', 'perDay', 'days', 'timing'].filter((k) => m[k].low).length, 0);

export function BackLink({ children, onClick }) {
  return (
    <button type="button" onClick={onClick} className="hidden items-center gap-1 self-start py-2 pr-2 text-14 font-medium text-muted hover:text-ink lg:inline-flex">
      <ChevronLeft size={18} aria-hidden />
      {children}
    </button>
  );
}

/**
 * S-04 처방 내용 확인
 * 모바일: 한 단 (원본 요약 → 약 목록) + 아래 고정 버튼
 * 데스크톱: 왼쪽 420px 원본 사진, 오른쪽 약 표 + 버튼
 */
export function ConfirmScreen({ go, onTab }) {
  const make = () => go('guide-loading');
  const retake = () => go('upload');
  const actions = {
    mobile: (
      <>
        <Button className="w-full" onClick={make}>확인했어요, 가이드 만들기</Button>
        <Button variant="secondary" className="w-full" onClick={retake}>다시 찍기</Button>
      </>
    ),
    desktop: null,
  };
  return (
    <AppShell tab="upload" onTab={onTab} showTabs={false} width="wide" actions={actions}
      header={<Header title="처방 내용 확인" onBack={retake} className="lg:hidden" />}>
      <div className="flex flex-col gap-5 px-5 pb-7 pt-1 lg:gap-5 lg:px-0 lg:pb-16 lg:pt-8">
        <BackLink onClick={retake}>처방 올리기로 돌아가기</BackLink>
        <h2 className="text-22 font-bold lg:text-28">
          읽은 내용이 처방전과<br className="lg:hidden" /> 같은지 확인해 주세요
        </h2>

        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:gap-10">
          {/* 데스크톱 원본 */}
          <div className="hidden w-[420px] shrink-0 flex-col gap-3 lg:sticky lg:top-[100px] lg:flex">
            <RxPaper width={420} marks={MARKS} />
            <div className="flex gap-2">
              <SmallButton icon={Eye}>크게 보기</SmallButton>
              <SmallButton icon={Camera} onClick={retake}>다시 찍기</SmallButton>
            </div>
          </div>

          <div className="flex min-w-0 flex-1 flex-col gap-5">
            <LowConfidenceBanner count={lowCount} />

            {/* 모바일 원본 요약 */}
            <Panel className="flex items-center gap-3 p-3 lg:hidden">
              <RxPaper width={54} marks={MARKS} />
              <div className="flex flex-1 flex-col gap-0.5">
                <p className="text-15 font-semibold">{rx.hospital}</p>
                <p className="text-13 text-muted">{rx.shortDate} 처방, 사진 1장</p>
              </div>
              <SmallButton icon={Eye}>원본</SmallButton>
            </Panel>

            {/* 데스크톱 메타 */}
            <dl className="hidden gap-10 lg:flex">
              {[['병원', rx.hospital], ['처방일', rx.date], ['아이', '지우, 만 4세']].map(([k, v]) => (
                <div key={k} className="flex flex-col gap-0.5">
                  <dt className="text-13 text-muted">{k}</dt>
                  <dd className="text-16 font-medium">{v}</dd>
                </div>
              ))}
            </dl>

            <h3 className="text-18 font-bold">약 {meds.length}개</h3>
            <div className="lg:hidden"><MedList meds={meds} /></div>
            <div className="hidden lg:block"><MedTable meds={meds} /></div>

            <div className="hidden justify-end gap-3 lg:flex">
              <Button variant="secondary" className="w-[140px]" onClick={retake}>다시 찍기</Button>
              <Button className="w-[260px]" onClick={make}>확인했어요, 가이드 만들기</Button>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
