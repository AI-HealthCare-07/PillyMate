import { useEffect, useRef, useState } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { Button, IconButton } from '../ui/Button.jsx';
import { Field } from '../ui/Field.jsx';
import { LowValue } from './Highlight.jsx';
import { medFields } from '../../data/sample.js';

/** 새로 추가하는 약의 빈 값 */
export const emptyMed = () => ({
  id: crypto.randomUUID(),
  name: '',
  isNew: true,
  ...Object.fromEntries(medFields.map(([k]) => [k, { value: '' }])),
});

function Value({ v }) {
  if (!v.value) return <span className="text-16 text-faint">—</span>;
  if (v.low) return <LowValue value={v.value} stacked size="text-16" />;
  return <span className="text-16 font-medium">{v.value}</span>;
}

/** 보기 상태 — 약 이름 17 SemiBold + 값 칸(모바일 2×2, 데스크톱 4칸) */
function MedView({ med, onEdit, editRef }) {
  return (
    <>
      <div className="flex items-center gap-1">
        <h4 className="flex-1 text-17 font-semibold">{med.name}</h4>
        <IconButton ref={editRef} icon={Pencil} label={`${med.name} 고치기`} tone="muted" onClick={onEdit} />
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-3 pr-2 sm:grid-cols-4">
        {medFields.map(([k, label]) => (
          <div key={k} className="flex flex-col gap-0.5">
            <dt className="text-13 text-muted">{label}</dt>
            <dd><Value v={med[k]} /></dd>
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
    <form ref={formRef} onSubmit={submit} className="flex flex-col gap-4 pr-2" aria-label={med.isNew ? '새 약 추가' : `${med.name} 고치기`}>
      <Field label="약 이름" value={draft.name} onChange={set('name')} error={error} placeholder="예: 아목시실린 건조시럽" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {medFields.map(([k, label]) => (
          <Field
            key={k}
            label={label}
            name={k}
            value={draft[k]}
            onChange={set(k)}
            helper={med[k].low ? '흐릿하게 읽혔어요' : undefined}
          />
        ))}
      </div>
      <div className="flex items-center gap-2">
        {onDelete && (
          <button type="button" onClick={onDelete} className="mr-auto inline-flex items-center gap-1.5 rounded-md px-2 py-2.5 text-14 font-medium text-danger hover:bg-danger-soft">
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

  const low = medFields.some(([k]) => med[k].low);
  return (
    <li
      ref={cardRef}
      className={`flex flex-col gap-3 rounded-xl border bg-surface pb-4 pl-4 pr-2 pt-3 ${
        editing ? 'border-brand ring-2 ring-brand/15' : low ? 'border-mark' : 'border-line'
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
      <ul className="flex flex-col gap-3">
        {meds.map((m) => (
          <MedCard key={m.id} med={m} onChange={onChange} onRemove={() => onRemove(m.id)} onEditingChange={onEditingChange} />
        ))}
      </ul>
      <button
        type="button"
        onClick={onAdd}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-brand/40 bg-surface px-4 py-4 text-15 font-semibold text-brand hover:bg-brand-soft"
      >
        <Plus size={20} strokeWidth={2} aria-hidden />
        빠진 약 추가하기
      </button>
    </section>
  );
}
