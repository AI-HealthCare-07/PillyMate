import { useEffect, useRef, useState } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { Button, IconButton } from '../ui/Button.jsx';
import { Field, SelectField } from '../ui/Field.jsx';
import { Highlight, LowValue } from './Highlight.jsx';
import { medFields } from '../../data/sample.js';
import { USAGE_MAX_LENGTH, USAGE_OPTIONS, initialUsage, usageMode } from '../../data/usageOptions.js';
import { isAsNeeded } from '../../state/records.jsx';
import { TOPICAL_DOSE_DEFAULT, cardDoseUnit, isTopical, withDoseUnit } from '../../api/prescriptionConfirm.js';

/** 새로 추가하는 약의 빈 값 */
export const emptyMed = () => ({
  id: crypto.randomUUID(),
  name: '',
  isNew: true,
  ...Object.fromEntries(medFields.map(([k]) => [k, { value: '' }])),
});

/** 바르는 약의 '바르는 양' 드롭다운 — 기본값 하나와 직접 입력 */
const TOPICAL_DOSE_OPTIONS = [TOPICAL_DOSE_DEFAULT];
const TOPICAL_DOSE_MAX_LENGTH = 50;

/** 칸 이름 — 바르는 약은 1회 양 대신 '바르는 양'이라고 불러요. */
const fieldLabel = (med, k, label) => (k === 'dose' && isTopical(med) ? '바르는 양' : label);

/**
 * 처음 불러올 때와 보호자가 저장할 때 1회 양을 다듬어요.
 * - 먹는 약: 숫자뿐이면('5') OCR 단위나 약 이름·제형으로 짐작한 단위를 붙여요('5mL').
 * - 바르는 약: 비어 있으면 '적당량(얇게)'으로 채워요. 숫자 양은 안내하지 않아요.
 */
export function fillGuessedFields(med) {
  const doseText = med.dose?.value ?? '';
  if (isTopical(med)) {
    return doseText.trim() ? med : { ...med, dose: { ...med.dose, value: TOPICAL_DOSE_DEFAULT, mode: 'select' } };
  }
  const dose = withDoseUnit(doseText, cardDoseUnit(med));
  return dose === doseText ? med : { ...med, dose: { ...med.dose, value: dose } };
}

/**
 * OCR로 읽은 약 카드를 확인 화면에 처음 올릴 때 — 1회 양 단위를 채우고, 용법은 문서 종류에 맞는 입력 방식으로 둬요.
 * 처방전은 읽은 용법 글 그대로(직접 입력), 약봉투는 드롭다운 값(식전 30분·식후 30분·필요시)이 기본이에요.
 * 바르는 약은 OCR이 읽은 숫자 양('1', '1g')이나 '적당량'을 '적당량(얇게)'으로 바꾸고, 그 밖의 글은 직접 입력으로 남겨요.
 */
export function prepareOcrMed(med, sourceType) {
  const usage = initialUsage(med.timing?.value, { sourceType, asNeeded: isAsNeeded(med) });
  const timing = { ...med.timing, value: usage.value, mode: usage.mode };
  if (isTopical(med)) {
    const text = String(med.dose?.value ?? '').trim();
    const dose = !text || /^\d|적당/.test(text) ? { value: TOPICAL_DOSE_DEFAULT, mode: 'select' } : { value: text, mode: 'custom' };
    return { ...med, dose: { ...med.dose, ...dose }, timing };
  }
  return { ...fillGuessedFields(med), timing };
}

/** 비어 있는 칸인지 — 필요할 때 먹는 약은 정해진 기간이 없어서 비어 있어도 돼요. 비어 있어도 가이드는 만들 수 있어요. */
export const isMissing = (med, k) => !String(med[k]?.value ?? '').trim() && !(k === 'days' && isAsNeeded(med));

function Value({ v, missing }) {
  // 읽지 못한 칸은 노란 형광펜으로 표시해요. 채우지 않아도 가이드는 만들 수 있어요.
  if (missing) return <Highlight className="text-14">비어 있음</Highlight>;
  if (!v.value) return <span className="text-14 font-medium text-faint">정해진 기간 없음</span>;
  if (v.low) return <LowValue value={v.value} stacked size="text-16" />;
  return <span className="text-16 font-medium">{v.value}</span>;
}

/** 보기 상태 — 약 이름 17 SemiBold + 값 칸(모바일 2×2, 데스크톱 4칸) */
function MedView({ med, onEdit, editRef }) {
  return (
    <>
      <div className="flex items-center gap-1">
        <h4 className="min-w-0 flex-1 break-words text-17 font-semibold">{med.name}</h4>
        <IconButton ref={editRef} icon={Pencil} label={`${med.name} 고치기`} tone="muted" onClick={onEdit} />
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3.5 pr-2 sm:grid-cols-4">
        {medFields.map(([k, label]) => (
          <div key={k} className="flex min-w-0 flex-col gap-0.5">
            <dt className="text-13 text-muted">{fieldLabel(med, k, label)}</dt>
            <dd><Value v={med[k]} missing={isMissing(med, k)} /></dd>
          </div>
        ))}
      </dl>
    </>
  );
}

