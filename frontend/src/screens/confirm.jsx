import { useCallback, useEffect, useState } from 'react';
import { fetchPrescriptionDetail } from '../api/prescriptionRecords.js';
import { Camera, ChevronLeft, Eye } from 'lucide-react';
import { Button, SmallButton } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Panel } from '../components/ui/misc.jsx';
import { Modal } from '../components/ui/Modal.jsx';
import { AppShell, Header } from '../components/ui/layout.jsx';
import { RxPaper } from '../components/rx/RxPaper.jsx';
import { Highlight, LowConfidenceBanner } from '../components/rx/Highlight.jsx';
import { MedList, emptyMed, fillGuessedFields, isMissing, prepareOcrMed } from '../components/rx/meds.jsx';
import { confirmPrescription, toConfirmItem } from '../api/prescriptionConfirm.js';
import { suggestDiseaseName } from '../data/diseaseCodes.js';
import { medFields, meds as sampleMeds, prescription as rx } from '../data/sample.js';
import { getPrescriptionDraft, setPrescriptionDraft } from './fe2Draft.js';
import { dateParts, todayKey, useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';

const MARKS = [[140, 186, 30], [190, 226, 22]];
const countLow = (list) => list.reduce((n, m) => n + medFields.filter(([k]) => Boolean(m[k]?.low)).length, 0);
/** 빈 칸이 있는 약 수 — 알려만 주고, 가이드 만들기를 막지는 않아요. */
const countWithBlank = (list) => list.filter((m) => !m.isNew && medFields.some(([k]) => isMissing(m, k))).length;

/** 처방전·약봉투에 따라 바뀌는 낱말 (조사까지 함께) */
const DOC_WORDS = {
  PRESCRIPTION: { name: '처방전', withAnd: '처방전과', dateLabel: '처방일', dateSuffix: '처방' },
  PILL_BAG: { name: '약봉투', withAnd: '약봉투와', dateLabel: '약 받은 날', dateSuffix: '받은 약' },
};

export function BackLink({ children, onClick }) {
  return (
    <button type="button" onClick={onClick} className="-ml-1 hidden min-h-11 items-center gap-1 self-start rounded-md pl-1 pr-2 text-14 font-medium text-muted hover:text-ink lg:inline-flex">
      <ChevronLeft size={18} aria-hidden />
      {children}
    </button>
  );
}

/** 병명 칸 아래 안내 — 어디서 채운 값인지 알려 줘서 보호자가 맞는지 확인하게 해요. */
function diseaseHelperText({ typed, suggestion, current }) {
  const codes = suggestion.codes.join(', ');
  if (typed || !codes) return '진료받을 때 들은 병명을 적어 주세요. 병에 맞는 돌봄 방법을 고를 때 써요.';
  if (suggestion.name && current === suggestion.name) {
    return `처방전 질병분류기호(${codes})로 채운 병명이에요. 맞는지 확인하고, 다르면 고쳐 주세요.`;
  }
  if (!suggestion.name) return `처방전 질병분류기호는 ${codes}예요. 진료받을 때 들은 병명을 적어 주세요.`;
  return `처방전 질병분류기호: ${codes}`;
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
      <div className="flex flex-col gap-3 bg-paper p-4">
        {previewUrl ? <img src={previewUrl} alt={`업로드한 ${words.name} 원본`} className="max-h-[70vh] w-full rounded-md object-contain" /> : <RxPaper fluid marks={MARKS} />}
        {!previewUrl && <p className="flex items-center gap-2 text-13 text-muted">
          <Highlight className="text-13">노란 표시</Highlight>
          흐릿하게 읽힌 곳이에요.
        </p>}
      </div>
    </Modal>
  );
}

