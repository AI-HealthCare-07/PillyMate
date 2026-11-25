import { useId } from 'react';

/** Figma: Field — 라벨 14 Medium, 칸 높이 52 / 모서리 10 / 가로 16, 도움말 13. multiline이면 높이 104 */
export function Field({ label, helper, error, multiline = false, className = '', inputClassName = '', ...props }) {
  const id = useId();
  const helpId = `${id}-help`;
  const box = 'w-full rounded-md border bg-surface px-4 text-16 text-ink placeholder:text-faint hover:border-edge/70 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand-soft';
  const border = error ? 'border-danger' : 'border-edge/50';
  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <label htmlFor={id} className="text-14 font-semibold text-ink">{label}</label>
      {multiline ? (
        <textarea id={id} rows={3} aria-describedby={helper || error ? helpId : undefined} className={`${box} ${border} h-[104px] resize-none py-3.5 ${inputClassName}`} {...props} />
      ) : (
        <input id={id} aria-describedby={helper || error ? helpId : undefined} aria-invalid={!!error} className={`${box} ${border} h-13 ${inputClassName}`} {...props} />
      )}
      {(error || helper) && (
        <p id={helpId} className={`text-13 ${error ? 'text-danger' : 'text-muted'}`}>{error || helper}</p>
      )}
    </div>
  );
}
