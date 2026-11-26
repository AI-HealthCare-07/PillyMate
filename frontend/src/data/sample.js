// 화면 확인용 예시 데이터예요. 실제 의학 정보가 아니니 API 응답으로 바꿔 주세요.
export const children = [
  { id: 'c1', name: '지우', birth: '2022.03.14', age: '만 4세', weight: '16.2kg', allergies: [], allergy: null, note: '' },
  { id: 'c2', name: '서준', birth: '2019.05.02', age: '만 7세', weight: '23.0kg', allergies: ['페니실린'], allergy: '페니실린 알레르기', note: '' },
  { id: 'c3', name: '서현', birth: '2012.04.17', age: '만 14세', weight: '48.0kg', allergies: [], allergy: null, note: '알약은 잘 삼켜요.' },
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
  ['timing', '용법'],
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
  {
    id: 'v2', childId: 'c2', date: '2026-11-09', hospital: '바른이비인후과', title: '감기', meds: [{ name: '해열 시럽', days: '3일' }, { name: '기침 시럽', days: '3일' }], note: '', source: 'ocr', status: '확인 전',
    // 처방전은 읽었지만 보호자가 아직 확인하지 않은 약 목록(데모 OCR 결과). 처방 확인 화면에 그대로 채워져요.
    ocrMeds: [
      { id: 'v2m1', name: '해열 시럽', dose: { value: '7mL' }, perDay: { value: '열날 때, 최대 4번' }, days: { value: '3일' }, timing: { value: '4시간 넘게 띄워서' } },
      { id: 'v2m2', name: '기침 시럽', dose: { value: '5mL', low: true }, perDay: { value: '3번' }, days: { value: '3일' }, timing: { value: '식후 30분' } },
    ],
  },
  { id: 'v3', childId: 'c1', date: '2026-10-02', hospital: '튼튼소아청소년과', title: '장염', meds: [{ name: '정장제 가루약', days: '3일' }, { name: '구토 억제 시럽', days: '3일' }], note: '이틀 동안 설사', source: 'ocr' },
  { id: 'v4', childId: 'c2', date: '2026-09-14', hospital: '하늘소아과', title: '예방접종', meds: [], note: '독감 1차', source: 'manual' },
  { id: 'v6', childId: 'c3', date: '2026-11-22', hospital: '연세가정의학과', title: '독감(A형)', meds: [{ name: '오셀타미비르 캡슐 75mg', days: '5일' }, { name: '암브록솔 정 30mg', days: '5일' }, { name: '레바미피드 정 100mg', days: '5일' }, { name: '아세트아미노펜 정 500mg', days: '필요할 때' }], note: '신속항원검사 A형 양성, 38.9도', source: 'ocr' },
  { id: 'v5', childId: 'c2', date: '2026-11-22', hospital: '하늘소아과', title: '수족구', meds: [{ name: '이부프로펜 시럽', days: '3일' }, { name: '아세트아미노펜 시럽', days: '필요할 때' }, { name: '세티리진 시럽', days: '5일' }], note: '입안 물집, 손발 발진', source: 'ocr' },
];

// 서준 수족구(11월 22일 처방) — 입안 통증 때문에 진통제를 정해진 때 먹이고, 열은 따로 해열제로 잡아요.
const hfmdSchedule = [
  { slot: '아침', items: [['이부프로펜 시럽', '10mL', 3]] },
  { slot: '점심', items: [['이부프로펜 시럽', '10mL', 3]] },
  { slot: '저녁', items: [['이부프로펜 시럽', '10mL', 3]] },
  { slot: '자기 전', items: [['세티리진 시럽', '5mL', 5]] },
];

