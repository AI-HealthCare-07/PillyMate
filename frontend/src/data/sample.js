// 화면 확인용 예시 데이터예요. 실제 의학 정보가 아니니 API 응답으로 바꿔 주세요.
export const children = [
  { id: 'c1', name: '지우', birth: '2022.03.14', age: '만 4세', weight: '16.2kg', allergies: [], allergy: null, note: '' },
  { id: 'c2', name: '서준', birth: '2019.05.02', age: '만 7세', weight: '23.0kg', allergies: ['페니실린'], allergy: '페니실린 알레르기', note: '' },
];

// low: OCR 신뢰도가 낮아 보호자 확인이 필요한 값
export const meds = [
  { id: 'm1', name: '아목시실린 건조시럽', dose: { value: '6mL' }, perDay: { value: '3번' }, days: { value: '7일' }, timing: { value: '식후 30분' } },
  { id: 'm2', name: '이부프로펜 시럽', dose: { value: '5mL', low: true }, perDay: { value: '열날 때, 최대 4번' }, days: { value: '필요할 때' }, timing: { value: '6시간 넘게 띄워서' } },
  { id: 'm3', name: '세티리진 시럽', dose: { value: '2.5mL' }, perDay: { value: '1번', low: true }, days: { value: '7일' }, timing: { value: '자기 전' } },
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
  isoDate: '2026-11-18',
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
    { name: '아목시실린 건조시럽', how: '계량컵이나 주사기로 6mL를 재서 먹여요. 나아 보여도 7일 동안 끝까지 먹여야 해요.', note: '냉장 보관하고, 먹이기 전에 흔들어 주세요.' },
    { name: '이부프로펜 시럽', how: '38도가 넘는 열이 날 때만 5mL를 먹여요. 하루 4번을 넘기지 마세요.', note: '빈속보다는 무언가 먹은 뒤에 주면 속이 편해요.' },
    { name: '세티리진 시럽', how: '자기 전에 2.5mL를 먹여요.', note: '졸음이 올 수 있어요.' },
  ],
  life: ['물을 자주 마시게 해 주세요.', '코를 세게 풀지 않게 해 주세요.', '귀를 만지거나 아파하면 시간과 함께 적어 두세요.'],
  danger: ['39도가 넘는 열이 이틀 넘게 이어질 때', '두드러기가 나거나 숨쉬기 힘들어할 때', '귀에서 진물이나 피가 날 때', '물을 거의 못 마시고 소변이 줄었을 때'],
};

// 건강기록 — 병원에 간 날, 병원, 진단, 처방받은 약(며칠분).
// source: 'ocr'은 처방 올리기에서 처방전을 읽어 자동으로 남긴 기록, 'manual'은 보호자가 직접 남긴 기록.
// status가 있으면 앱에서 처방 내용을 아직 확인하지 않은 기록이에요.
export const visits = [
  { id: 'v1', childId: 'c1', date: '2026-11-18', hospital: '튼튼소아청소년과', title: '중이염', meds: [{ name: '아목시실린 건조시럽', days: '7일' }, { name: '이부프로펜 시럽', days: '필요할 때' }, { name: '세티리진 시럽', days: '7일' }], note: '', source: 'ocr' },
  { id: 'v2', childId: 'c2', date: '2026-11-09', hospital: '바른이비인후과', title: '감기', meds: [{ name: '해열 시럽', days: '3일' }, { name: '기침 시럽', days: '3일' }], note: '', source: 'ocr', status: '확인 전' },
  { id: 'v3', childId: 'c1', date: '2026-10-02', hospital: '튼튼소아청소년과', title: '장염', meds: [{ name: '정장제 가루약', days: '3일' }, { name: '구토 억제 시럽', days: '3일' }], note: '이틀 동안 설사', source: 'ocr' },
  { id: 'v4', childId: 'c2', date: '2026-09-14', hospital: '하늘소아과', title: '예방접종', meds: [], note: '독감 1차', source: 'manual' },
];

// 복약 일정 — 처방을 확인하고 가이드를 만든 뒤 생겨요. start부터 days일 동안 schedule대로 먹여요.
export const courses = [
  { id: 'k1', childId: 'c1', visitId: 'v1', title: '중이염', hospital: '튼튼소아청소년과', start: '2026-11-18', days: 7, schedule: guide.schedule },
  {
    id: 'k2', childId: 'c1', visitId: 'v3', title: '장염', hospital: '튼튼소아청소년과', start: '2026-10-02', days: 3,
    schedule: [
      { slot: '아침', items: [['정장제', '1포'], ['구토 억제 시럽', '3mL']] },
      { slot: '저녁', items: [['정장제', '1포'], ['구토 억제 시럽', '3mL']] },
    ],
  },
];

// 예시 복약 체크 — 날짜까지 지난 일정은 대부분 먹인 것으로, 몇 번은 빼먹은 것으로 채워요.
export const sampleMissed = ['c1|2026-11-20|점심|아목시실린', 'c1|2026-11-21|자기 전|세티리진', 'c1|2026-10-03|저녁|구토 억제 시럽'];

export const chat = {
  childName: '지우',
  context: '11월 18일 중이염',
  messages: [
    { id: 'q0', from: 'bot', text: '안녕하세요, 지우 보호자님. 11월 18일에 받은 중이염 약에 대해 궁금한 걸 물어보세요.' },
    { id: 'q1', from: 'me', text: '이부프로펜은 언제 다시 먹일 수 있어요?' },
    { id: 'q2', from: 'bot', text: '처방 내용으로는 열이 날 때만 5mL를 먹이고, 다음 번까지 6시간 넘게 띄우라고 되어 있어요.\n하루 4번을 넘기지 마세요.' },
  ],
  suggestions: ['약을 먹고 토했어요', '시럽은 어떻게 보관해요?', '아목시실린을 빼먹었어요'],
  demoReply: '지금은 화면 확인용 예시 답변이에요. 정확한 내용은 약사나 의사에게 꼭 물어봐 주세요.',
};

