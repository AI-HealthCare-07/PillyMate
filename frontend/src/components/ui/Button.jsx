import { forwardRef } from 'react';

const variants = {
  primary: 'bg-brand text-on-brand hover:bg-brand-hover active:bg-brand-active',
  secondary: 'bg-surface text-ink border border-edge/60 hover:bg-paper active:bg-sunk',
  disabled: 'bg-sunk text-muted cursor-not-allowed',
};

/** Figma: Button/Primary · Secondary · Disabled — 높이 52, 가로 패딩 20, 모서리 12, 16px SemiBold */
export function Button({ variant = 'primary', className = '', disabled, children, ...props }) {
  const v = disabled ? 'disabled' : variant;
  // 화면에서 높이(h-*)를 넘기면 그 값을 써요. 기본은 52px.
  const height = /(^|\s)h-/.test(className) ? '' : 'h-13';
  return (
    <button
      type="button"
      disabled={disabled}
      className={`inline-flex ${height} items-center justify-center rounded-lg px-5 text-16 font-semibold tracking-[-0.01em] transition-colors ${variants[v]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

/** 작은 테두리 버튼 (다시 찍기, 앨범, 원본 등) — 패딩 10/12, 모서리 10, 14px Medium */
export function SmallButton({ icon: Icon, children, className = '', ...props }) {
  return (
    <button
      type="button"
      className={`inline-flex min-h-11 items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-2.5 text-14 font-medium text-ink hover:bg-paper ${className}`}
      {...props}
    >
      {Icon && <Icon size={18} strokeWidth={1.75} aria-hidden />}
      {children}
    </button>
  );
}

/** 44px 아이콘 버튼 — 패딩 10, 모서리 10 */
export const IconButton = forwardRef(function IconButton({ icon: Icon, label, tone = 'ink', className = '', ...props }, ref) {
  return (
    <button
      ref={ref}
      type="button"
      aria-label={label}
      className={`inline-flex size-11 shrink-0 items-center justify-center rounded-md hover:bg-sunk ${tone === 'muted' ? 'text-muted' : 'text-ink'} ${className}`}
      {...props}
    >
      <Icon size={24} strokeWidth={1.75} aria-hidden />
    </button>
  );
});