// 서현 독감(11월 22일 처방) — 중학생이라 알약·캡슐로 처방받았어요. 항바이러스제는 아침·저녁 하루 2번.
const fluSchedule = [
  { slot: '아침', items: [['오셀타미비르', '1캡슐', 5], ['암브록솔', '1정', 5], ['레바미피드', '1정', 5]] },
  { slot: '점심', items: [['암브록솔', '1정', 5], ['레바미피드', '1정', 5]] },
  { slot: '저녁', items: [['오셀타미비르', '1캡슐', 5], ['암브록솔', '1정', 5], ['레바미피드', '1정', 5]] },
];

// 복약 일정 — 처방을 확인하고 가이드를 만든 뒤 생겨요. start부터 days일 동안 schedule대로 먹여요.
export const courses = [
  { id: 'k1', childId: 'c1', visitId: 'v1', title: '중이염', hospital: '튼튼소아청소년과', start: '2026-11-18', days: 7, schedule: guide.schedule },
  { id: 'k4', childId: 'c3', visitId: 'v6', title: '독감(A형)', hospital: '연세가정의학과', start: '2026-11-22', days: 5, schedule: fluSchedule },
  { id: 'k3', childId: 'c2', visitId: 'v5', title: '수족구', hospital: '하늘소아과', start: '2026-11-22', days: 5, schedule: hfmdSchedule },
  {
    id: 'k2', childId: 'c1', visitId: 'v3', title: '장염', hospital: '튼튼소아청소년과', start: '2026-10-02', days: 3,
    schedule: [
      { slot: '아침', items: [['정장제', '1포'], ['구토 억제 시럽', '3mL']] },
      { slot: '저녁', items: [['정장제', '1포'], ['구토 억제 시럽', '3mL']] },
    ],
  },
];

