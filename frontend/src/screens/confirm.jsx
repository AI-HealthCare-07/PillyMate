import { useCallback, useState } from 'react';
import { Camera, ChevronLeft, Eye } from 'lucide-react';
import { Button, SmallButton } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Panel } from '../components/ui/misc.jsx';
import { Modal } from '../components/ui/Modal.jsx';
import { AppShell, Header } from '../components/ui/layout.jsx';
import { RxPaper } from '../components/rx/RxPaper.jsx';
import { Highlight, LowConfidenceBanner } from '../components/rx/Highlight.jsx';
import { MedList, emptyMed } from '../components/rx/meds.jsx';
import { medFields, meds as sampleMeds, prescription as rx } from '../data/sample.js';
import { getPrescriptionDraft, setPrescriptionDraft } from './fe2Draft.js';
import { dateParts, todayKey, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';

const MARKS = [[140, 186, 30], [190, 226, 22]];
const countLow = (list) => list.reduce((n, m) => n + medFields.filter(([k]) => Boolean(m[k]?.low)).length, 0);
const countNoTiming = (list) => list.filter((m) => !m.isNew && !String(m.timing?.value ?? '').trim()).length;

/** 처방전·약봉투에 따라 바뀌는 낱말 (조사까지 함께) */
const DOC_WORDS = {
  PRESCRIPTION: { name: '처방전', withAnd: '처방전과', dateLabel: '처방일', dateSuffix: '처방' },
  PILL_BAG: { name: '약봉투', withAnd: '약봉투와', dateLabel: '약 받은 날', dateSuffix: '받은 약' },
};

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
function OriginalModal({ open, onClose, previewUrl, head, words }) {
  return (
    <Modal open={open} onClose={onClose} title={`${words.name} 원본`} description={`${head.hospital}, ${head.date}`}>
      <div className="flex flex-col gap-3 bg-sunk p-4">
        {previewUrl ? <img src={previewUrl} alt={`업로드한 ${words.name} 원본`} className="max-h-[70vh] w-full object-contain" /> : <RxPaper fluid marks={MARKS} />}
        {!previewUrl && <p className="flex items-center gap-2 text-13 text-muted">
          <Highlight className="text-13">노란 표시</Highlight>
          흐릿하게 읽힌 곳이에요.
        </p>}
      </div>
    </Modal>
  );
}

export function ConfirmScreen({ go, back, onTab }) {
  const draft = getPrescriptionDraft();
  const { recordPrescription } = useRecords();
  const { child: selectedChild, childList } = useSelectedChild();
  const child = childList.find((c) => c.id === draft?.childId) ?? selectedChild;
  // 처방전 머리 정보 — OCR 결과가 없으면(주소로 바로 들어온 경우 등) 예시 값을 보여요.
  const ocr = draft?.ocr ?? { hospital: rx.hospital, date: rx.isoDate, disease: rx.disease };
  const words = DOC_WORDS[draft?.sourceType] ?? DOC_WORDS.PRESCRIPTION;
  // 약봉투에는 처방일이 없어요(서버가 null). 그때는 보호자가 약 받은 날을 골라야 복약 일정을 시작할 수 있어요.
  const needsDate = !ocr.date;
  const [pickedDate, setPickedDate] = useState('');
  const [dateError, setDateError] = useState('');
  const date = ocr.date || pickedDate || null;
  const when = date ? dateParts(date) : null;
  const head = {
    hospital: ocr.hospital,
    date: when ? `${when.year}년 ${when.month}월 ${when.day}일` : '날짜를 골라 주세요',
    shortDate: when ? `${when.month}월 ${when.day}일` : '날짜 미입력',
  };
  // TODO(API): OCR 응답의 약 목록을 정규화해 초기 상태로 사용하세요.
  // 현재 목록은 데모 데이터이며 업로드한 이미지에서 읽어낸 결과가 아닙니다.
  const [meds, setMeds] = useState(() => draft?.ocrMeds ?? sampleMeds);
  const [showOriginal, setShowOriginal] = useState(false);
  const [editingIds, setEditingIds] = useState(() => new Set());
  const onEditingChange = useCallback((id, editing) => {
    setEditingIds((previous) => {
      if (previous.has(id) === editing) return previous;
      const next = new Set(previous);
      if (editing) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);
  const openOriginal = () => setShowOriginal(true);
  const closeOriginal = useCallback(() => setShowOriginal(false), []);

  const updateMed = (next) => setMeds((list) => list.map((m) => (m.id === next.id ? next : m)));
  const removeMed = (id) => setMeds((list) => list.filter((m) => m.id !== id));
  const addMed = () => setMeds((list) => [...list, emptyMed()]);
  const lowCount = countLow(meds);
  const noTimingCount = countNoTiming(meds);
  const saved = meds.filter((m) => !m.isNew);

  const make = () => {
    if (editingIds.size > 0) {
      window.alert('수정 중인 약 정보가 있습니다. 저장하거나 취소한 후 가이드를 만들어 주세요.');
      return;
    }
    if (meds.length === 0) {
      window.alert('확인할 약이 없습니다. 약을 추가한 후 가이드를 만들어 주세요.');
      return;
    }
    if (needsDate && !pickedDate) {
      setDateError(`${words.dateLabel}을 골라 주세요.`);
      window.alert(`${words.name}에 날짜가 없어요. ${words.dateLabel}을 골라 주세요.`);
      return;
    }
    if (meds.some((m) => m.isNew || !m.name.trim())) {
      window.alert('추가 중인 약을 저장하고 약 이름을 확인해 주세요.');
      return;
    }
    // ISSUE-07: 편집 내용은 임시 저장할 수 있지만,
    // 가이드 생성 전에 핵심 복약 정보가 모두 확인되었는지 검사합니다.
    const requiredFields = [
      ['dose', '1회 양'],
      ['perDay', '하루 횟수'],
      ['days', '복용 기간'],
    ];
    for (const med of meds) {
      for (const [key, label] of requiredFields) {
        if (!String(med[key]?.value ?? '').trim()) {
          window.alert(
            `「${med.name}」의 ${label} 정보가 없습니다. ${words.name} 원본을 확인하거나 의료기관·약국에 문의해 주세요. 확인 전에는 가이드를 만들 수 없습니다.`
          );
          return;
        }
      }
    }
    // TODO(API): 수정한 약 목록과 처방 ID를 BE-2 확정 API에 전송하고
    // 저장 성공 시에만 가이드 생성 화면으로 이동해야 합니다.
    // TODO(INTEGRATION): FE-1과 확정 처방 데이터 전달 계약을 합의하세요.
    // 화면을 다시 열어도 확정한 약 목록을 복원할 수 있도록 임시 저장합니다.
    // 실제 서버 저장/API 호출은 추후 연동하며, 이 저장은 새로고침 후 유지되지 않습니다.
    setPrescriptionDraft({
      ...getPrescriptionDraft(),
      ocrMeds: meds,
      guideReady: true,
    });
    // 처방전에서 읽은 병원·날짜·병명·약으로 건강기록과 복약 일정을 자동으로 남겨요.
    // 병명은 보호자가 처방 올리기에서 적은 값이 있으면 그걸, 없으면 처방전에서 읽은 값을 써요.
    // 만든 가이드의 id를 임시 데이터에 남겨서, 만드는 중 화면 → 가이드 화면이 이 아이의 이 가이드를 보여 줘요.
    if (child) {
      const { guide } = recordPrescription({
        prescriptionId: draft?.prescriptionId,
        childId: child.id,
        date,
        hospital: ocr.hospital,
        title: draft?.disease?.trim() || ocr.disease || '진료',
        meds,
      });
      setPrescriptionDraft({ ...getPrescriptionDraft(), childId: child.id, guideId: guide.id });
    }
    go('guide-loading');
  };
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
      header={<Header title="처방 내용 확인" onBack={() => back('upload')} className="lg:hidden" />}>
      <div className="flex flex-col gap-5 px-5 pb-7 pt-1 lg:gap-5 lg:px-0 lg:pb-16 lg:pt-8">
        <BackLink onClick={() => back('upload')}>돌아가기</BackLink>
        <h2 className="text-22 font-bold lg:text-28">
          읽은 내용이 {words.withAnd}<br className="lg:hidden" /> 같은지 확인해 주세요
        </h2>

        {!draft?.prescriptionId && <p role="status" className="text-13 text-muted">현재 약 목록은 예시 데이터입니다. 업로드한 사진의 실제 OCR 결과가 아닙니다.</p>}
        <p className="text-14 text-muted">확인을 누르면 병원, {words.dateLabel}, 병명, 약이 {child?.name ?? '아이'}의 건강기록에 자동으로 남고, 복약 달력에 먹일 약이 채워져요.</p>
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:gap-10">
          {/* 데스크톱 원본 */}
          <div className="hidden w-[420px] shrink-0 flex-col gap-3 lg:sticky lg:top-[100px] lg:flex">
            {draft?.previewUrl ? <img src={draft.previewUrl} alt={`업로드한 ${words.name} 원본`} className="max-h-[580px] w-full rounded-xl border border-line object-contain" /> : <RxPaper width={420} marks={MARKS} />}
            <div className="flex gap-2">
              <SmallButton icon={Eye} onClick={openOriginal}>크게 보기</SmallButton>
            </div>
          </div>

          <div className="flex min-w-0 flex-1 flex-col gap-5">
            {lowCount > 0 && <LowConfidenceBanner count={lowCount} />}
            {noTimingCount > 0 && (
              <p role="note" className="rounded-lg bg-sunk px-3.5 py-3 text-14">
                {noTimingCount}개 약은 먹는 때를 읽지 못했어요.{' '}
                {draft?.sourceType === 'PILL_BAG' ? '약봉투에 식전·식후 표시가 없거나 흐릿했어요. ' : ''}
                약국 안내를 보고 연필 버튼을 눌러 적어 주세요.
              </p>
            )}
            {needsDate && (
              <Field
                label={words.dateLabel}
                type="date"
                value={pickedDate}
                onChange={(e) => { setPickedDate(e.target.value); setDateError(''); }}
                max={todayKey()}
                helper={`${words.name}에는 처방일이 적혀 있지 않아요. 약국에서 약을 받은 날을 골라 주세요. 복약 일정이 이 날부터 시작돼요.`}
                error={dateError}
              />
            )}

            {/* 모바일 원본 요약 */}
            <Panel className="flex items-center gap-3 p-3 lg:hidden">
              {draft?.previewUrl ? <img src={draft.previewUrl} alt={`${words.name} 미리보기`} className="h-[76px] w-[54px] rounded border border-line object-cover" /> : <RxPaper width={54} marks={MARKS} />}
              <div className="flex flex-1 flex-col gap-0.5">
                <p className="text-15 font-semibold">{head.hospital}</p>
                <p className="text-13 text-muted">{when ? `${head.shortDate} ${words.dateSuffix}` : head.shortDate}, 사진 1장</p>
              </div>
              <SmallButton icon={Eye} onClick={openOriginal}>원본</SmallButton>
            </Panel>

            {/* 데스크톱 메타 */}
            <dl className="hidden gap-10 lg:flex">
              {[['병원', head.hospital], [words.dateLabel, head.date], ['아이', child ? `${child.name}, ${child.age}` : '-']].map(([k, v]) => (
                <div key={k} className="flex flex-col gap-0.5">
                  <dt className="text-13 text-muted">{k}</dt>
                  <dd className="text-16 font-medium">{v}</dd>
                </div>
              ))}
            </dl>

            <h3 className="text-18 font-bold">약 {saved.length}개</h3>
            <MedList meds={meds} onChange={updateMed} onAdd={addMed} onRemove={removeMed} onEditingChange={onEditingChange} />

            <div className="hidden justify-end gap-3 lg:flex">
              <Button variant="secondary" className="w-[140px]" onClick={retake}>다시 찍기</Button>
              <Button className="w-[260px]" onClick={make}>확인했어요, 가이드 만들기</Button>
            </div>
          </div>
        </div>
      </div>
      <OriginalModal open={showOriginal} onClose={closeOriginal} previewUrl={draft?.previewUrl} head={head} words={words} />
    </AppShell>
  );
}
