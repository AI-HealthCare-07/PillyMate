import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, Camera, Check, Circle, ImageIcon, RefreshCw } from 'lucide-react';
import { Button, SmallButton } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Avatar, Panel, SectionLabel, SelectChip } from '../components/ui/misc.jsx';
import { AlertDialog } from '../components/ui/AlertDialog.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { RxPaper } from '../components/rx/RxPaper.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';
import { getPrescriptionDraft, setPrescriptionDraft } from './fe2Draft.js';
import {
  ACCEPT_ATTRIBUTE,
  draftFieldsFromRegistration,
  imageFileProblem,
  registerPrescription,
} from '../api/prescriptionRegistration.js';

// 서버 OCR은 문서 종류마다 다른 양식으로 읽어요. 약봉투를 처방전으로 보내면 약을 찾지 못해요.
const SOURCE_TYPES = [
  { value: 'PRESCRIPTION', label: '처방전' },
  { value: 'PILL_BAG', label: '약봉투' },
];
const sourceLabel = (value) => SOURCE_TYPES.find((t) => t.value === value)?.label ?? '처방전';

/** S-03 처방 올리기 — 처방전·약봉투 사진을 골라 서버에서 읽어요. */
export function UploadScreen({ go, back, onTab }) {
  const previous = getPrescriptionDraft();
  // 처방은 항상 아이 화면에서 고른 아이의 약으로 올려요. 바꾸려면 아이 화면에서 다시 골라요.
  const { childId: child, child: childInfo } = useSelectedChild();
  const [sourceType, setSourceType] = useState(previous?.sourceType ?? 'PRESCRIPTION');
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
    const problem = imageFileProblem(selected);
    if (problem) {
      setError(problem);
      return;
    }
    const url = URL.createObjectURL(selected);
    setPrescriptionDraft({ childId: child, sourceType, disease, note, file: selected, previewUrl: url, status: 'selected', guideReady: false });
    setFile(selected);
    setPreviewUrl(url);
    setError('');
  };

  const startReading = () => {
    if (!file || !previewUrl) {
      setError(`${sourceLabel(sourceType)} 사진을 먼저 선택해 주세요.`);
      return;
    }
    if (!child) {
      setError('아이를 먼저 선택해 주세요.');
      return;
    }
    setPrescriptionDraft({ childId: child, sourceType, disease: disease.trim(), note: note.trim(), file, previewUrl, status: 'selected', guideReady: false });
    go('reading');
  };
  const read = <Button className="w-full lg:w-auto lg:min-w-[200px]" onClick={startReading}>처방 내용 읽기</Button>;
  return (
    <AppShell tab="upload" onTab={onTab} header={<Header title="처방 올리기" onBack={() => back('home')} />} actions={{ mobile: read, desktop: null }} actionsBar={false}>
      <Body className="gap-[22px] pt-1">
        <div className="flex flex-col gap-2.5">
          <SectionLabel>누구의 약인가요?</SectionLabel>
          {childInfo ? (
            <Panel className="flex items-center gap-3.5 py-3 pl-3.5 pr-2">
              <Avatar name={childInfo.name} size={40} />
              <div className="flex flex-1 flex-col gap-0.5">
                <p className="text-16 font-semibold">{childInfo.name}의 약</p>
                <p className="text-13 text-muted">{[childInfo.age, childInfo.weight].filter(Boolean).join(', ')}</p>
                {childInfo.allergy && (
                  <p className="flex items-center gap-1 text-13 font-medium text-danger">
                    <AlertTriangle size={14} strokeWidth={2} aria-hidden />{childInfo.allergy}
                  </p>
                )}
              </div>
              <button type="button" onClick={() => go('children')} className="rounded-md px-2 py-1.5 text-14 font-semibold text-brand hover:bg-paper">
                아이 바꾸기
              </button>
            </Panel>
          ) : (
            <Button variant="secondary" className="w-full" onClick={() => go('children')}>아이 먼저 고르기</Button>
          )}
        </div>
        <div className="flex flex-col gap-2.5">
          <SectionLabel>어떤 사진인가요?</SectionLabel>
          <div className="flex gap-2" role="group" aria-label="사진 종류">
            {SOURCE_TYPES.map((t) => (
              <SelectChip key={t.value} selected={sourceType === t.value} onClick={() => setSourceType(t.value)}>{t.label}</SelectChip>
            ))}
          </div>
          <p className="text-13 text-muted">
            {sourceType === 'PILL_BAG' ? '약국에서 받은 약봉투의 글자 면 전체가 나오게 찍어 주세요.' : '병원에서 받은 처방전 전체가 나오게 찍어 주세요.'}
          </p>
        </div>
        <div className="flex flex-col gap-2.5">
          <SectionLabel>{sourceLabel(sourceType)} 사진</SectionLabel>
          <Panel className="flex items-center gap-3.5 p-3">
            {previewUrl ? (
              <img src={previewUrl} alt={`선택한 ${sourceLabel(sourceType)} 미리보기`} className="h-24 w-[72px] shrink-0 rounded-md border border-line object-cover" />
            ) : (
              <RxPaper width={72} marks={[[140, 186, 30]]} />
            )}
            <div className="flex flex-1 flex-col gap-2.5">
              <div className="flex flex-col gap-0.5">
                <p className="text-16 font-semibold">{file ? file.name : `${sourceLabel(sourceType)} 사진을 선택해 주세요`}</p>
                <p className="text-13 text-muted">{file ? `${(file.size / 1024 / 1024).toFixed(2)}MB` : 'JPG, PNG · 최대 10MB'}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <SmallButton icon={Camera} onClick={() => cameraInput.current?.click()}>사진 찍기</SmallButton>
                <SmallButton icon={ImageIcon} onClick={() => fileInput.current?.click()}>앨범/파일</SmallButton>
              </div>
            </div>
          </Panel>
          <input ref={cameraInput} type="file" accept={ACCEPT_ATTRIBUTE} capture="environment" className="hidden" onChange={chooseFile} aria-label="카메라로 처방전 촬영" />
          <input ref={fileInput} type="file" accept={ACCEPT_ATTRIBUTE} className="hidden" onChange={chooseFile} aria-label="처방전 이미지 선택" />
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
  { label: '약 정보 정리하기', state: 'next' },
];

