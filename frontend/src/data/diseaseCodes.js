/**
 * 처방전 질병분류기호(KCD) → 보호자가 알아보기 쉬운 병명.
 * 소아청소년과·이비인후과·피부과·안과 처방전에 자주 나오는 코드만 담았어요. 표에 없는 코드는 병명을 비워 두고
 * 보호자가 직접 적게 해요(코드만 참고로 보여 줘요). 병명은 짐작으로 채우지 않아요.
 *
 * 앞의 쉬운 이름은 가이드 서버가 질환별 생활 수칙을 고를 때 쓰는 낱말(감기·중이염·장염·피부염·결막염 등,
 * app/resources/guide/templates/DATA-REF-006_*.json의 match_user_input)과 맞췄어요.
 * TODO: 건강보험심사평가원 질병정보서비스 API 활용신청이 승인되면, 표에 없는 코드는 그 API로 찾아요.
 */
const KCD_NAMES = {
  // 호흡기
  J00: '감기(급성 비인두염)',
  J01: '급성 부비동염',
  J02: '목감기(급성 인두염)',
  J03: '급성 편도염',
  J04: '급성 후두염',
  J05: '크룹(급성 폐쇄성 후두염)',
  J06: '감기(급성 상기도 감염)',
  J10: '독감(인플루엔자)',
  J11: '독감(인플루엔자)',
  J12: '폐렴(바이러스성)',
  J15: '폐렴(세균성)',
  J18: '폐렴',
  J20: '급성 기관지염',
  J21: '급성 모세기관지염',
  J30: '알레르기 비염',
  J31: '만성 비염',
  J32: '만성 부비동염',
  J40: '기관지염',
  J45: '천식',
  // 귀·눈
  H00: '다래끼',
  H10: '결막염',
  H60: '외이도염',
  H65: '중이염(비화농성)',
  H66: '중이염(화농성)',
  // 소화기
  A08: '장염(바이러스성)',
  A09: '장염(감염성 위장염)',
  K12: '구내염',
  K52: '위장염(비감염성)',
  K590: '변비',
  // 피부
  L01: '농가진',
  L20: '아토피 피부염',
  L22: '기저귀 피부염',
  L23: '접촉성 피부염(알레르기성)',
  L24: '접촉성 피부염(자극성)',
  L25: '접촉성 피부염',
  L30: '피부염',
  L50: '두드러기',
  // 감염병
  A38: '성홍열',
  B01: '수두',
  B084: '수족구병',
  B34: '바이러스 감염',
  // 증상
  R05: '기침',
  R10: '복통',
  R11: '구토',
  R50: '발열',
};

const normalize = (code) => code.toUpperCase().replace(/[^A-Z0-9]/g, '');

/** 코드 하나 → 병명. 세부 코드(J069)가 없으면 앞 세 자리(J06)로 찾아요. 없으면 null. */
export function diseaseNameOf(code) {
  const c = normalize(code);
  if (!c) return null;
  return KCD_NAMES[c] ?? KCD_NAMES[c.slice(0, 4)] ?? KCD_NAMES[c.slice(0, 3)] ?? null;
}

/**
 * 처방 질병분류기호(서버 diagnosis_extracted, 쉼표로 이어진 문자열) → 병명 제안.
 * 결과: { codes: ['J00', 'H66'], name: '감기(급성 비인두염), 중이염(화농성)', unknown: ['Z00'] }
 * 아는 코드가 하나도 없으면 name은 ''예요.
 */
export function suggestDiseaseName(diagnosisCodes) {
  const codes = String(diagnosisCodes ?? '')
    .split(/[,\s]+/)
    .map(normalize)
    .filter(Boolean);
  const names = [];
  const unknown = [];
  for (const code of codes) {
    const name = diseaseNameOf(code);
    if (!name) unknown.push(code);
    else if (!names.includes(name)) names.push(name);
  }
  return { codes, name: names.join(', '), unknown };
}
