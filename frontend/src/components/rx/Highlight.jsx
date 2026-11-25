/**
 * 흐릿하게 읽힌 값 표시 — 글자 아래쪽 58%를 덮는 1.2° 기울어진 형광펜.
 * 색만으로 구분하지 않도록 '확인 필요' 라벨을 함께 붙여요.
 */
export function Highlight({ children, className = '' }) {
  return (
    <span className={`relative inline-block px-1 font-semibold text-mark-ink ${className}`}>
      <span aria-hidden className="absolute inset-x-0 bottom-[2px] top-[42%] rotate-[1.2deg] rounded-[2px] bg-mark" />
      <span className="relative">{children}</span>
    </span>
  );
}

export function LowValue({ value, stacked = false, size = 'text-16' }) {
  return (
    <span className={`flex ${stacked ? 'flex-col items-start gap-0.5' : 'items-center gap-1.5'}`}>
      <Highlight className={size}>{value}</Highlight>
      <span className="text-12 font-semibold text-mark-ink">확인 필요</span>
    </span>
  );
}

/** 안내 배너 — 패딩 12/14, 모서리 12, 연노랑 바탕 */
export function LowConfidenceBanner({ count }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-mark bg-mark-soft px-4 py-3 sm:items-center" role="note">
      <Highlight className="shrink-0 text-14">노란 표시</Highlight>
      <p className="text-14 text-mark-ink">{count}곳은 글자가 흐릿하게 읽혔어요. 처방전과 같은지 봐 주세요.</p>
    </div>
  );
}
