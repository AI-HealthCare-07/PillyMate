/**
 * 약효 분류 — 약 이름(또는 성분)으로 약효 배지에 띄울 짧은 분류와 한 줄 설명을 찾아요.
 *
 * 데이터 출처: 백엔드 ai_worker/data/drug_refs.json (status: done, 식약처 허가 사용상의 주의사항으로 검수한 약)
 *            + app/resources/guide/templates/DATA-REF-007_med_tips.json 의 ingredient_to_class.
 * 서버 가이드가 쓰는 것과 같은 근거만 써요. 근거 없이 이름 모양으로 짐작하지 않아요.
 *
 * 찾는 순서 (백엔드 references.py와 같은 흐름)
 *   0) 약 데이터에 efficacy: { label } (또는 efficacyLabel / efficacy_label)가 있으면 → 그대로
 *      TODO(API): 식약처 허가정보·심평원 성분약효정보·ATC 코드를 연결하면 이 필드를 채워 주세요.
 *   1) 제품 이름 정확히 일치 (괄호·함량·띄어쓰기를 지운 뒤)
 *   2) 이름 안에 적힌 성분 (괄호 속 성분 또는 이름 자체에 든 성분명) → 성분 기준 분류
 *   3) 못 찾으면 null → 배지를 그리지 않아요
 */

/** 성분 → 분류. label은 배지에 쓰는 짧은 말, summary는 drug_refs.json의 효능 문장이에요. */
const BY_INGREDIENT = {
  acetaminophen: {
    label: '해열진통제',
    summary: '감기로 인한 열과 두통·근육통 같은 통증을 줄여 주는 해열진통제예요.',
  },
  ibuprofen: {
    label: '해열진통소염제',
    summary: '열을 내리고 통증과 염증을 줄여 주는 해열진통소염제(NSAID)예요.',
  },
  // 단일 성분 아목시실린은 drug_refs.json에 제품이 없어 효능 문장은 비워 두고, 계열(DATA-REF-007: antibiotic)만 써요.
  amoxicillin: { label: '항생제', summary: null },
  'amoxicillin/clavulanate': {
    label: '항생제',
    summary: '세균 감염(중이염, 부비동염, 편도염, 기관지염 등)을 치료하는 페니실린계 항생제예요.',
  },
  cefaclor: {
    label: '항생제',
    summary: '세균 감염(중이염, 인후두염, 편도염, 기관지염 등)을 치료하는 세팔로스포린계 항생제예요.',
  },
  clarithromycin: {
    label: '항생제',
    summary: '세균 감염(중이염, 인두염, 편도염, 부비동염, 기관지염 등)을 치료하는 마크로라이드계 항생제예요.',
  },
  'saccharomyces boulardii': {
    label: '정장제',
    summary: '항생제 등으로 깨진 장내 균형을 바로잡아 묽은 변·복부 팽만을 개선하는 정장제예요(효모균).',
  },
  racecadotril: {
    label: '지사제',
    summary: '생후 3개월 이상 아이의 급성 설사에서 수분·전해질 보충을 돕는 지사제예요.',
  },
  cetirizine: {
    label: '항히스타민제',
    summary: '콧물·재채기 같은 알레르기 비염, 알레르기 결막염, 두드러기, 피부 가려움을 줄여 주는 항히스타민제예요.',
  },
  ambroxol: {
    label: '가래약(거담제)',
    summary: '가래를 묽게 해서 잘 나오게 돕는 거담제예요(급·만성 기관지염).',
  },
  levodropropizine: {
    label: '기침약(진해제)',
    summary: '기침을 가라앉히는 진해제예요(급·만성 기관지염의 기침).',
  },
  hydrocortisone: {
    label: '피부 스테로이드제',
    summary: '습진·피부염, 피부 가려움, 벌레 물린 데 쓰는 약한 스테로이드 로션이에요.',
  },
  desonide: {
    label: '피부 스테로이드제',
    summary: '스테로이드에 반응하는 피부 질환(습진·피부염 등)의 가려움과 염증을 줄여 주는 약한 스테로이드 크림이에요.',
  },
  pimecrolimus: {
    label: '아토피 피부염약',
    summary: '2세 이상 아이의 가벼운~중간 정도 아토피 피부염에 쓰는 비스테로이드 연고(칼시뉴린 억제제)예요.',
  },
  tobramycin: {
    label: '항생제 안약',
    summary: '세균성 결막염, 다래끼, 안검염, 각막염 같은 눈의 세균 감염을 치료하는 항생제 안약이에요.',
  },
};

