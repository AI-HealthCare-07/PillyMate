import { useCallback, useState } from 'react';
import { Camera, ChevronLeft, Eye } from 'lucide-react';
import { Button, SmallButton } from '../components/ui/Button.jsx';
import { Panel } from '../components/ui/misc.jsx';
import { Modal } from '../components/ui/Modal.jsx';
import { AppShell, Header } from '../components/ui/layout.jsx';
import { RxPaper } from '../components/rx/RxPaper.jsx';
import { Highlight, LowConfidenceBanner } from '../components/rx/Highlight.jsx';
import { MedList, emptyMed } from '../components/rx/meds.jsx';
import { children as sampleChildren, medFields, meds as sampleMeds, prescription as rx } from '../data/sample.js';
import { getPrescriptionDraft, setPrescriptionDraft } from './fe2Draft.js';

const MARKS = [[140, 186, 30], [190, 226, 22]];
const countLow = (list) => list.reduce((n, m) => n + medFields.filter(([k]) => Boolean(m[k]?.low)).length, 0);

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
/** 원본 사진 모달 — 실제 서비스에서는 RxPaper 대신 업로드한 사진(<img>)을 넣어요 */
function OriginalModal({ open, onClose, previewUrl }) {
  return (
    <Modal open={open} onClose={onClose} title="처방전 원본" description={previewUrl ? "사용자가 선택한 이미지" : `${rx.hospital}, ${rx.date} (예시)`}>
      <div className="flex flex-col gap-3 bg-sunk p-4">
        {previewUrl ? <img src={previewUrl} alt="업로드한 처방전 원본" className="max-h-[70vh] w-full object-contain" /> : <RxPaper fluid marks={MARKS} />}
        {!previewUrl && <p className="flex items-center gap-2 text-13 text-muted">
          <Highlight className="text-13">노란 표시</Highlight>
          흐릿하게 읽힌 곳이에요.
        </p>}
      </div>
    </Modal>
  );
}