const RETAKE_TIPS = [
  '밝은 곳에서 그림자 없이 찍어 주세요.',
  '처방전이나 약봉투 전체가 화면에 들어오게 해 주세요.',
  '처방 올리기에서 고른 사진 종류(처방전·약봉투)가 맞는지 확인해 주세요.',
];

/**
 * 다시 찍기 알럿 — 신뢰도가 낮거나(60% 미만) OCR이 실패하면 처방이 저장되지 않아요.
 * 버튼을 누르기 전에는 닫히지 않고 뒤 화면도 누를 수 없어요 (Esc·바깥 누르기 무시).
 * 새 사진을 고르면 다시 읽고, '처방 올리기로 돌아가기'를 누르면 처음 화면으로 가요.
 */
function RetakeAlert({ open, message, onPick, onGiveUp }) {
  const [error, setError] = useState('');
  const cameraInput = useRef(null);
  const fileInput = useRef(null);
  const choose = (event) => {
    const selected = event.target.files?.[0];
    event.target.value = '';
    if (!selected) return;
    const problem = imageFileProblem(selected);
    if (problem) {
      setError(problem);
      return;
    }
    setError('');
    onPick(selected);
  };
  return (
    <>
      <AlertDialog open={open} title="사진을 다시 찍어 주세요" description={message}>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-14 text-muted">
          {RETAKE_TIPS.map((tip) => <li key={tip}>{tip}</li>)}
        </ul>
        {error && <p role="alert" className="text-13 text-danger">{error}</p>}
        <div className="flex flex-col gap-2">
          <Button className="w-full" onClick={() => cameraInput.current?.click()}>
            <Camera size={18} className="mr-1.5" aria-hidden />사진 다시 찍기
          </Button>
          <Button variant="secondary" className="w-full" onClick={() => fileInput.current?.click()}>
            <ImageIcon size={18} className="mr-1.5" aria-hidden />앨범에서 고르기
          </Button>
          <button type="button" onClick={onGiveUp} className="self-center rounded-md px-3 py-2 text-14 font-medium text-muted hover:text-ink">
            처방 올리기로 돌아가기
          </button>
        </div>
      </AlertDialog>
      {/* 숨긴 input은 다이얼로그 밖에 둬요. 안에 있으면 Tab 가두기가 보이지 않는 칸에서 끊겨요. */}
      <input ref={cameraInput} type="file" accept={ACCEPT_ATTRIBUTE} capture="environment" className="hidden" tabIndex={-1} onChange={choose} aria-label="카메라로 처방전 다시 촬영" />
      <input ref={fileInput} type="file" accept={ACCEPT_ATTRIBUTE} className="hidden" tabIndex={-1} onChange={choose} aria-label="처방전 이미지 다시 선택" />
    </>
  );
}

