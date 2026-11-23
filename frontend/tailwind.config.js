/** PillyMate design tokens — Figma "PillyMate color" 변수와 1:1로 맞춘 값 */
const t = (size, lh, ls) => [`${size}px`, { lineHeight: lh, letterSpacing: ls }];

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F3F5F2',
        surface: '#FFFFFF',
        sunk: '#E8ECE8',
        ink: '#16201D',
        muted: '#4B5853',
        faint: '#66726D',
        line: '#D5DCD7',
        brand: { DEFAULT: '#0E5A4F', soft: '#E0EDE8' },
        'on-brand': '#FFFFFF',
        mark: { DEFAULT: '#FFDD5C', soft: '#FFF4C4', ink: '#584000' },
        danger: { DEFAULT: '#A3261D', soft: '#FBE8E4' },
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
        sm: '9px',   // 세그먼트 안쪽
        md: '10px',  // 입력칸, 아이콘 버튼, 작은 버튼
        lg: '12px',  // 버튼, 안내 배너, 일정 칸
        xl: '14px',  // 패널
        pill: '22px',
      },
      spacing: { 13: '52px', 17: '68px' },
      maxWidth: { content: '1120px', screen: '390px', form: '480px' },
      // card: 화면의 핵심 카드(오늘 먹을 약) / raised: 떠 있는 메뉴 / paper: 처방전 그림
      boxShadow: {
        paper: '0 6px 18px rgba(13, 51, 41, 0.12)',
        card: '0 1px 2px rgba(13, 51, 41, 0.06), 0 8px 24px rgba(13, 51, 41, 0.08)',
        raised: '0 12px 32px rgba(13, 51, 41, 0.18)',
      },
    },
  },
  plugins: [],
};
