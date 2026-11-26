import { useEffect, useRef, useState } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { Button, IconButton } from '../ui/Button.jsx';
import { Field, SelectField } from '../ui/Field.jsx';
import { Highlight, LowValue } from './Highlight.jsx';
import { medFields } from '../../data/sample.js';
import { TAKING_TIME_OPTIONS, toTakingTimeOption } from '../../data/takingTimeOptions.js';
import { isAsNeeded } from '../../state/records.jsx';
import { cardDoseUnit, withDoseUnit } from '../../api/prescriptionConfirm.js';

/** 새로 추가하는 약의 빈 값 */
export const emptyMed = () => ({
  id: crypto.randomUUID(),
  name: '',
  isNew: true,
  ...Object.fromEntries(medFields.map(([k]) => [k, { value: '' }])),
});

/**
 * 읽은 값을 보호자가 손대지 않아도 되게 다듬어요 — 처음 불러올 때와 저장할 때 써요.
 * - 1회 양이 숫자뿐이면('5') OCR 단위나 약 이름·제형으로 짐작한 단위를 붙여요('5mL').
 * - 먹는 때는 드롭다운의 세 가지(식전 30분·식후 30분·필요시) 중 가장 가까운 것으로 바꿔요.
 */
export function fillGuessedFields(med) {
  const doseText = med.dose?.value ?? '';
  const dose = withDoseUnit(doseText, cardDoseUnit(med));
  const timing = toTakingTimeOption(med.timing?.value, isAsNeeded(med));
  return {
    ...med,
    dose: dose === doseText ? med.dose : { ...med.dose, value: dose },
    timing: timing === (med.timing?.value ?? '') ? med.timing : { ...med.timing, value: timing },
  };
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
            <dt className="text-13 text-muted">{label}</dt>
            <dd><Value v={med[k]} missing={isMissing(med, k)} /></dd>
          </div>
        ))}
      </dl>
    </>
  );
}

/** 고치기 상태 — 같은 카드 안에서 입력칸으로 바뀌어요. 저장하면 '확인 필요' 표시가 사라져요 */
function MedEdit({ med, onSave, onCancel, onDelete }) {
  const [draft, setDraft] = useState(() => ({
    name: med.name,
    ...Object.fromEntries(medFields.map(([k]) => [k, med[k].value])),
  }));
  const [error, setError] = useState('');
  const formRef = useRef(null);
  // 고치는 중인 약 이름으로 단위를 다시 짐작해요(새로 추가하는 약은 이름을 적어야 알 수 있어요).
  const guessedUnit = cardDoseUnit({ ...med, name: draft.name });

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
    });
  };

  return (
    <form ref={formRef} onSubmit={submit} className="flex flex-col gap-4 py-1 pr-2" aria-label={med.isNew ? '새 약 추가' : `${med.name} 고치기`}>
      <Field label="약 이름" value={draft.name} onChange={set('name')} error={error} placeholder="예: 아목시실린 건조시럽" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {medFields.map(([k, label]) => (k === 'timing' ? (
          <SelectField
            key={k}
            label={label}
            name={k}
            value={draft[k]}
            onChange={set(k)}
            options={TAKING_TIME_OPTIONS}
            helper={med[k].low ? '흐릿하게 읽혔어요' : undefined}
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