export function ConfirmScreen({ go, onTab }) {
  const draft = getPrescriptionDraft();
  const selectedChild = sampleChildren.find((item) => item.id === draft?.childId);
  const hasUploadedImage = Boolean(draft?.file);
  // TODO(API): OCR 응답의 약 목록을 정규화해 초기 상태로 사용하세요.
  // 현재 목록은 데모 데이터이며 업로드한 이미지에서 읽어낸 결과가 아닙니다.
  const [meds, setMeds] = useState(() => draft?.ocrMeds ?? sampleMeds);
  const [showOriginal, setShowOriginal] = useState(false);
  const [guideReady, setGuideReady] = useState(Boolean(draft?.guideReady));
  const openOriginal = () => setShowOriginal(true);
  const closeOriginal = useCallback(() => setShowOriginal(false), []);

  const markChanged = () => {
    setGuideReady(false);
    const current = getPrescriptionDraft();
    if (current) setPrescriptionDraft({ ...current, guideReady: false });
  };
  const updateMed = (next) => { markChanged(); setMeds((list) => list.map((m) => (m.id === next.id ? next : m))); };
  const removeMed = (id) => { markChanged(); setMeds((list) => list.filter((m) => m.id !== id)); };
  const addMed = () => { markChanged(); setMeds((list) => [...list, emptyMed()]); };
  const lowCount = countLow(meds);
  const saved = meds.filter((m) => !m.isNew);

  const make = () => {
    if (meds.some((m) => m.isNew || !m.name.trim())) {
      window.alert('추가 중인 약을 저장하고 약 이름을 확인해 주세요.');
      return;
    }
    // 동일한 처방의 가이드를 이미 생성했다면 로딩 화면을 다시 거치지 않습니다.
    if (guideReady) { go('guide'); return; }
    // TODO(API): 실제 서버의 가이드 생성 완료 여부와 처방 버전을 기준으로 판단하세요.
    // TODO(API): 수정한 약 목록과 처방 ID를 BE-2 확정 API에 전송하고 저장 성공을 확인하세요.
    // TODO(INTEGRATION): FE-1의 가이드 생성 완료 응답 시 guideReady를 설정하도록 연결하세요.
    // 현재 데모에서는 로딩 화면 이후 성공한다고 가정합니다.
    const current = getPrescriptionDraft();
    if (current) setPrescriptionDraft({ ...current, ocrMeds: meds, guideReady: true });
    setGuideReady(true);
    go('guide-loading');
  };
  const retake = () => go('upload');
  const actions = {
    mobile: (
      <>
        <Button className="w-full" onClick={make}>{guideReady ? '가이드 다시 보기' : '확인했어요, 가이드 만들기'}</Button>
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

        <p role="status" className="text-13 text-muted">현재 약 목록은 예시 데이터입니다. 업로드한 사진의 실제 OCR 결과가 아닙니다.</p>
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:gap-10">
          {/* 데스크톱 원본 */}
          <div className="hidden w-[420px] shrink-0 flex-col gap-3 lg:sticky lg:top-[100px] lg:flex">
            {draft?.previewUrl ? <img src={draft.previewUrl} alt="업로드한 처방전 원본" className="max-h-[580px] w-full rounded-xl border border-line object-contain" /> : <RxPaper width={420} marks={MARKS} />}
            <div className="flex gap-2">
              <SmallButton icon={Eye} onClick={openOriginal}>크게 보기</SmallButton>
            </div>
          </div>

          <div className="flex min-w-0 flex-1 flex-col gap-5">
            {lowCount > 0 && <LowConfidenceBanner count={lowCount} />}

            {/* 모바일 원본 요약 */}
            <Panel className="flex items-center gap-3 p-3 lg:hidden">
              {draft?.previewUrl ? <img src={draft.previewUrl} alt="처방전 미리보기" className="h-[76px] w-[54px] rounded border border-line object-cover" /> : <RxPaper width={54} marks={MARKS} />}
              <div className="flex flex-1 flex-col gap-0.5">
                <p className="text-15 font-semibold">{hasUploadedImage ? '선택한 처방전' : `${rx.hospital} (예시)`}</p>
                <p className="text-13 text-muted">{hasUploadedImage ? `${draft.file.name} · ${selectedChild?.name ?? '아이 미선택'}` : `${rx.shortDate} 처방, 사진 1장 (예시)`}</p>
              </div>
              <SmallButton icon={Eye} onClick={openOriginal}>원본</SmallButton>
            </Panel>

            {/* 데스크톱 메타 */}
            <dl className="hidden gap-10 lg:flex">
              {[['병원', hasUploadedImage ? 'OCR 연동 전' : `${rx.hospital} (예시)`], ['처방일', hasUploadedImage ? 'OCR 연동 전' : rx.date], ['아이', selectedChild ? `${selectedChild.name}, ${selectedChild.age}` : '선택 전']].map(([k, v]) => (
                <div key={k} className="flex flex-col gap-0.5">
                  <dt className="text-13 text-muted">{k}</dt>
                  <dd className="text-16 font-medium">{v}</dd>
                </div>
              ))}
            </dl>

            <h3 className="text-18 font-bold">약 {saved.length}개</h3>
            <MedList meds={meds} onChange={updateMed} onAdd={addMed} onRemove={removeMed} />

            <div className="hidden justify-end gap-3 lg:flex">
              <Button variant="secondary" className="w-[140px]" onClick={retake}>
                <Camera size={18} aria-hidden="true" />
                다시 찍기
              </Button>
              <Button className="w-[260px]" onClick={make}>{guideReady ? '가이드 다시 보기' : '확인했어요, 가이드 만들기'}</Button>
            </div>
          </div>
        </div>
      </div>
      <OriginalModal open={showOriginal} onClose={closeOriginal} previewUrl={draft?.previewUrl} />
    </AppShell>
  );
}
