import { useState } from 'react';
import { Check, ChevronDown, Info } from 'lucide-react';
import { Button } from '../ui/Button.jsx';
import { Modal } from '../ui/Modal.jsx';

/**
 * 아이 등록 전 보호자 동의.
 * 아이 추가하기 → 이 동의 팝업 → (모두 동의하면) 기존 아이 추가 화면 순서로 열려요.
 * 동의 내용은 아이 추가 화면으로 넘어갈 때 함께 넘겨서, 마지막 저장 때 한 번 더 확인해요.
 */

// 동의 문구는 법적 검토 전 초안이에요. 확정되면 version과 문구를 함께 바꿔 주세요.
export const CONSENT_VERSION = 'draft-2026-11';

export const CONSENT_ITEMS = [
  {
    key: 'guardian',
    title: '법정대리인 확인 및 자녀 등록 동의',
    detail: [
      '본인은 등록하려는 아이의 부모 또는 법정대리인이에요.',
      '아이 정보를 PillyMate에 등록하고, 아이의 복약 관리를 위해 앱을 이용하는 것에 동의해요.',
      '만 14세 미만 아동의 개인정보는 법정대리인의 동의를 받아 처리해요.',
    ],
  },
  {
    key: 'personalInfo',
    title: '자녀 개인정보 수집·이용 동의',
    detail: [
      '수집 항목: 이름 또는 별명, 생년월일, 체중',
      '이용 목적: 아이 구분, 나이·체중에 맞는 복약 안내',
      '보유 기간: 아이 정보를 삭제하거나 회원 탈퇴할 때까지',
      '동의하지 않을 수 있지만, 동의하지 않으면 아이를 등록할 수 없어요.',
    ],
  },
  {
    key: 'healthInfo',
    title: '자녀 건강정보 처리 동의',
    detail: [
      '처리 항목: 알레르기, 특이사항, 처방전 내용, 복약 기록',
      '이용 목적: 복약 가이드 작성, 알레르기 주의 안내, 복약 기록 관리',
      '보유 기간: 아이 정보를 삭제하거나 회원 탈퇴할 때까지',
      '동의하지 않을 수 있지만, 동의하지 않으면 아이를 등록할 수 없어요.',
    ],
  },
];

/** 세 가지 필수 동의를 모두 했는지 — 팝업 버튼과 마지막 저장에서 같은 기준을 써요. */
export function hasAllConsents(consent) {
  return Boolean(consent) && CONSENT_ITEMS.every(({ key }) => consent[key] === true);
}

/**
 * 등록 데이터에 동의 여부를 붙여요.
 * TODO(API): 아이 등록 API가 생기면 이 값을 그대로 보내요(consent_agreed, consent_version, consent_agreed_at).
 */
export function withConsent(values, consent) {
  return {
    ...values,
    consent_agreed: hasAllConsents(consent),
    consent_version: consent?.version ?? null,
    consent_agreed_at: consent?.agreedAt ?? null,
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

        <CheckRow checked={all} onChange={setAll} className="rounded-lg border border-line px-3.5 py-3.5">
          <span className="text-16 font-bold">전체 동의하기</span>
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
                    className="flex shrink-0 items-center gap-0.5 rounded-md px-2 py-2 text-13 font-semibold text-muted hover:bg-paper hover:text-ink"
                  >
                    자세히 보기
                    <ChevronDown size={15} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} aria-hidden />
                  </button>
                </div>
                {isOpen && (
                  <div id={detailId} className="mb-3 ml-3.5 rounded-lg bg-paper px-3.5 py-3">
                    <p className="mb-1.5 text-12 font-semibold text-faint">초안 · 법적 검토 전</p>
                    <ul className="flex list-disc flex-col gap-1 pl-4 text-13 text-muted">
                      {item.detail.map((line) => <li key={line}>{line}</li>)}
                    </ul>
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        <div className="flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:justify-end">
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
        className={`flex size-6 shrink-0 items-center justify-center rounded-[6px] border-2 transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-brand/40 ${checked ? 'border-brand bg-brand text-on-brand' : 'border-line bg-surface text-transparent'}`}
        aria-hidden
      >
        <Check size={15} strokeWidth={3} />
      </span>
      {children}
    </label>
  );
}