/** drug_refs.json의 제품 이름(key + names) → 성분 */
const PRODUCTS = [
  [['비오플250산', '비오플250산(사카로마이세스보울라르디균)'], 'saccharomyces boulardii'],
  [['토브렉스점안액', '토브렉스0.3%점안액(토브라마이신)'], 'tobramycin'],
  [['하이드라섹산', '하이드라섹산10mg(라세카도트릴)', '하이드라섹산30mg(라세카도트릴)'], 'racecadotril'],
  [['챔프시럽', '챔프시럽(아세트아미노펜)'], 'acetaminophen'],
  [['뮤코브이시럽', '뮤코브이시럽(암브록솔염산염)'], 'ambroxol'],
  [['어린이부루펜시럽', '어린이부루펜시럽(이부프로펜)'], 'ibuprofen'],
  [['락티케어에취씨로션', '락티케어에취씨로션1%(히드로코르티손)'], 'hydrocortisone'],
  [['데소덤크림', '데소덤크림0.05%(데소나이드)'], 'desonide'],
  [['유한아세트아미노펜정500밀리그램'], 'acetaminophen'],
  [['세노바액', '세노바액(세티리진염산염)'], 'cetirizine'],
  [['오구멘틴듀오시럽', '오구멘틴듀오시럽228mg/5ml(아목시실린`클라불란산칼륨)'], 'amoxicillin/clavulanate'],
  [['건일레보드로프로피진시럽'], 'levodropropizine'],
  [['알세진정10밀리그램', '알세진정10밀리그램(세티리진염산염)'], 'cetirizine'],
  [['팜젠암브록솔염산염정', '팜젠암브록솔염산염정30mg'], 'ambroxol'],
  [['레브로콜정60밀리그램', '레브로콜정60밀리그램(레보드로프로피진)'], 'levodropropizine'],
  [['크라맥스정625밀리그램', '크라맥스정625밀리그램(아목시실린-클라불란산칼륨(4:1))'], 'amoxicillin/clavulanate'],
  [['경보세파클러건조시럽', '경보세파클러건조시럽25mg/mL(세파클러수화물)'], 'cefaclor'],
  [['엘리델크림', '엘리델크림1%(피메크로리무스)'], 'pimecrolimus'],
  [['광동클래리트로마이신건조시럽', '광동클래리트로마이신건조시럽125mg/5mL'], 'clarithromycin'],
  [['넬슨이부프로펜정200밀리그램', '넬슨이부프로펜정200밀리그램(이부프로펜)'], 'ibuprofen'],
  [['일양세파클러캡슐250밀리그램'], 'cefaclor'],
];

/**
 * 성분의 한글 이름 → 성분. 약 이름에 성분명이 그대로 적힌 경우(괄호 속 또는 '유한아세트아미노펜정')만 찾아요.
 * 긴 이름부터 맞춰서 '아목시실린-클라불란산'이 '아목시실린'보다 먼저 걸리게 해요.
 */
