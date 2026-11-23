import { Check, Plus, ChevronDown } from 'lucide-react';

export function Avatar({ name, size = 28 }) {
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-brand-soft font-semibold text-brand"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.42) }}
      aria-hidden
    >
      {name[0]}
    </span>
  );
}

/** 헤더 오른쪽 아이 전환 버튼 — 높이 44, 모서리 22 */
export function ChildSwitcher({ name, onClick }) {
  return (
    <button type="button" onClick={onClick} className="inline-flex h-11 items-center gap-1.5 rounded-pill border border-line bg-surface py-2 pl-2 pr-3 hover:bg-paper" aria-label={`아이 바꾸기, 지금은 ${name}`}>
      <Avatar name={name} size={26} />
      <span className="text-15 font-semibold">{name}</span>
      <ChevronDown size={16} className="text-muted" aria-hidden />
    </button>
  );
}

/** 알레르기 선택 칩 — 패딩 11/14, 모서리 22 */
export function SelectChip({ selected, add, children, ...props }) {
  return (
    <button
      type="button"
      aria-pressed={add ? undefined : selected}
      className={`inline-flex items-center gap-1.5 rounded-pill border px-3.5 py-[11px] text-14 ${selected ? 'border-brand bg-brand-soft font-semibold text-brand' : 'border-line bg-surface font-medium text-ink hover:bg-paper'}`}
      {...props}
    >
      {selected && <Check size={16} strokeWidth={2.25} aria-hidden />}
      {add && <Plus size={16} strokeWidth={2} className="text-muted" aria-hidden />}
      {children}
    </button>
  );
}

/** 기록 화면 필터 칩 — 선택 시 잉크 배경 */
export function FilterChip({ selected, children, ...props }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={`rounded-pill px-4 py-2.5 text-14 font-semibold ${selected ? 'bg-ink text-on-brand' : 'border border-line bg-surface text-ink hover:bg-paper'}`}
      {...props}
    >
      {children}
    </button>
  );
}

/** 아이 선택 세그먼트 — 바깥 패딩 4 / 모서리 12, 안쪽 모서리 9 */
export function Segmented({ options, value, onChange, label }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex gap-1 rounded-lg bg-sunk p-1">
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange?.(o.value)}
            className={`flex-1 rounded-sm py-[11px] text-15 ${on ? 'bg-surface font-semibold text-ink' : 'font-medium text-muted'}`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function Tag({ children, tone = 'muted' }) {
  return (
    <span className={`inline-flex shrink-0 items-center rounded-[14px] bg-sunk px-2.5 py-1.5 text-13 font-semibold tracking-normal ${tone === 'faint' ? 'text-faint' : 'text-muted'}`}>
      {children}
    </span>
  );
}

const PANEL_TONES = {
  default: 'rounded-xl border border-line bg-surface',
  // 화면의 핵심 카드 — 테두리 대신 그림자로 띄우고 모서리를 더 둥글게
  raised: 'rounded-[20px] bg-surface shadow-card',
};

/** 흰 바탕 + 테두리 + 모서리 14 목록 패널. 행 사이는 위쪽 1px 선. tone="raised"는 화면의 핵심 카드용 */
export function Panel({ className = '', tone = 'default', children, as: As = 'div', ...props }) {
  return (
    <As className={`overflow-hidden ${PANEL_TONES[tone]} ${className}`} {...props}>
      {children}
    </As>
  );
}

export function SectionLabel({ children, className = '' }) {
  return <p className={`text-14 font-medium text-muted ${className}`}>{children}</p>;
}

export function Logo({ size = 28 }) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden>
        <g transform="rotate(-38 14 14)">
          <path d="M14 9H9a5 5 0 0 0 0 10h5z" fill="#0E5A4F" />
          <path d="M14 9h5a5 5 0 0 1 0 10h-5z" fill="#FFDD5C" />
        </g>
      </svg>
      <span className="font-bold tracking-[-0.02em] text-brand" style={{ fontSize: size * 0.7 }}>PillyMate</span>
    </span>
  );
}

/** 켜고 끄는 스위치 — 52×30, 켜지면 브랜드 색. 라벨은 aria-labelledby나 aria-label로 붙여요. */
export function Switch({ checked, onChange, disabled, className = '', ...props }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-[30px] w-[52px] shrink-0 items-center rounded-pill transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${checked ? 'bg-brand' : 'bg-line'} ${className}`}
      {...props}
    >
      <span className={`inline-block size-6 rounded-full bg-surface shadow transition-transform duration-200 ${checked ? 'translate-x-[25px]' : 'translate-x-[3px]'}`} />
    </button>
  );
}
