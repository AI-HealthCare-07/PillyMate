// 약효 분류 — 홈 '오늘 먹을 약'에서 약 이름 아래 배지로 보여 줘요.
//
// 지금은 약효 정보를 주는 API가 없어서, 사람이 성분과 분류를 직접 확인한 약만 아래 표에 적어 둬요.
// 표에 없는 약은 분류를 짐작하지 않고 '약효 정보 확인 중'으로 보여 줘요. LLM이 만든 분류는 넣지 마세요.
//
// TODO(API): 식약처 의약품 제품 허가정보, 심평원 의약품성분약효정보, ATC 코드 등을 연결하면
// 약 데이터에 아래 모양의 efficacy 필드를 채워 주세요. 그 값이 있으면 이 표보다 먼저 써요.
//   efficacy: { label: '항생제', code?: 'J01CA04', source?: 'hira' }

/** 성분 이름 → 확인된 약효 분류. 키는 약 이름의 첫 낱말(제형·용량을 뺀 성분명)과 똑같아야 해요. */
const VERIFIED = {
  아목시실린: { label: '항생제', source: 'manual' },
  세티리진: { label: '항히스타민제', source: 'manual' },
};

export const EFFICACY_PENDING_LABEL = '약효 정보 확인 중';

/**
 * 약 하나의 약효 분류를 돌려줘요. 확인된 분류가 없으면 null.
 * @param {{ name: string, efficacy?: { label: string } | null }} med
 */
export function efficacyOf(med) {
  if (med?.efficacy?.label) return med.efficacy;
  // '아목시실린 건조시럽' → '아목시실린'. 첫 낱말이 정확히 같을 때만 맞는 것으로 봐요.
  const ingredient = String(med?.name ?? '').trim().split(/\s+/)[0];
  return VERIFIED[ingredient] ?? null;
}
