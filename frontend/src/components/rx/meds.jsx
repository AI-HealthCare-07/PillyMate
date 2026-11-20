import { Pencil, Plus } from 'lucide-react';
import { IconButton } from '../ui/Button.jsx';
import { Panel } from '../ui/misc.jsx';
import { LowValue } from './Highlight.jsx';
import { medFields } from '../../data/sample.js';

function Value({ v, desktop }) {
  if (v.low) return <LowValue value={v.value} stacked={desktop} size={desktop ? 'text-15' : 'text-16'} />;
  return <span className={`${desktop ? 'text-15' : 'text-16'} font-medium`}>{v.value}</span>;
}

function AddMed({ onAdd, center }) {
  return (
    <button type="button" onClick={onAdd} className={`flex w-full items-center gap-2 border-t border-line px-4 py-3.5 text-15 font-semibold text-brand hover:bg-paper ${center ? 'justify-center' : ''}`}>
      <Plus size={20} strokeWidth={2} aria-hidden />
      빠진 약 추가하기
    </button>
  );
}

/** 모바일 약 목록 — 행마다 약 이름 17 SemiBold + 2×2 값 칸 (라벨 13, 값 16 Medium) */
export function MedList({ meds, onEdit, onAdd }) {
  return (
    <Panel as="section" aria-label="약 목록">
      <ul>
        {meds.map((m, j) => (
          <li key={m.id} className={`flex flex-col gap-2.5 pb-4 pl-4 pr-2 pt-3.5 ${j ? 'border-t border-line' : ''}`}>
            <div className="flex items-center gap-1">
              <h3 className="flex-1 text-17 font-semibold">{m.name}</h3>
              <IconButton icon={Pencil} label={`${m.name} 고치기`} tone="muted" onClick={() => onEdit?.(m)} />
            </div>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-2.5 pr-2">
              {medFields.map(([k, label]) => (
                <div key={k} className="flex flex-col gap-0.5">
                  <dt className="text-13 text-muted">{label}</dt>
                  <dd><Value v={m[k]} /></dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
      <AddMed onAdd={onAdd} center />
    </Panel>
  );
}

/** 데스크톱 약 표 — 이름 칸 200, 값 칸 균등, 수정 버튼 44 */
export function MedTable({ meds, onEdit, onAdd }) {
  return (
    <Panel as="section" aria-label="약 목록">
      <table className="w-full table-fixed border-collapse text-left">
        <colgroup>
          <col className="w-[216px]" />
          {medFields.map(([k]) => <col key={k} />)}
          <col className="w-[60px]" />
        </colgroup>
        <thead className="bg-sunk">
          <tr>
            <th scope="col" className="py-2.5 pl-4 text-13 font-medium text-muted">약 이름</th>
            {medFields.map(([k, label]) => (
              <th key={k} scope="col" className="py-2.5 pl-3 text-13 font-medium text-muted">{label}</th>
            ))}
            <th scope="col"><span className="sr-only">고치기</span></th>
          </tr>
        </thead>
        <tbody>
          {meds.map((m) => (
            <tr key={m.id} className="border-t border-line">
              <th scope="row" className="py-3 pl-4 text-15 font-semibold">{m.name}</th>
              {medFields.map(([k]) => (
                <td key={k} className="py-3 pl-3 align-middle"><Value v={m[k]} desktop /></td>
              ))}
              <td className="pr-4"><IconButton icon={Pencil} label={`${m.name} 고치기`} tone="muted" onClick={() => onEdit?.(m)} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <AddMed onAdd={onAdd} />
    </Panel>
  );
}
