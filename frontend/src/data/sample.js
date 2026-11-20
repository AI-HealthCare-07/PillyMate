// 화면 확인용 예시 데이터예요. 실제 의학 정보가 아니니 API 응답으로 바꿔 주세요.
export const children = [
  { id: 'c1', name: '지우', age: '만 4세', weight: '16.2kg', allergy: null },
  { id: 'c2', name: '서준', age: '만 7세', weight: '23.0kg', allergy: '페니실린 알레르기' },
];

// low: OCR 신뢰도가 낮아 보호자 확인이 필요한 값
export const meds = [
  { id: 'm1', name: '아목시실린 건조시럽', dose: { value: '6mL' }, perDay: { value: '3번' }, days: { value: '5일' }, timing: { value: '식후 30분' } },
  { id: 'm2', name: '이부프로펜 시럽', dose: { value: '5mL', low: true }, perDay: { value: '열날 때, 최대 4번' }, days: { value: '필요할 때' }, timing: { value: '6시간 넘게 띄워서' } },
  { id: 'm3', name: '세티리진 시럽', dose: { value: '2.5mL' }, perDay: { value: '1번', low: true }, days: { value: '5일' }, timing: { value: '자기 전' } },
];

export const medFields = [
  ['dose', '1회 양'],
  ['perDay', '하루'],
  ['days', '기간'],
  ['timing', '먹는 때'],
];

export const prescription = {
  hospital: '튼튼소아청소년과',
  date: '2026년 11월 18일',
  shortDate: '11월 18일',
  disease: '중이염',
};

export const guide = {
  schedule: [
    { slot: '아침', items: [['아목시실린', '6mL']] },
    { slot: '점심', items: [['아목시실린', '6mL']] },
    { slot: '저녁', items: [['아목시실린', '6mL']] },
    { slot: '자기 전', items: [['세티리진', '2.5mL']] },
  ],
  asNeeded: '열날 때만 이부프로펜 5mL. 다음 번까지 6시간 넘게 띄워 주세요.',
  howTo: [
    { name: '아목시실린 건조시럽', how: '계량컵이나 주사기로 6mL를 재서 먹여요. 나아 보여도 5일 동안 끝까지 먹여야 해요.', note: '냉장 보관하고, 먹이기 전에 흔들어 주세요.' },
    { name: '이부프로펜 시럽', how: '38도가 넘는 열이 날 때만 5mL를 먹여요. 하루 4번을 넘기지 마세요.', note: '빈속보다는 무언가 먹은 뒤에 주면 속이 편해요.' },
    { name: '세티리진 시럽', how: '자기 전에 2.5mL를 먹여요.', note: '졸음이 올 수 있어요.' },
  ],
  life: ['물을 자주 마시게 해 주세요.', '코를 세게 풀지 않게 해 주세요.', '귀를 만지거나 아파하면 시간과 함께 적어 두세요.'],
  danger: ['39도가 넘는 열이 이틀 넘게 이어질 때', '두드러기가 나거나 숨쉬기 힘들어할 때', '귀에서 진물이나 피가 날 때', '물을 거의 못 마시고 소변이 줄었을 때'],
};

export const history = [
  { month: '11월', rows: [
    { id: 'h1', day: '18', weekday: '수', title: '중이염', sub: '지우, 약 3개' },
    { id: 'h2', day: '9', weekday: '월', title: '감기', sub: '서준, 약 2개', status: '확인 전' },
  ] },
  { month: '10월', rows: [{ id: 'h3', day: '2', weekday: '금', title: '장염', sub: '지우, 약 2개' }] },
];
