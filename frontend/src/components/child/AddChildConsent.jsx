import { useState } from 'react';
import { Check, ChevronDown, Info } from 'lucide-react';
import { Button } from '../ui/Button.jsx';
import { Modal } from '../ui/Modal.jsx';

/**
 * 아이 등록 전 보호자 동의.
 * 아이 추가하기 → 이 동의 팝업 → (모두 동의하면) 기존 아이 추가 화면 순서로 열려요.
 * 동의 내용은 아이 추가 화면으로 넘어갈 때 함께 넘겨서, 마지막 저장 때 한 번 더 확인해요.
 */

// 동의 문구 버전. 문구는 법적 검토 전 초안이에요. 문구를 바꾸면 버전도 함께 올려 주세요.
// 지금 API(POST /children)는 버전을 받지 않아서 서버로 보내지 않아요. 버전별 동의 기록은 백엔드 협의가 필요해요.
export const CONSENT_VERSION = 'draft-2026-11';

// 자녀 등록 연령 — API 명세 0절·11절(11/24 결정): 만 18세 미만만 등록, 14세로 나누지 않고 같은 동의 흐름.
export const CHILD_AGE_LIMIT = 18;

/**
 * 필수 동의 3가지 (API 명세 USER-003).
 * detail의 status: 'tbd' = 정책이 정해지지 않음(미정), 'review' = 사실 확인·법적 검토 중.
 * 표시가 없는 줄도 법적 검토 전 초안이에요. 실제 데이터 모델(API 명세 3번)에 있는 항목만 적어요.
 */
export const CONSENT_ITEMS = [
  {
    key: 'guardian',
    title: '법정대리인 확인 및 자녀 등록 동의',
    detail: [
      { label: '확인 내용', text: `등록하려는 아이(만 ${CHILD_AGE_LIMIT}세 미만)의 부모 또는 법정대리인임을 보호자 본인이 확인해요.` },
      { label: '등록 목적', text: '보호자가 아이 정보를 등록하고, 아이의 처방·복약 일정과 복약 가이드를 대신 관리하기 위해서예요.' },
      {
        label: '확인 방법',
        status: 'tbd',
        text: '지금은 이 체크로 보호자 본인의 확인만 받아요. 이 체크가 법정대리인 신원이나 가족관계를 증명하지는 않으며, 별도 확인 방법은 아직 정해지지 않았어요.',
      },
      { label: '동의 거부', text: '동의하지 않을 수 있어요. 동의하지 않으면 아이를 등록할 수 없어요.' },
    ],
  },
  {
    key: 'personalInfo',
    title: '자녀 개인정보 수집·이용 동의',
    detail: [
      { label: '수집 항목', text: '이름 또는 별명, 생년월일, 체중' },
      { label: '이용 목적', text: `아이 구분, 나이에 맞는 복약 안내, 만 ${CHILD_AGE_LIMIT}세 미만 등록 기준 확인. 체중은 참고용으로만 쓰고 약 용량을 계산하지 않아요.` },
      { label: '보유 기간', status: 'tbd', text: '아이 정보를 삭제하거나 회원 탈퇴할 때까지 보관하는 방향으로 검토 중이에요.' },
      { label: '동의 거부', text: '동의하지 않을 수 있어요. 동의하지 않으면 아이를 등록할 수 없고, 처방 올리기·복약 가이드·복약 일정을 쓸 수 없어요.' },
    ],
  },
  {
    key: 'healthInfo',
    title: '자녀 건강정보(민감정보) 처리 동의',
    detail: [
      { label: '구분', text: '위 개인정보 수집·이용 동의와 따로 받는 민감정보(건강정보) 처리 동의예요.' },
      { label: '처리 항목', text: '알레르기, 특이사항, 처방전(사진과 약 이름·용법·병명·증상 메모 등 처방 내용), 복약 기록' },
      { label: '처리 목적', text: '복약 일정 관리, 처방 내용에 맞춘 복약 가이드 작성, 알레르기 주의 안내' },
      {
        label: '외부 처리',
        status: 'review',
        text: '처방전 글자 인식(OCR)과 복약 가이드 작성(AI)을 위해 처방 내용이 외부 서비스에서 처리될 수 있어요. 처리 위탁·국외 이전 안내는 검토 후 추가돼요.',
      },
      { label: '보유 기간', text: '처방전 원본 사진은 복약 가이드를 만들면 바로, 만들지 않으면 7일 뒤 삭제해요.' },
      { label: '보유 기간', status: 'tbd', text: '그 밖의 건강정보 보유 기간은 아직 정해지지 않았어요.' },
      { label: '동의 거부', text: '동의하지 않을 수 있어요. 동의하지 않으면 아이를 등록할 수 없고, 처방 올리기·복약 가이드·복약 일정을 쓸 수 없어요.' },
    ],
  },
];

