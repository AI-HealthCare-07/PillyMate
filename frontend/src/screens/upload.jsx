import { useEffect, useState } from 'react';
import { Camera, Check, Circle, ImageIcon, RefreshCw } from 'lucide-react';
import { Button, SmallButton } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Panel, SectionLabel, Segmented } from '../components/ui/misc.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { RxPaper } from '../components/rx/RxPaper.jsx';

/** S-03 처방 올리기 (사진을 고른 상태) */
export function UploadScreen({ go, onTab }) {
  const [child, setChild] = useState('c1');
  const read = <Button className="w-full lg:w-auto lg:min-w-[200px]" onClick={() => go('reading')}>처방 내용 읽기</Button>;
  return (
    <AppShell tab="upload" onTab={onTab} header={<Header title="처방 올리기" />} actions={{ mobile: read }}>
      <Body className="gap-[22px] pt-1">
        <div className="flex flex-col gap-2.5">
          <SectionLabel>누구의 약인가요?</SectionLabel>
          <Segmented label="아이 선택" value={child} onChange={setChild} options={[{ value: 'c1', label: '지우' }, { value: 'c2', label: '서준' }]} />
        </div>
        <div className="flex flex-col gap-2.5">
          <SectionLabel>처방전 사진</SectionLabel>
          <Panel className="flex items-center gap-3.5 p-3">
            <RxPaper width={72} marks={[[140, 186, 30]]} />
            <div className="flex flex-1 flex-col gap-2.5">
              <div className="flex flex-col gap-0.5">
                <p className="text-16 font-semibold">처방전 1장</p>
                <p className="text-13 text-muted">2.4MB, 방금 찍음</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <SmallButton icon={Camera}>다시 찍기</SmallButton>
                <SmallButton icon={ImageIcon}>앨범</SmallButton>
              </div>
            </div>
          </Panel>
        </div>
        <Field label="병명 (아는 경우)" placeholder="예: 중이염" />
        <Field label="특이사항" multiline placeholder="예: 어제부터 39도 열이 나요" helper="적어 주시면 가이드에 반영돼요." />
      </Body>
    </AppShell>
  );
}

const STEPS = [
  { label: '사진 올리기', state: 'done' },
  { label: '글자 읽기', state: 'active' },
  { label: '이름, 주민번호 가리기', state: 'next' },
];

/** S-03 읽는 중 — 데모에서는 2.5초 뒤 확인 화면으로 넘어가요 */
export function ReadingScreen({ go, onTab }) {
  useEffect(() => {
    const t = setTimeout(() => go('confirm'), 2500);
    return () => clearTimeout(t);
  }, [go]);
  const cancel = <Button variant="secondary" className="w-full lg:w-auto lg:min-w-[160px]" onClick={() => go('upload')}>취소</Button>;
  return (
    <AppShell tab="upload" onTab={onTab} showTabs={false} header={<Header title="처방 읽는 중" onBack={() => go('upload')} />} actions={{ mobile: cancel }}>
      <div className="flex flex-1 flex-col items-center gap-7 p-6 lg:px-0" aria-live="polite">
        <RxPaper width={200} marks={[[140, 186, 30], [232, 206, 30]]} scanning />
        <div className="flex flex-col gap-2 text-center">
          <h2 className="text-22 font-bold">처방전을 읽고 있어요</h2>
          <p className="text-15 text-muted">보통 몇 초면 끝나요. 이 화면에서 잠시만 기다려 주세요.</p>
        </div>
        <Panel as="ol" className="w-full" aria-label="진행 단계">
          {STEPS.map((s, j) => (
            <li key={s.label} className={`flex items-center gap-3 px-4 py-3.5 ${j ? 'border-t border-line' : ''}`}>
              {s.state === 'done' && <Check size={22} strokeWidth={2} className="text-brand" aria-hidden />}
              {s.state === 'active' && <RefreshCw size={22} strokeWidth={2} className="animate-spin text-brand [animation-duration:2s]" aria-hidden />}
              {s.state === 'next' && <Circle size={22} strokeWidth={2} className="text-faint" aria-hidden />}
              <span className={`flex-1 text-15 ${s.state === 'active' ? 'font-semibold' : 'font-medium'} ${s.state === 'next' ? 'text-muted' : ''}`}>{s.label}</span>
              <span className={`text-13 ${s.state === 'active' ? 'font-semibold text-brand' : 'text-muted'}`}>
                {s.state === 'done' ? '끝났어요' : s.state === 'active' ? '읽는 중' : '다음 순서'}
              </span>
            </li>
          ))}
        </Panel>
      </div>
    </AppShell>
  );
}