const CUSTOM = '직접 입력'; // 드롭다운 맨 아래 항목 — 고르면 글 입력칸이 나와요
const INPUT_BOX = 'h-13 w-full rounded-md border border-edge/50 bg-surface px-4 text-16 text-ink placeholder:text-faint hover:border-edge/70 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand-soft';

/**
 * 드롭다운 + 직접 입력 — 용법(식전 30분·식후 30분·필요시)과 바르는 양(적당량(얇게))에 써요.
 * '직접 입력'을 고르면 아래에 글 입력칸이 나와요. 드롭다운 값에서 바꾸면 그 글을 입력칸에 넣어 둬서 조금만 고칠 수 있어요.
 */
function ChoiceField({ label, name, value, mode, options, onChange, helper, maxLength, placeholder }) {
  const inputRef = useRef(null);
  const switchedToCustom = useRef(false);
  useEffect(() => {
    if (mode === 'custom' && switchedToCustom.current) inputRef.current?.focus();
    switchedToCustom.current = false;
  }, [mode]);
  const pick = (e) => {
    const picked = e.target.value;
    if (picked === CUSTOM) {
      switchedToCustom.current = true;
      onChange({ value, mode: 'custom' });
    } else {
      onChange({ value: picked, mode: 'select' });
    }
  };
  return (
    <div className={`flex flex-col gap-2 ${mode === 'custom' ? 'col-span-2' : ''}`}>
      <SelectField
        label={label}
        name={name}
        value={mode === 'custom' ? CUSTOM : value}
        onChange={pick}
        options={[...options, CUSTOM]}
        helper={mode === 'custom' ? undefined : helper}
      />
      {mode === 'custom' && (
        <>
          <input
            ref={inputRef}
            aria-label={`${label} 직접 입력`}
            value={value}
            onChange={(e) => onChange({ value: e.target.value, mode: 'custom' })}
            maxLength={maxLength}
            placeholder={placeholder}
            className={INPUT_BOX}
          />
          {helper && <p className="text-13 text-muted">{helper}</p>}
        </>
      )}
    </div>
  );
}

/** 고치기 상태 — 같은 카드 안에서 입력칸으로 바뀌어요. 저장하면 '확인 필요' 표시가 사라져요 */
function MedEdit({ med, onSave, onCancel, onDelete }) {
  const [draft, setDraft] = useState(() => ({
    name: med.name,
    ...Object.fromEntries(medFields.map(([k]) => [k, med[k].value])),
  }));
  const [usage, setUsage] = useState(() => ({ value: med.timing.value, mode: usageMode(med.timing) }));
  // 바르는 양 — 지금은 먹는 약이어도 이름을 '○○연고'로 고치면 바로 쓸 수 있게 기본값을 들고 있어요.
  const [amount, setAmount] = useState(() =>
    isTopical(med) && med.dose.value
      ? { value: med.dose.value, mode: med.dose.mode ?? (med.dose.value === TOPICAL_DOSE_DEFAULT ? 'select' : 'custom') }
      : { value: TOPICAL_DOSE_DEFAULT, mode: 'select' },
  );
  const [error, setError] = useState('');
  const formRef = useRef(null);
  // 고치는 중인 약 이름으로 단위와 바르는 약인지를 다시 짐작해요(새로 추가하는 약은 이름을 적어야 알 수 있어요).
  const editing = { ...med, name: draft.name };
  const guessedUnit = cardDoseUnit(editing);
  const topical = isTopical(editing);

  useEffect(() => {
    formRef.current?.querySelector('input')?.focus();
  }, []);

  const set = (k) => (e) => {
    const value = e.target.value;
    setDraft((d) => ({ ...d, [k]: value }));
    if (k === 'name') setError('');
  };
  const submit = (e) => {
    e.preventDefault();
    const name = draft.name.trim();
    if (!name) {
      setError('약 이름을 적어 주세요.');
      formRef.current?.querySelector('input')?.focus();
      return;
    }
    onSave({
      ...med,
      name,
      isNew: false,
      ...Object.fromEntries(medFields.map(([k]) => [k, { value: draft[k].trim() }])),
      timing: { value: usage.value.trim(), mode: usage.mode },
      ...(topical ? { dose: { value: amount.value.trim(), mode: amount.mode } } : {}),
    });
  };

  return (
    <form ref={formRef} onSubmit={submit} className="flex flex-col gap-4 py-1 pr-2" aria-label={med.isNew ? '새 약 추가' : `${med.name} 고치기`}>
      <Field label="약 이름" value={draft.name} onChange={set('name')} error={error} placeholder="예: 아목시실린 건조시럽" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {medFields.map(([k, label]) => (k === 'timing' ? (
          <ChoiceField
            key={k}
            label={label}
            name={k}
            value={usage.value}
            mode={usage.mode}
            options={USAGE_OPTIONS}
            onChange={setUsage}
            maxLength={USAGE_MAX_LENGTH}
            placeholder="예: 1일 3회 식후 즉시, 자기 전"
            helper={med[k].low ? '흐릿하게 읽혔어요' : undefined}
          />
        ) : k === 'dose' && topical ? (
          <ChoiceField
            key={k}
            label="바르는 양"
            name={k}
            value={amount.value}
            mode={amount.mode}
            options={TOPICAL_DOSE_OPTIONS}
            onChange={setAmount}
            maxLength={TOPICAL_DOSE_MAX_LENGTH}
            placeholder="예: 손가락 한 마디만큼"
            helper="바르는 약은 양을 숫자로 적지 않아도 돼요"
          />
        ) : (
          <Field
            key={k}
            label={label}
            name={k}
            value={draft[k]}
            onChange={set(k)}
            placeholder={k === 'dose' ? '예: 5mL' : undefined}
            helper={med[k].low ? '흐릿하게 읽혔어요' : k === 'dose' && guessedUnit ? `숫자만 적어도 돼요 (단위 ${guessedUnit})` : undefined}
          />
        )))}
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
        {onDelete && (
          <button type="button" onClick={onDelete} className="-ml-2 mr-auto inline-flex min-h-11 items-center gap-1.5 rounded-md px-2 text-14 font-medium text-danger hover:bg-danger-soft">
            <Trash2 size={18} strokeWidth={1.75} aria-hidden />
            이 약 빼기
          </button>
        )}
        <div className="ml-auto flex gap-2">
          <Button variant="secondary" className="h-11 px-4 text-15" onClick={onCancel}>취소</Button>
          <Button type="submit" className="h-11 px-5 text-15">저장</Button>
        </div>
      </div>
    </form>
  );
}