const STATUS_LABEL = { tbd: '미정', review: '검토 중' };

/** 세 가지 필수 동의를 모두 했는지 — 팝업 버튼, 등록 화면 진입, 마지막 저장에서 같은 기준을 써요. */
export function hasAllConsents(consent) {
  return Boolean(consent) && CONSENT_ITEMS.every(({ key }) => consent[key] === true);
}

/** 만 나이(세). 날짜가 아니면 null. */
export function fullAge(birthDate, today = new Date()) {
  if (!(birthDate instanceof Date)) return null;
  let age = today.getFullYear() - birthDate.getFullYear();
  if (today.getMonth() < birthDate.getMonth() || (today.getMonth() === birthDate.getMonth() && today.getDate() < birthDate.getDate())) age -= 1;
  return age;
}

/**
 * 자녀 등록 요청 본문 — API 명세 3번 `POST /children`과 같은 필드만 만들어요.
 * - consent_agreed: 필수 동의 3가지를 모두 했을 때만 true (서버는 불리언 하나만 받아요)
 * - 동의 시각은 서버가 저장해요(child.consent_agreed_at). 화면의 시각·버전·항목별 동의는 보내지 않아요.
 * 이 값을 그대로 POST /api/v1/children 본문으로 보내요 (state/selectedChild.jsx의 addChild).
 */
export function toChildCreateRequest({ name, birth, weight, allergies, note }, consent) {
  const weightKg = Number(String(weight ?? '').replace(/[^\d.]/g, ''));
  const allergyList = (allergies ?? []).filter((a) => a !== '없음');
  return {
    name: String(name ?? '').trim(),
    birth_date: String(birth ?? '').trim(),
    consent_agreed: hasAllConsents(consent),
    ...(weightKg > 0 ? { weight_kg: weightKg } : {}),
    ...(allergyList.length ? { allergies: allergyList.join(', ') } : {}),
    ...(String(note ?? '').trim() ? { notes: String(note).trim() } : {}),
  };
}

const empty = () => Object.fromEntries(CONSENT_ITEMS.map(({ key }) => [key, false]));

/**
 * 아이 추가하기 버튼에 붙여 쓰는 흐름.
 * const { start, modal } = useAddChildConsent(go); → 버튼 onClick={start}, 화면 어딘가에 {modal}.
 * 팝업을 열 때마다 동의를 처음부터 다시 받아요.
 */
export function useAddChildConsent(go) {
  const [open, setOpen] = useState(false);
  const [session, setSession] = useState(0);
  const start = () => {
    setSession((n) => n + 1);
    setOpen(true);
  };
  const close = () => setOpen(false);
  const proceed = (checked) => {
    if (!hasAllConsents(checked)) return;
    setOpen(false);
    // agreedAt은 화면에서 동의한 시각(참고용)이에요. 공식 동의 시각은 등록 때 서버가 기록해요.
    go('child-add', { consent: { ...checked, version: CONSENT_VERSION, agreedAt: new Date().toISOString() } });
  };
  const modal = <ConsentModal key={session} open={open} onClose={close} onAgree={proceed} />;
  return { start, modal };
}