export function ConfirmScreen(props) {
  const prescriptionId = getPrescriptionDraft()?.prescriptionId;
  const [access, setAccess] = useState(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!prescriptionId) return;

    let cancelled = false;

    async function checkPrescription() {
      try {
        const detail = await fetchPrescriptionDetail(prescriptionId);

        if (cancelled) return;

        if (detail.status === 'GUIDE_DONE') {
          setAccess({ id: prescriptionId, state: 'blocked' });
        } else if (['OCR_DONE', 'CONFIRMED'].includes(detail.status)) {
          setAccess({ id: prescriptionId, state: 'allowed' });
        } else {
          setAccess({ id: prescriptionId, state: 'error' });
        }
      } catch {
        if (!cancelled) {
          setAccess({ id: prescriptionId, state: 'error' });
        }
      }
    }

    checkPrescription();

    return () => {
      cancelled = true;
    };
  }, [prescriptionId, retry]);

  const state = access?.id === prescriptionId
    ? access?.state
    : null;

  if (prescriptionId && state !== 'allowed') {
    return (
      <AppShell
        tab="upload"
        onTab={props.onTab}
        showTabs={false}
        header={<Header title="처방 내용 확인" />}
      >
        <div className="flex flex-col gap-4 p-6">
          {state === 'blocked' ? (
            <>
              <h2 className="text-22 font-bold">
                이미 가이드가 생성된 처방이에요.
              </h2>
              <p>가이드 생성이 완료된 처방은 수정할 수 없어요.</p>
              <Button onClick={() => props.go('guides', undefined, { replace: true })}>
                가이드 목록 보기
              </Button>
            </>
          ) : state === 'error' ? (
            <>
              <p>처방 상태를 확인하지 못했어요.</p>
              <Button onClick={() => {
                setAccess(null);
                setRetry((n) => n + 1);
              }}>
                다시 확인하기
              </Button>
            </>
          ) : (
            <p role="status">처방 상태를 확인하고 있어요…</p>
          )}
          <Button variant="secondary" onClick={() => props.go('home', undefined, { replace: true })}>
            홈으로 돌아가기
          </Button>
        </div>
      </AppShell>
    );
  }

  return <ConfirmForm key={prescriptionId ?? 'demo'} {...props} />;
}