/** 약 카드 — 바탕 surface, 테두리, 모서리 14. 고치는 중에는 브랜드 테두리 */
export function MedCard({ med, onChange, onRemove, onEditingChange }) {
  const [editing, setEditing] = useState(!!med.isNew);
  const cardRef = useRef(null);
  const editRef = useRef(null);
  const restoreFocus = useRef(false);

  useEffect(() => {
    onEditingChange?.(med.id, editing);
    return () => onEditingChange?.(med.id, false);
  }, [med.id, editing, onEditingChange]);

  useEffect(() => {
    if (med.isNew) cardRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [med.isNew]);

  useEffect(() => {
    if (!editing && restoreFocus.current) {
      editRef.current?.focus();
      restoreFocus.current = false;
    }
  }, [editing]);

  const close = () => {
    restoreFocus.current = true;
    setEditing(false);
  };
  const cancel = () => (med.isNew ? onRemove() : close());
  const save = (next) => {
    onChange(next);
    close();
  };

  // 흐릿하게 읽혔거나 채워야 할 칸이 있으면 카드 왼쪽에 노란 띠를 둘러요.
  const low = medFields.some(([k]) => med[k].low || isMissing(med, k));
  return (
    <li
      ref={cardRef}
      className={`relative flex scroll-mt-24 flex-col gap-3 pb-4 pl-4 pr-2 pt-3 lg:pl-5 ${
        editing ? 'bg-surface ring-2 ring-inset ring-brand' : low ? 'bg-surface before:absolute before:inset-y-0 before:left-0 before:w-1 before:bg-mark' : 'bg-surface'
      }`}
    >
      {editing ? (
        <MedEdit med={med} onSave={save} onCancel={cancel} onDelete={med.isNew ? undefined : onRemove} />
      ) : (
        <MedView med={med} onEdit={() => setEditing(true)} editRef={editRef} />
      )}
    </li>
  );
}

/** 약 카드 목록 + 빠진 약 추가 버튼. 모바일·데스크톱 같은 모양이고, 값 칸만 폭에 따라 2칸/4칸 */
export function MedList({ meds, onChange, onAdd, onRemove, onEditingChange }) {
  return (
    <section aria-label="약 목록" className="flex flex-col gap-3">
      <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface empty:hidden">
        {meds.map((m) => (
          <MedCard key={m.id} med={m} onChange={onChange} onRemove={() => onRemove(m.id)} onEditingChange={onEditingChange} />
        ))}
      </ul>
      <button
        type="button"
        onClick={onAdd}
        className="flex min-h-13 w-full items-center justify-center gap-2 rounded-xl border border-dashed border-edge/50 px-4 py-3 text-15 font-semibold text-brand hover:border-brand/40 hover:bg-surface"
      >
        <Plus size={20} strokeWidth={2} aria-hidden />
        빠진 약 추가하기
      </button>
    </section>
  );
}