/** S-03 읽는 중 — POST /prescriptions로 사진을 올리고 OCR 결과를 받아요. */
export function ReadingScreen({ go, back, onTab }) {
  const [attempt, setAttempt] = useState(0);
  const [retakeMessage, setRetakeMessage] = useState('');
  const [failure, setFailure] = useState('');
  // 개발 모드(StrictMode)에서 효과가 두 번 돌아도 처방 등록 요청은 한 번만 보내요 (두 번 보내면 처방이 두 개 저장돼요).
  const mounted = useRef(true);
  const startedAttempt = useRef(-1);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => {
    const current = getPrescriptionDraft();
    if (!current?.file) { go('upload', undefined, { replace: true }); return undefined; }
    if (startedAttempt.current === attempt) return undefined;
    startedAttempt.current = attempt;
    registerPrescription({ childId: current.childId, sourceType: current.sourceType, file: current.file, disease: current.disease, note: current.note })
      .then((data) => {
        if (!mounted.current) return;
        setPrescriptionDraft({ ...getPrescriptionDraft(), ...draftFieldsFromRegistration(data) });
        go('confirm', undefined, { replace: true });
      })
      .catch((error) => {
        if (!mounted.current) return;
        if (error.retake) setRetakeMessage(error.message);
        else setFailure(error.message);
      });
    return undefined;
  }, [go, attempt]);

  const retakeWith = useCallback((file) => {
    const current = getPrescriptionDraft();
    setPrescriptionDraft({ ...current, file, previewUrl: URL.createObjectURL(file), status: 'selected' });
    setRetakeMessage('');
    setAttempt((n) => n + 1);
  }, []);
  const giveUp = useCallback(() => back('upload'), [back]);

  const cancel = <Button variant="secondary" className="w-full lg:w-auto lg:min-w-[160px]" onClick={() => back('upload')}>취소</Button>;
  return (
    <AppShell tab="upload" onTab={onTab} showTabs={false} header={<Header title="처방 읽는 중" onBack={() => back('upload')} />} actions={{ mobile: cancel }}>
      <div className="flex flex-1 flex-col items-center gap-7 p-6 lg:px-0" aria-live="polite">
        <RxPaper width={200} marks={[[140, 186, 30], [232, 206, 30]]} scanning={!failure} />
        {failure ? (
          <div className="flex flex-col items-center gap-4 text-center">
            <h2 className="text-22 font-bold">처방전을 올리지 못했어요</h2>
            <p role="alert" className="text-15 text-danger">{failure}</p>
            <Button variant="secondary" onClick={() => back('upload')}>처방 올리기로 돌아가기</Button>
          </div>
        ) : (
          <div className="flex flex-col gap-2 text-center">
            <h2 className="text-22 font-bold">{sourceLabel(getPrescriptionDraft()?.sourceType) === '약봉투' ? '약봉투를' : '처방전을'} 읽고 있어요</h2>
            <p className="text-15 text-muted">최대 30초쯤 걸려요. 화면을 닫지 말아 주세요.</p>
          </div>
        )}
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
      <RetakeAlert open={Boolean(retakeMessage)} message={retakeMessage} onPick={retakeWith} onGiveUp={giveUp} />
    </AppShell>
  );
}
