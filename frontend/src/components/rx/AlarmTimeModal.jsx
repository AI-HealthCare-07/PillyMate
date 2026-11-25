import { useEffect, useId, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { Button } from '../ui/Button.jsx';
import { Modal } from '../ui/Modal.jsx';
import { SLOT_TIME, hhmm, useRecords } from '../../state/records.jsx';

const toInput = (t) => hhmm(t);
const fromInput = (v) => v.split(':').map(Number);

/**
 * 복약 알림 시간 설정 — 처방(가이드)마다 먹는 때(아침/점심/저녁/자기 전)별 알림 시각을 바꿔요.
 * 저장하면 상단 알림이 바뀐 시각 기준으로 울려요. '기본 시간으로'는 처음 시각으로 되돌려요.
 */
export function AlarmTimeModal({ open, onClose, visitId, slots, title }) {
  const { alarmTimeOf, setAlarmTimes } = useRecords();
  const [values, setValues] = useState({});
  const baseId = useId();

  // 열 때마다 지금 저장된 시각으로 채워요.
  useEffect(() => {
    if (open) setValues(Object.fromEntries(slots.map((slot) => [slot, toInput(alarmTimeOf(visitId, slot))])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const isDefault = slots.every((slot) => values[slot] === toInput(SLOT_TIME[slot] ?? [9, 0]));
  const complete = slots.every((slot) => /^\d{2}:\d{2}$/.test(values[slot] ?? ''));

  const save = () => {
    if (!complete) return;
    setAlarmTimes(visitId, isDefault ? null : Object.fromEntries(slots.map((slot) => [slot, fromInput(values[slot])])));
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="알림 시간 설정" description={title} className="max-w-[420px]">
      <form
        className="flex flex-col gap-5 p-5"
        onSubmit={(e) => {
          e.preventDefault();
          save();
        }}
      >
        <p className="text-14 text-muted">먹는 때마다 알림 받을 시간을 정해 주세요. 이 처방에만 적용돼요.</p>
        <ul className="flex flex-col divide-y divide-line rounded-lg border border-line bg-surface">
          {slots.map((slot) => {
            const id = `${baseId}-${slot}`;
            return (
              <li key={slot} className="flex min-h-[60px] items-center justify-between gap-3 px-4 py-2">
                <label htmlFor={id} className="text-15 font-semibold text-brand">{slot}</label>
                <input
                  id={id}
                  type="time"
                  step={300}
                  required
                  value={values[slot] ?? ''}
                  onChange={(e) => setValues((prev) => ({ ...prev, [slot]: e.target.value }))}
                  onClick={(e) => {
                    try {
                      e.currentTarget.showPicker?.();
                    } catch {
                      // 지원하지 않는 브라우저는 직접 입력해요.
                    }
                  }}
                  className="h-11 w-[148px] shrink-0 cursor-pointer rounded-md border border-edge/50 bg-surface px-3 text-16 tabular-nums focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
                />
              </li>
            );
          })}
        </ul>
        <button
          type="button"
          disabled={isDefault}
          onClick={() => setValues(Object.fromEntries(slots.map((slot) => [slot, toInput(SLOT_TIME[slot] ?? [9, 0])])))}
          className="-ml-2 -mt-2 inline-flex min-h-11 items-center gap-1.5 self-start rounded-md px-2 text-14 font-medium text-muted hover:bg-paper hover:text-ink disabled:opacity-40 disabled:hover:bg-transparent"
        >
          <RotateCcw size={15} strokeWidth={2} aria-hidden />기본 시간으로
        </button>
        <div className="flex flex-col-reverse gap-2 border-t border-line pt-4 sm:flex-row sm:justify-end sm:[&>button]:min-w-[120px]">
          <Button variant="secondary" onClick={onClose}>취소</Button>
          <Button type="submit" disabled={!complete}>저장하기</Button>
        </div>
      </form>
    </Modal>
  );
}
