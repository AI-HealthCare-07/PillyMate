/** PillyMate design tokens — Figma "PillyMate color" 변수와 1:1로 맞춘 값 */
const t = (size, lh, ls) => [`${size}px`, { lineHeight: lh, letterSpacing: ls }];

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      // Warm Parenting Healthcare — 공통 디자인 토큰. 화면에서는 이 이름만 쓰고 색 값을 직접 쓰지 않아요.
      // 텍스트 조합은 WCAG AA(4.5:1) 확인. sage·plum·terra 기본값은 대비가 낮아 장식/배경에만 써요.
      colors: {
        paper: '#F9F6F0',     // 전체 배경
        surface: '#FFFDF9',   // 콘텐츠 배경
        sunk: '#EFE5D5',      // 웜 베이지 — 눌린 칸, 세그먼트 바탕
        ink: '#302923',       // 기본 텍스트
        muted: '#6B6560',     // 보조 텍스트 (#77716B는 AA 미달이라 보정)
        faint: '#726C66',     // 옅은 텍스트 — paper/surface 위에서만
        line: '#E5DED3',      // 구분선
        edge: '#8C8279',      // 체크 원·체크박스 테두리 (비텍스트 3:1)
        brand: { DEFAULT: '#34482E', hover: '#2A3A25', active: '#22301E', soft: '#E3E7D3' }, // 딥 올리브 / 라이트 세이지
        'on-brand': '#FFFDF9',
        sage: '#8D9D66',      // 장식·진행 막대 등 보조
        mark: { DEFAULT: '#F9E5BB', soft: '#FAF0DE', ink: '#7A5214' }, // 버터·크림 옐로 — 처방 등록, 확인 필요
        terra: { DEFAULT: '#AB6B50', ink: '#96593F' },                 // 감성 안내 문구
        lav: { DEFAULT: '#EBE2EF', plum: '#95819F', ink: '#6B5878' },  // AI 상담
        ok: '#52654C',        // 상태: 복약 완료
        warn: '#98651E',      // 상태: 확인 필요 (surface/paper 위)
        danger: { DEFAULT: '#A3332C', hover: '#862821', soft: '#F8E5E0' }, // 상태: 의료 경고
      },
      fontFamily: {
        sans: ['"IBM Plex Sans KR"', 'system-ui', '-apple-system', 'sans-serif'],
      },
      // Figma 텍스트 규칙: 22px 이상 132%, 17px 이상 140%, 그 외 150% / 20px 이상 -2%, 그 외 -0.5%
      fontSize: {
        12: t(12, '1.5', '0'),
        13: t(13, '1.5', '-0.005em'),
        14: t(14, '1.5', '-0.005em'),
        15: t(15, '1.5', '-0.005em'),
        16: t(16, '1.5', '-0.005em'),
        17: t(17, '1.4', '-0.005em'),
        18: t(18, '1.4', '-0.005em'),
        20: t(20, '1.4', '-0.02em'),
        22: t(22, '1.32', '-0.02em'),
        24: t(24, '1.32', '-0.02em'),
        28: t(28, '1.32', '-0.02em'),
        32: t(32, '1.32', '-0.02em'),
      },
      borderRadius: {
        sm: '8px',   // 세그먼트 안쪽
        md: '10px',  // 입력칸, 아이콘 버튼, 작은 버튼
        lg: '12px',  // 버튼, 안내 배너, 일정 칸
        xl: '16px',  // 패널
        '2xl': '20px', // 화면의 핵심 카드
        pill: '999px',
      },
      spacing: { 13: '52px', 17: '68px' },
      maxWidth: { content: '1120px', screen: '390px', form: '560px', reading: '720px' },
      // card: 화면의 핵심 카드(오늘 먹을 약) / raised: 떠 있는 메뉴 / paper: 처방전 그림
      boxShadow: {
        paper: '0 4px 14px rgba(48, 41, 35, 0.10)',
        card: '0 1px 2px rgba(48, 41, 35, 0.05)',
        raised: '0 12px 32px rgba(48, 41, 35, 0.14)',
      },
    },
  },
  plugins: [],
};