function ConfirmForm({ go, back, onTab }) {
  const draft = getPrescriptionDraft();
  const { recordPrescription } = useRecords();
  const { child: selectedChild, childList } = useSelectedChild();
  const child = childList.find((c) => c.id === draft?.childId) ?? selectedChild;
  // 처방전 머리 정보 — OCR 결과가 없으면(주소로 바로 들어온 경우 등) 예시 값을 보여요.
  const ocr = draft?.ocr ?? { hospital: rx.hospital, date: rx.isoDate, disease: rx.disease };
  const words = DOC_WORDS[draft?.sourceType] ?? DOC_WORDS.PRESCRIPTION;
  // 약봉투는 조제일자를 약 받은 날로 써요. OCR이 날짜를 못 읽었으면(서버가 null) 보호자가 골라야 복약 일정을 시작할 수 있어요.
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
  // 숫자만 읽힌 1회 양에는 단위를 붙이고, 용법은 처방전이면 읽은 글 그대로(직접 입력), 약봉투면 드롭다운 값으로 둬요.
  const [meds, setMeds] = useState(() => (draft?.ocrMeds ?? sampleMeds).map((m) => prepareOcrMed(m, draft?.sourceType)));
  // 병명 — 보호자가 처방 올리기에서 적은 값이 먼저예요. 없으면 처방전 질병분류기호로 병명을 제안해요(보호자가 확인·수정).
  const suggestion = suggestDiseaseName(ocr.diagnosisCodes);
  const typedDisease = (draft?.disease || ocr.disease || '').trim();
  const [disease, setDisease] = useState(() => typedDisease || suggestion.name);
  const [diseaseError, setDiseaseError] = useState('');
  const diseaseHelper = diseaseHelperText({ typed: Boolean(typedDisease), suggestion, current: disease });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
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

  const updateMed = (next) => setMeds((list) => list.map((m) => (m.id === next.id ? fillGuessedFields(next) : m)));
  const removeMed = (id) => setMeds((list) => list.filter((m) => m.id !== id));
  const addMed = () => setMeds((list) => [...list, emptyMed()]);
  const lowCount = countLow(meds);
  const blankCount = countWithBlank(meds);
  const saved = meds.filter((m) => !m.isNew);

  // 가이드를 못 만드는 이유는 알림창 대신 버튼 바로 위에 보여요. 앱 안 브라우저처럼 알림창이 안 뜨는 곳에서도 보이게요.
  const fail = (message) => setFormError(message);
  const make = async () => {
    if (saving) return;
    setFormError('');
    if (editingIds.size > 0) {
      fail('수정 중인 약 정보가 있습니다. 저장하거나 취소한 후 가이드를 만들어 주세요.');
      return;
    }
    if (meds.length === 0) {
      fail('확인할 약이 없습니다. 약을 추가한 후 가이드를 만들어 주세요.');
      return;
    }
    if (needsDate && !pickedDate) {
      setDateError(`${words.dateLabel}을 골라 주세요.`);
      fail(`${words.name}에서 날짜를 읽지 못했어요. ${words.dateLabel}을 골라 주세요.`);
      return;
    }
    if (meds.some((m) => m.isNew || !m.name.trim())) {
      fail('추가 중인 약을 저장하고 약 이름을 확인해 주세요.');
      return;
    }
    // 1회 양·하루 횟수·기간·용법은 비어 있어도 가이드를 만들어요. 빈 칸은 위 안내와 카드의 노란 표시로만 알려요.
    const diseaseName = disease.trim();
    if (!diseaseName) {
      setDiseaseError('병명을 적어 주세요.');
      fail('병명을 적어 주세요. 가이드가 병에 맞는 돌봄 방법을 고를 때 써요.');
      return;
    }

    // 서버에 올린 처방이면 확정 API(7번)로 보호자가 고친 약 목록과 병명을 저장해요. 저장에 성공해야 가이드를 만들어요.
    if (draft?.prescriptionId) {
      const items = meds.map(toConfirmItem);
      setSaving(true);
      try {
        await confirmPrescription(draft.prescriptionId, {
          // 처방일은 약봉투처럼 서버에 없을 때만 보내요. 병원 이름은 이 화면에서 고치지 않으니 서버 값을 그대로 둬요.
          prescription_date: needsDate ? pickedDate : null,
          hospital_name: null,
          diagnosis_user_input: diseaseName,
          symptom_notes: draft.note || null,
          medications: items,
        });
      } catch (error) {
        setSaving(false);
        fail(error.message || '처방 내용을 저장하지 못했어요.');
        return;
      }
      setSaving(false);
    }

    setPrescriptionDraft({
      ...getPrescriptionDraft(),
      disease: diseaseName,
      ocrMeds: meds,
      guideReady: true,
    });
    // 확인한 병원·날짜·병명·약으로 건강기록과 복약 일정을 자동으로 남겨요.
    // 예시 처방(서버 없음)은 여기서 가이드도 만들어요. 서버 처방의 가이드는 만드는 중 화면이 서버에서 받아 와요.
    if (child) {
      const { visit, guide } = recordPrescription({
        prescriptionId: draft?.prescriptionId,
        childId: child.id,
        date,
        hospital: ocr.hospital,
        title: diseaseName,
        meds,
      });
      setPrescriptionDraft({ ...getPrescriptionDraft(), childId: child.id, guideId: guide?.id ?? `g${visit.id}` });
    }
    go('guide-loading');
  };
  const retake = () => go('upload');
  const errorNote = formError && (
    <p role="alert" className="rounded-lg bg-danger-soft px-3.5 py-3 text-14 text-danger">{formError}</p>
  );
  const actions = {
    mobile: (
      <>
        {errorNote && <div className="lg:hidden">{errorNote}</div>}
        <Button className="w-full" onClick={make} disabled={saving}>{saving ? '저장하는 중…' : '확인했어요, 가이드 만들기'}</Button>
        <Button variant="secondary" className="w-full" onClick={retake} disabled={saving}>다시 찍기</Button>
      </>
    ),
    desktop: null,
  };
  return (
    <AppShell tab="upload" onTab={onTab} showTabs={false} width="wide" actions={actions}
      header={<Header title="처방 내용 확인" onBack={() => back('upload')} className="lg:hidden" />}>
      <div className="flex flex-col gap-6 px-5 pb-8 pt-1 lg:gap-8 lg:px-0 lg:pb-16 lg:pt-6">
        <div className="flex flex-col gap-3 lg:max-w-reading">
          <BackLink onClick={() => back('upload')}>돌아가기</BackLink>
          <h2 className="text-22 font-bold lg:text-28">
            읽은 내용이 {words.withAnd}<br className="lg:hidden" /> 같은지 확인해 주세요
          </h2>
          {!draft?.prescriptionId && <p role="status" className="text-13 text-faint">현재 약 목록은 예시 데이터입니다. 업로드한 사진의 실제 OCR 결과가 아닙니다.</p>}
          <p className="text-15 text-muted">확인을 누르면 병원, {words.dateLabel}, 병명, 약이 {child?.name ?? '아이'}의 건강기록에 자동으로 남고, 복약 달력에 먹일 약이 채워져요.</p>
        </div>
        <div className="flex flex-col gap-6 lg:grid lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)] lg:items-start lg:gap-10 xl:grid-cols-[minmax(0,420px)_minmax(0,1fr)] xl:gap-12">
          {/* 데스크톱 원본 */}
          <div className="hidden flex-col overflow-hidden rounded-xl border border-line bg-surface lg:sticky lg:top-[88px] lg:flex">
            <div className="flex justify-center bg-paper p-5">
              {draft?.previewUrl ? <img src={draft.previewUrl} alt={`업로드한 ${words.name} 원본`} className="max-h-[520px] w-full rounded-md object-contain" /> : <RxPaper width={420} marks={MARKS} className="h-auto w-full max-w-[340px]" />}
            </div>
            {/* 데스크톱 메타 */}
            <dl className="flex flex-col divide-y divide-line border-t border-line px-5">
              {[['병원', head.hospital], [words.dateLabel, head.date], ['아이', child ? `${child.name}, ${child.age}` : '-']].map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between gap-4 py-3">
                  <dt className="shrink-0 text-14 text-muted">{k}</dt>
                  <dd className="min-w-0 text-right text-15 font-medium">{v}</dd>
                </div>
              ))}
            </dl>
            <div className="flex border-t border-line px-5 py-3">
              <SmallButton icon={Eye} onClick={openOriginal}>크게 보기</SmallButton>
            </div>
          </div>

          <div className="flex min-w-0 flex-col gap-5">
            {lowCount > 0 && <LowConfidenceBanner count={lowCount} />}
            {blankCount > 0 && (
              <p role="note" className="rounded-lg bg-sunk px-3.5 py-3 text-14">
                {blankCount}개 약에 읽지 못한 칸이 있어요. 비워 둔 채로 가이드를 만들 수 있고,
                {' '}{words.name} 원본이나 약국 안내를 보고 연필 버튼으로 채우면 가이드가 더 정확해져요.
              </p>
            )}
            {needsDate && (
              <Field
                label={words.dateLabel}
                type="date"
                value={pickedDate}
                onChange={(e) => { setPickedDate(e.target.value); setDateError(''); }}
                max={todayKey()}
                helper={draft?.sourceType === 'PILL_BAG'
                  ? '약봉투의 조제일자를 읽지 못했어요. 약봉투에 적힌 조제일자(약 받은 날)를 골라 주세요. 복약 일정이 이 날부터 시작돼요.'
                  : `${words.name}에서 ${words.dateLabel}을 읽지 못했어요. 날짜를 골라 주세요. 복약 일정이 이 날부터 시작돼요.`}
                error={dateError}
              />
            )}
            <Field
              label="병명"
              value={disease}
              onChange={(e) => { setDisease(e.target.value); setDiseaseError(''); }}
              placeholder="예: 중이염"
              maxLength={200}
              helper={diseaseHelper}
              error={diseaseError}
            />

            {/* 모바일 원본 요약 */}
            <Panel className="flex items-center gap-3 py-3 pl-3 pr-3 lg:hidden">
              {draft?.previewUrl ? <img src={draft.previewUrl} alt={`${words.name} 미리보기`} className="h-[76px] w-[54px] shrink-0 rounded-sm border border-line object-cover" /> : <RxPaper width={54} marks={MARKS} />}
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <p className="text-15 font-semibold">{head.hospital}</p>
                <p className="text-13 text-muted">{when ? `${head.shortDate} ${words.dateSuffix}` : head.shortDate}, 사진 1장</p>
              </div>
              <SmallButton icon={Eye} onClick={openOriginal} className="shrink-0">원본</SmallButton>
            </Panel>

            <h3 className="mt-1 text-18 font-bold lg:mt-0 lg:text-20">약 {saved.length}개</h3>
            <MedList meds={meds} onChange={updateMed} onAdd={addMed} onRemove={removeMed} onEditingChange={onEditingChange} />

            {errorNote && <div className="hidden lg:block">{errorNote}</div>}
            <div className="hidden justify-end gap-3 border-t border-line pt-6 lg:flex">
              <Button variant="secondary" className="min-w-[140px]" onClick={retake} disabled={saving}>다시 찍기</Button>
              <Button className="min-w-[260px]" onClick={make} disabled={saving}>{saving ? '저장하는 중…' : '확인했어요, 가이드 만들기'}</Button>
            </div>
          </div>
        </div>
      </div>
      <OriginalModal open={showOriginal} onClose={closeOriginal} previewUrl={draft?.previewUrl} head={head} words={words} />
    </AppShell>
  );
}