const INGREDIENT_WORDS = [
  ['아목시실린클라불란산', 'amoxicillin/clavulanate'],
  ['클라불란산', 'amoxicillin/clavulanate'],
  ['사카로마이세스', 'saccharomyces boulardii'],
  ['레보드로프로피진', 'levodropropizine'],
  ['클래리트로마이신', 'clarithromycin'],
  ['클라리스로마이신', 'clarithromycin'],
  ['아세트아미노펜', 'acetaminophen'],
  ['아목시실린', 'amoxicillin'],
  ['하이드로코르티손', 'hydrocortisone'],
  ['히드로코르티손', 'hydrocortisone'],
  ['피메크로리무스', 'pimecrolimus'],
  ['라세카도트릴', 'racecadotril'],
  ['토브라마이신', 'tobramycin'],
  ['이부프로펜', 'ibuprofen'],
  ['세파클러', 'cefaclor'],
  ['세티리진', 'cetirizine'],
  ['암브록솔', 'ambroxol'],
  ['데소나이드', 'desonide'],
].sort((a, b) => b[0].length - a[0].length);

// 백엔드 ai_worker/tasks/rag/normalize.py 와 같은 규칙
const STRENGTH = /\d+(\.\d+)?\s*(mg|g|ml|mcg|μg|iu|%)(\s*\/\s*\d*(\.\d+)?\s*(ml|g))?/gi;
const BRACKETS = /[([（【][^)\]）】]*[)\]）】]/g;
const SPACES = /[\s_\-·.,/`]+/g;

export function normalizeName(name) {
  if (!name) return '';
  return String(name).replace(BRACKETS, '').replace(STRENGTH, '').replace(SPACES, '').toLowerCase();
}

const byName = new Map();
for (const [names, ingredient] of PRODUCTS) {
  for (const n of names) {
    const key = normalizeName(n);
    if (key && !byName.has(key)) byName.set(key, ingredient);
  }
}

function ingredientFromText(text) {
  const flat = String(text || '').replace(SPACES, '');
  return INGREDIENT_WORDS.find(([word]) => flat.includes(word))?.[1] ?? null;
}

function toInfo(ingredient, basis) {
  const c = BY_INGREDIENT[ingredient];
  return c ? { label: c.label, summary: c.summary, ingredient, basis } : null;
}

/** 예전 화면 호환용. 이제 홈에서는 쓰지 않아요(못 찾으면 배지를 숨겨요). */
export const EFFICACY_PENDING_LABEL = '약효 정보 확인 중';

const cache = new Map();

/**
 * 약(오늘 먹을 약 한 줄, 처방 약 등) → { label, summary, ingredient, basis } 또는 null.
 * basis: 'server' | 'product' | 'ingredient'
 */
export function efficacyOf(med) {
  if (!med) return null;

  // 0) 약 데이터에 약효가 이미 있으면(API 연결 후) 그걸 먼저 써요.
  //    기존 약속 형식 efficacy: { label, code?, source? } 와 efficacyLabel / efficacy_label 문자열 둘 다 받아요.
  if (med.efficacy?.label) {
    return { summary: null, ingredient: med.ingredient ?? null, ...med.efficacy, basis: 'server' };
  }
  const serverLabel = med.efficacyLabel ?? med.efficacy_label;
  if (serverLabel) {
    return { label: serverLabel, summary: null, ingredient: med.ingredient ?? null, basis: 'server' };
  }

  const name = med.name ?? med.medicationName ?? med.medication_name ?? '';
  const cacheKey = `${name}|${med.ingredient ?? ''}`;
  if (cache.has(cacheKey)) return cache.get(cacheKey);

  let info = null;
  // 1) 제품 이름 정확히 일치
  const productIngredient = byName.get(normalizeName(name));
  if (productIngredient) info = toInfo(productIngredient, 'product');
  // 2) 성분 기준 — 영문 성분값이 있으면 그걸로, 없으면 이름에 적힌 한글 성분명으로
  if (!info && med.ingredient) info = toInfo(String(med.ingredient).toLowerCase(), 'ingredient');
  if (!info) {
    const ingredient = ingredientFromText(name);
    if (ingredient) info = toInfo(ingredient, 'ingredient');
  }

  cache.set(cacheKey, info);
  return info;
}