// 저장된 복약 가이드 — 처방을 확인하고 가이드를 만들면 하나씩 생겨요. visitId로 건강기록과 이어져요.
export const guides = [
  { id: 'g1', childId: 'c1', visitId: 'v1', title: '중이염', hospital: '튼튼소아청소년과', date: '2026-11-18', ...guide },
  {
    id: 'g4', childId: 'c3', visitId: 'v6', title: '독감(A형)', hospital: '연세가정의학과', date: '2026-11-22',
    schedule: fluSchedule.map(({ slot, items }) => ({ slot, items: items.map(([name, dose]) => [name, dose]) })),
    asNeeded: '38도가 넘는 열이나 몸살이 심하면 아세트아미노펜 1정. 다음 번까지 4시간 넘게 띄우고, 하루 4정을 넘기지 마세요.',
    howTo: [
      { name: '오셀타미비르 캡슐 75mg (타미플루 성분)', how: '아침·저녁 하루 2번, 1캡슐씩 물과 함께 삼켜요. 열이 내려도 5일치를 끝까지 먹어야 해요.', note: '빈속에 먹으면 메스꺼울 수 있어요. 밥이나 우유와 함께 먹으면 편해요.' },
      { name: '암브록솔 정 30mg', how: '하루 3번 식후 1정씩 먹어요. 가래를 묽게 해서 기침으로 잘 나오게 도와요.', note: '물을 많이 마시면 효과가 더 좋아요.' },
      { name: '레바미피드 정 100mg', how: '하루 3번 식후 1정씩 먹어요. 약 때문에 속이 쓰리지 않게 위를 보호해요.', note: '' },
      { name: '아세트아미노펜 정 500mg', how: '38도가 넘는 열이 나거나 몸살이 심할 때만 1정 먹어요.', note: '종합감기약에도 같은 성분이 들어 있는 경우가 많아요. 다른 감기약과 같이 먹기 전에 약사에게 물어봐 주세요.' },
    ],
    life: [
      '해열제 없이 열이 내린 뒤 24시간이 지날 때까지 학교·학원은 쉬어요.',
      '항바이러스제를 먹는 처음 이틀 동안은 혼자 두지 말고 가까이서 지켜봐 주세요.',
      '물을 자주 마시고, 잠을 충분히 자게 해 주세요.',
      '가족과 수건·컵을 따로 쓰고, 기침할 땐 마스크를 써요.',
    ],
    danger: [
      '숨쉬기 힘들어하거나 가슴이 아프다고 할 때',
      '갑자기 헛소리를 하거나 평소와 다르게 행동할 때(창문·현관으로 뛰쳐나가려 하는 등)',
      '열이 사흘 넘게 이어지거나, 내렸다가 다시 오를 때',
      '물을 거의 못 마시고 소변이 크게 줄었을 때',
    ],
  },
  {
    id: 'g3', childId: 'c2', visitId: 'v5', title: '수족구', hospital: '하늘소아과', date: '2026-11-22',
    schedule: hfmdSchedule.map(({ slot, items }) => ({ slot, items: items.map(([name, dose]) => [name, dose]) })),
    asNeeded: '38도가 넘는 열이 나면 아세트아미노펜 9mL. 다음 번까지 4시간 넘게 띄우고, 하루 5번을 넘기지 마세요.',
    howTo: [
      { name: '이부프로펜 시럽', how: '아침·점심·저녁 밥 먹은 뒤 10mL씩 3일 동안 먹여요. 입안이 아파 못 먹을 때 통증을 줄여 줘요.', note: '빈속에 먹이면 속이 쓰릴 수 있어요. 우유나 죽을 조금이라도 먹인 뒤에 주세요.' },
      { name: '아세트아미노펜 시럽', how: '열이 38도를 넘을 때만 9mL를 먹여요.', note: '이부프로펜과 성분이 달라서 같이 써도 되지만, 각각 정해진 간격은 지켜 주세요.' },
      { name: '세티리진 시럽', how: '자기 전에 5mL를 5일 동안 먹여요. 손발 발진이 가려울 때 도움이 돼요.', note: '졸음이 올 수 있어요.' },
    ],
    life: [
      '입안이 아프니 차갑고 부드러운 음식(죽, 푸딩, 미지근한 우유)을 주세요. 맵고 짜고 신 음식은 피해요.',
      '물을 조금씩 자주 마시게 해 주세요.',
      '열이 내리고 입안 물집이 나을 때까지(보통 일주일) 학교나 학원은 쉬어요.',
      '손을 자주 씻기고, 수건·컵은 따로 써 주세요. 대변으로도 몇 주 동안 옮을 수 있어요.',
    ],
    danger: [
      '39도가 넘는 열이 이틀 넘게 이어질 때',
      '자꾸 토하거나, 목이 뻣뻣하거나, 심하게 처질 때',
      '팔다리에 힘이 빠지거나 경련을 할 때',
      '물을 거의 못 마시고 6시간 넘게 소변을 안 볼 때',
    ],
  },
  {
    id: 'g2', childId: 'c1', visitId: 'v3', title: '장염', hospital: '튼튼소아청소년과', date: '2026-10-02',
    schedule: [
      { slot: '아침', items: [['정장제', '1포'], ['구토 억제 시럽', '3mL']] },
      { slot: '저녁', items: [['정장제', '1포'], ['구토 억제 시럽', '3mL']] },
    ],
    asNeeded: null,
    howTo: [
      { name: '정장제 가루약', how: '1포를 물이나 분유 조금에 타서 먹여요.', note: '뜨거운 물에 타면 유산균이 죽을 수 있어요.' },
      { name: '구토 억제 시럽', how: '밥 먹기 30분 전에 3mL를 먹여요.', note: '토한 직후에는 30분쯤 쉬었다가 먹여요.' },
    ],
    life: ['물이나 이온음료를 조금씩 자주 먹여 주세요.', '기름진 음식과 유제품은 며칠 쉬어 주세요.', '기저귀나 변기 사용 후 손을 꼭 씻겨 주세요.'],
    danger: ['피가 섞인 변을 볼 때', '6시간 넘게 소변을 보지 않을 때', '계속 토해서 물도 못 마실 때'],
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

