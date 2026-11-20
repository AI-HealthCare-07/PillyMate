import { useEffect, useRef, useState } from 'react';
import { Camera, Check, Circle, ImageIcon, RefreshCw } from 'lucide-react';
import { Button, SmallButton } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Panel, SectionLabel, Segmented } from '../components/ui/misc.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { RxPaper } from '../components/rx/RxPaper.jsx';
import { children as sampleChildren } from '../data/sample.js';
import { getPrescriptionDraft, setPrescriptionDraft } from './fe2Draft.js';

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/** S-03 처방 올리기 — 파일 선택/검증/미리보기는 실제 동작합니다. */
export function UploadScreen({ go, onTab }) {
  const previous = getPrescriptionDraft();
  const [child, setChild] = useState(previous?.childId ?? sampleChildren[0]?.id ?? '');
  const [disease, setDisease] = useState(previous?.disease ?? '');
  const [note, setNote] = useState(previous?.note ?? '');
  const [file, setFile] = useState(previous?.file ?? null);
  const [previewUrl, setPreviewUrl] = useState(previous?.previewUrl ?? '');
  const [error, setError] = useState('');
  const fileInput = useRef(null);
  const cameraInput = useRef(null);

  const chooseFile = (event) => {
    const selected = event.target.files?.[0];
    event.target.value = '';
    if (!selected) return;
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setError('JPG, PNG, WEBP 사진만 올릴 수 있어요.');
      return;
    }
    if (selected.size > MAX_IMAGE_BYTES) {
      setError('사진은 10MB 이하로 선택해 주세요.');
      return;
    }
    if (!selected.size) {
      setError('비어 있는 파일은 올릴 수 없어요.');
      return;
    }
    const url = URL.createObjectURL(selected);
    setPrescriptionDraft({ childId: child, disease, note, file: selected, previewUrl: url, status: 'selected', guideReady: false });
    setFile(selected);
    setPreviewUrl(url);
    setError('');
  };

  const startReading = () => {
    if (!file || !previewUrl) {
      setError('처방전 사진을 먼저 선택해 주세요.');
      return;
    }
    if (!child) {
      setError('아이를 먼저 선택해 주세요.');
      return;
    }
    setPrescriptionDraft({ childId: child, disease: disease.trim(), note: note.trim(), file, previewUrl, status: 'selected', guideReady: false });
    go('reading');
  };
  const read = <Button className="w-full lg:w-auto lg:min-w-[200px]" onClick={startReading}>처방 내용 읽기</Button>;
  return (
    <AppShell tab="upload" onTab={onTab} header={<Header title="처방 올리기" onBack={() => go('children')} />} actions={{ mobile: read, desktop: null }}>
      <Body className="gap-[22px] pt-1">
        <div className="flex flex-col gap-2.5">
          <SectionLabel>누구의 약인가요?</SectionLabel>
          <Segmented label="아이 선택" value={child} onChange={setChild} options={sampleChildren.map((c) => ({ value: c.id, label: c.name }))} />
          {/* TODO(API): FE-1의 실제 아이 목록 조회 응답으로 교체. */}
        </div>
        <div className="flex flex-col gap-2.5">
          <SectionLabel>처방전 사진</SectionLabel>
          <Panel className="flex items-center gap-3.5 p-3">
            {previewUrl ? (
              <img src={previewUrl} alt="선택한 처방전 미리보기" className="h-24 w-[72px] shrink-0 rounded-md border border-line object-cover" />
            ) : (
              <RxPaper width={72} marks={[[140, 186, 30]]} />
            )}
            <div className="flex flex-1 flex-col gap-2.5">
              <div className="flex flex-col gap-0.5">
                <p className="text-16 font-semibold">{file ? file.name : '처방전 사진을 선택해 주세요'}</p>
                <p className="text-13 text-muted">{file ? `${(file.size / 1024 / 1024).toFixed(2)}MB` : 'JPG, PNG, WEBP · 최대 10MB'}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <SmallButton icon={Camera} onClick={() => cameraInput.current?.click()}>사진 찍기</SmallButton>
                <SmallButton icon={ImageIcon} onClick={() => fileInput.current?.click()}>앨범/파일</SmallButton>
              </div>
            </div>
          </Panel>
          <input ref={cameraInput} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={chooseFile} aria-label="카메라로 처방전 촬영" />
          <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={chooseFile} aria-label="처방전 이미지 선택" />
          {error && <p role="alert" className="text-13 text-danger">{error}</p>}
        </div>
        <Field label="병명 (아는 경우)" placeholder="예: 중이염" value={disease} onChange={(e) => setDisease(e.target.value)} />
        <Field label="특이사항" multiline placeholder="예: 어제부터 39도 열이 나요" helper="적어 주시면 가이드에 반영돼요." value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="hidden justify-end lg:flex">{read}</div>
      </Body>
    </AppShell>
  );
}

const STEPS = [
  { label: '사진 올리기', state: 'done' },
  { label: '글자 읽기', state: 'active' },
  { label: '이름, 주민번호 가리기', state: 'next' },
];

/** S-03 읽는 중 — API 연결 전 명시적 데모 동작 */
export function ReadingScreen({ go, onTab }) {
  const draft = getPrescriptionDraft();
  useEffect(() => {
    if (!draft?.file) { go('upload'); return undefined; }
    // TODO(API): BE-2 처방 이미지 업로드 + OCR 동기 API를 호출하고
    // 성공 응답의 약 목록/처방 ID를 setPrescriptionDraft에 저장한 뒤 confirm으로 이동.
    // 실패 시 이 화면에서 오류/재시도를 표시하고 자동으로 넘어가지 않도록 변경.
    // 현재는 화면 흐름 점검용 데모이며 실제 OCR은 수행하지 않습니다.
    const timer = setTimeout(() => {
      setPrescriptionDraft({ ...draft, status: 'mock-ocr' });
      go('confirm');
    }, 2500);
    return () => clearTimeout(timer);
  }, [go]);
  const cancel = <Button variant="secondary" className="w-full lg:w-auto lg:min-w-[160px]" onClick={() => go('upload')}>취소</Button>;
  return (
    <AppShell tab="upload" onTab={onTab} showTabs={false} header={<Header title="처방 읽는 중" onBack={() => go('upload')} />} actions={{ mobile: cancel }}>
      <div className="flex flex-1 flex-col items-center gap-7 p-6 lg:px-0" aria-live="polite">
        <RxPaper width={200} marks={[[140, 186, 30], [232, 206, 30]]} scanning />
        <div className="flex flex-col gap-2 text-center">
          <h2 className="text-22 font-bold">처방전을 읽고 있어요</h2>
          <p className="text-15 text-muted">현재는 화면 확인용 데모입니다. 실제 OCR은 API 연결 후 동작합니다.</p>
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