function ConsentModal({ open, onClose, onAgree }) {
  const [checked, setChecked] = useState(empty);
  const [expanded, setExpanded] = useState(null);
  const all = hasAllConsents(checked);
  const setAll = (on) => setChecked(Object.fromEntries(CONSENT_ITEMS.map(({ key }) => [key, on])));

  return (
    <Modal open={open} onClose={onClose} title="아이 등록 전 동의" description="세 가지 모두 동의해야 등록할 수 있어요" className="max-w-[480px]">
      <div className="flex flex-col gap-4 p-5">
        <p className="flex items-start gap-2 rounded-lg bg-mark-soft px-3.5 py-3 text-13 text-mark-ink">
          <Info size={16} strokeWidth={2} className="mt-0.5 shrink-0" aria-hidden />
          아래 동의 문구는 법적 검토 전 초안이에요. 내용이 확정되면 바뀔 수 있어요.
        </p>

        <CheckRow checked={all} onChange={setAll} className="min-h-14 rounded-xl border border-brand/30 bg-brand-soft px-4 py-3.5">
          <span className="text-16 font-bold text-brand">전체 동의하기</span>
        </CheckRow>

        <ul className="flex flex-col" aria-label="필수 동의 항목">
          {CONSENT_ITEMS.map((item, j) => {
            const isOpen = expanded === item.key;
            const detailId = `consent-detail-${item.key}`;
            return (
              <li key={item.key} className={j ? 'border-t border-line' : ''}>
                <div className="flex items-center gap-2 py-1">
                  <CheckRow
                    checked={checked[item.key]}
                    onChange={(on) => setChecked((prev) => ({ ...prev, [item.key]: on }))}
                    className="min-w-0 flex-1 py-2.5 pl-3.5"
                  >
                    <span className="text-15">
                      <span className="mr-1 font-semibold text-brand">[필수]</span>
                      <span className="break-keep">{item.title}</span>
                    </span>
                  </CheckRow>
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={detailId}
                    onClick={() => setExpanded(isOpen ? null : item.key)}
                    className="flex min-h-11 shrink-0 items-center gap-0.5 rounded-md px-2 text-13 font-semibold text-terra-ink hover:bg-paper"
                  >
                    자세히 보기
                    <ChevronDown size={15} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} aria-hidden />
                  </button>
                </div>
                {isOpen && (
                  <div id={detailId} className="mb-3 ml-3.5 rounded-lg bg-paper px-3.5 py-3">
                    <p className="mb-1.5 text-12 font-semibold text-faint">초안 · 법적 검토 전</p>
                    <ul className="flex list-disc flex-col gap-1.5 pl-4 text-13 text-muted">
                      {item.detail.map((line) => (
                        <li key={line.text} className="break-keep">
                          <span className="font-semibold text-ink">{line.label}</span>
                          {line.status && (
                            <span className="ml-1 inline-flex rounded-pill bg-mark-soft px-1.5 align-[1px] text-12 font-semibold text-mark-ink">
                              {STATUS_LABEL[line.status]}
                            </span>
                          )}
                          <span className="mx-1 text-faint" aria-hidden>·</span>
                          {line.text}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        <div className="flex flex-col-reverse gap-2 border-t border-line pt-4 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose}>취소</Button>
          <Button disabled={!all} onClick={() => onAgree(checked)}>동의하고 계속하기</Button>
        </div>
      </div>
    </Modal>
  );
}

/** 체크박스 한 줄 — 실제 checkbox 입력은 숨기고, 같은 모양의 상자를 그려요. */
function CheckRow({ checked, onChange, className = '', children }) {
  return (
    <label className={`flex cursor-pointer items-center gap-3 ${className}`}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="peer sr-only" />
      <span
        className={`flex size-6 shrink-0 items-center justify-center rounded-[6px] border-2 transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-brand/40 ${checked ? 'border-brand bg-brand text-on-brand' : 'border-edge bg-surface text-transparent'}`}
        aria-hidden
      >
        <Check size={15} strokeWidth={3} />
      </span>
      {children}
    </label>
  );
}
