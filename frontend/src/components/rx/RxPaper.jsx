/**
 * 처방전 사진 자리에 쓰는 일러스트. 실제 서비스에서는 업로드한 사진(<img>)으로 바꿔 쓰세요.
 * marks: [x, y, w] (300 기준 좌표) — 흐릿하게 읽힌 자리에 형광펜 표시
 */
export function RxPaper({ width = 72, marks = [], scanning = false, className = '' }) {
  const h = Math.round((width * 380) / 300);
  const rows = [[70, 120], [64, 90], [70, 150], [64, 70]];
  return (
    <svg
      width={width}
      height={h}
      viewBox="0 0 300 380"
      role="img"
      aria-label="처방전 사진"
      className={`shrink-0 rounded-[6px] border border-line bg-surface shadow-paper ${className}`}
    >
      {marks.map(([x, y, w], i) => (
        <rect key={i} x={x - 4} y={y - 3} width={w + 8} height={14} rx={2} fill="#FFDD5C" opacity={0.85} transform={`rotate(1.2 ${x} ${y})`} />
      ))}
      <rect x={110} y={22} width={80} height={9} rx={2} fill="#16201D" opacity={0.75} />
      <rect x={24} y={52} width={252} height={1} fill="#D5DCD7" />
      {rows.map(([a, b], j) => (
        <g key={j}>
          <rect x={24} y={66 + j * 14} width={a} height={5} rx={2} fill="#66726D" opacity={0.45} />
          <rect x={110} y={66 + j * 14} width={b} height={5} rx={2} fill="#66726D" opacity={0.45} />
        </g>
      ))}
      <rect x={24} y={130} width={252} height={1} fill="#D5DCD7" />
      <rect x={24} y={140} width={252} height={16} fill="#E8ECE8" />
      {Array.from({ length: 6 }, (_, j) => {
        const y = 166 + j * 20;
        return (
          <g key={j} fill="#16201D" opacity={0.4}>
            <rect x={24} y={y} width={96} height={6} rx={2} />
            <rect x={140} y={y} width={30} height={6} rx={2} />
            <rect x={190} y={y} width={22} height={6} rx={2} />
            <rect x={232} y={y} width={30} height={6} rx={2} />
          </g>
        );
      })}
      <rect x={24} y={300} width={252} height={1} fill="#D5DCD7" />
      <rect x={24} y={314} width={140} height={5} rx={2} fill="#66726D" opacity={0.45} />
      <rect x={24} y={328} width={100} height={5} rx={2} fill="#66726D" opacity={0.45} />
      <rect x={214} y={326} width={52} height={52} rx={2} fill="#A3261D" opacity={0.22} />
      {scanning && (
        <rect x={0} y={177} width={300} height={3} fill="#0E5A4F" opacity={0.9}>
          <animate attributeName="y" values="40;340;40" dur="2.4s" repeatCount="indefinite" />
        </rect>
      )}
    </svg>
  );
}
