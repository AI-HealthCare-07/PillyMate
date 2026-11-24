import { useState } from 'react';
import { AlertTriangle, Check, Pencil, Trash2 } from 'lucide-react';
import { Navigate, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Modal } from '../components/ui/Modal.jsx';
import { Avatar, Panel, SectionLabel, SelectChip } from '../components/ui/misc.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { parseBirth, useSelectedChild } from '../state/selectedChild.jsx';
import { todayKey, useRecords } from '../state/records.jsx';
import { CHILD_AGE_LIMIT, fullAge, hasAllConsents, toChildCreateRequest, useAddChildConsent } from '../components/child/AddChildConsent.jsx';

/** S-02 아이 목록 — 줄을 누르면 그 아이가 선택되고, 편집 버튼으로 아이 정보를 고쳐요. */
export function ChildListScreen({ go, onTab }) {
  const { childList, childId: selected, selectChild } = useSelectedChild();
  const addFlow = useAddChildConsent(go);
  return (
    <AppShell tab="children" onTab={onTab} header={<Header title="아이" />}>
      <Body className="gap-5">
        <p className="text-15 text-muted">고른 아이의 기록만 보여 드리고, 처방을 올릴 때도 그 아이 정보로 가이드를 만들어요. 체중과 알레르기는 최신으로 유지해 주세요.</p>
        {!childList.length && (
          <Panel className="px-4 py-6 text-center text-15 text-muted">등록된 아이가 없어요. 아이를 추가해 주세요.</Panel>
        )}
        <Panel as="ul" aria-label="아이 목록" className={childList.length ? '' : 'hidden'}>
          {childList.map((c, j) => {
            const on = c.id === selected;
            return (
              <li
                key={c.id}
                className={`flex items-center transition-colors ${j ? 'border-t border-line' : ''} ${on ? 'bg-brand-soft' : 'hover:bg-paper'}`}
              >
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => selectChild(c.id)}
                  className="flex flex-1 items-center gap-3.5 py-4 pl-4 pr-2 text-left"
                >
                  <Avatar name={c.name} size={44} />
                  <span className="flex flex-1 flex-col gap-0.5">
                    <span className="flex items-center gap-1.5">
                      <span className={`text-17 font-semibold ${on ? 'text-brand' : ''}`}>{c.name}</span>
                      {on && (
                        <span className="flex items-center gap-0.5 text-13 font-semibold text-brand">
                          <Check size={16} strokeWidth={2.5} aria-hidden />선택됨
                        </span>
                      )}
                    </span>
                    <span className="text-14 text-muted">{c.age}, {c.weight}</span>
                    {c.allergy ? (
                      <span className="flex items-center gap-1.5 text-14 font-medium text-danger">
                        <AlertTriangle size={16} strokeWidth={2} aria-hidden />{c.allergy}
                      </span>
                    ) : (
                      <span className="text-14 text-muted">알레르기 없음</span>
                    )}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => go('child-edit', { childId: c.id })}
                  aria-label={`${c.name} 정보 편집`}
                  className="mr-3 flex shrink-0 items-center gap-1 rounded-md border border-line bg-surface px-3 py-2.5 text-14 font-semibold hover:bg-paper"
                >
                  <Pencil size={15} strokeWidth={2} aria-hidden />편집
                </button>
              </li>
            );
          })}
        </Panel>
        <Button variant="secondary" className="w-full" onClick={addFlow.start}>아이 추가하기</Button>
        {addFlow.modal}
      </Body>
    </AppShell>
  );
}

const ALLERGIES = ['없음', '페니실린', '세팔로스포린', '이부프로펜'];

/** 저장 전 입력 확인 — 문제가 있는 칸만 메시지를 돌려줘요. */
function validate({ name, birth, weight }) {
  const errors = {};
  if (!name.trim()) errors.name = '이름이나 별명을 입력해 주세요.';
  const b = parseBirth(birth);
  if (!birth.trim()) errors.birth = '생년월일을 골라 주세요.';
  else if (!b) errors.birth = '날짜를 다시 골라 주세요.';
  else if (b > new Date()) errors.birth = '오늘 이후 날짜는 쓸 수 없어요.';
  const w = Number(String(weight).replace(/[^\d.]/g, ''));
  if (!String(weight).trim()) errors.weight = '체중을 입력해 주세요.';
  else if (!(w > 0) || w > 150) errors.weight = '16.2처럼 숫자로 입력해 주세요.';
  return errors;
}

/**
 * 아이 추가·편집 공통 폼. 저장하면 onSave(입력값)를 부르고 목록으로 돌아가요.
 * extraValidate는 화면별로 더 확인할 규칙이에요(예: 아이 추가의 만 18세 미만). 편집은 쓰지 않아요.
 */
function ChildForm({ back, onTab, title, initial, onSave, onDelete, extraValidate }) {
  const [name, setName] = useState(initial.name);
  // 날짜 칸(type=date)은 2022-03-14 형식만 받아서, 저장된 2022.03.14를 바꿔 넣어요.
  const [birth, setBirth] = useState(String(initial.birth).replaceAll('.', '-'));
  const [weight, setWeight] = useState(String(initial.weight).replace(/\s*kg$/i, ''));
  const [note, setNote] = useState(initial.note);
  const [errors, setErrors] = useState({});
  const [allergy, setAllergy] = useState(initial.allergies.length ? initial.allergies : ['없음']);
  const [chips, setChips] = useState(() => [...ALLERGIES, ...initial.allergies.filter((a) => !ALLERGIES.includes(a))]);
  const [adding, setAdding] = useState(false);
  const [custom, setCustom] = useState('');
  const closeCustom = () => {
    setAdding(false);
    setCustom('');
  };
  // 직접 입력한 알레르기를 칩으로 추가하고 바로 선택해요. 이미 있는 이름이면 그 칩을 선택만 해요.
  const addCustom = () => {
    const name = custom.trim();
    if (!name) return;
    if (!chips.includes(name)) setChips((prev) => [...prev, name]);
    setAllergy((prev) => (prev.includes(name) ? prev : [...prev.filter((x) => x !== '없음'), name]));
    closeCustom();
  };
  const toggle = (a) =>
    setAllergy((prev) => (a === '없음' ? ['없음'] : prev.includes(a) ? prev.filter((x) => x !== a) : [...prev.filter((x) => x !== '없음'), a]));
  // TODO(API): 아이 추가/수정 API 연결 후 저장 결과를 아이 목록에 반영.
  const submit = () => {
    const values = { name, birth, weight, allergies: allergy, note };
    const found = validate(values);
    if (!found.birth && extraValidate) Object.assign(found, extraValidate(values));
    setErrors(found);
    if (Object.keys(found).length) return;
    onSave(values);
  };
  const save = <Button className="w-full lg:w-auto lg:min-w-[160px]" onClick={submit}>저장하기</Button>;
  return (
    <AppShell tab="children" onTab={onTab} showTabs={false} header={<Header title={title} onBack={() => back('children')} />} actions={{ mobile: save }}>
      <Body className="gap-5">
        <Field label="이름 또는 별명" value={name} onChange={(e) => setName(e.target.value)} placeholder="예: 지우" maxLength={20} error={errors.name} />
        <div className="grid grid-cols-2 gap-3">
          <Field
            label="생년월일"
            type="date"
            value={birth}
            onChange={(e) => setBirth(e.target.value)}
            // 칸 어디를 눌러도 달력이 열리게 해요(기본은 오른쪽 달력 아이콘만 눌러야 열려요).
            onClick={(e) => {
              try {
                e.currentTarget.showPicker?.();
              } catch {
                // 지원하지 않는 브라우저는 기본 동작(아이콘 눌러 열기)을 그대로 써요.
              }
            }}
            min="2000-01-01"
            max={todayKey()}
            inputClassName={`cursor-pointer ${birth ? '' : 'text-faint'}`}
            error={errors.birth}
          />
          <div className="relative">
            <Field label="체중" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="16.2" inputMode="decimal" inputClassName="pr-11" error={errors.weight} />
            <span className="pointer-events-none absolute right-4 top-[46px] text-15 text-muted" aria-hidden>kg</span>
          </div>
        </div>
        <fieldset className="flex flex-col gap-2.5">
          <legend className="contents"><SectionLabel>알레르기</SectionLabel></legend>
          <div className="flex flex-wrap gap-2">
            {chips.map((a) => (
              <SelectChip key={a} selected={allergy.includes(a)} onClick={() => toggle(a)}>{a}</SelectChip>
            ))}
            {!adding && <SelectChip add onClick={() => setAdding(true)}>직접 입력</SelectChip>}
          </div>
          {adding && (
            <div className="flex gap-2">
              <input
                autoFocus
                value={custom}
                onChange={(e) => setCustom(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); addCustom(); }
                  if (e.key === 'Escape') closeCustom();
                }}
                maxLength={20}
                aria-label="알레르기 직접 입력"
                placeholder="예: 땅콩, 계란"
                className="h-11 min-w-0 flex-1 rounded-md border border-line bg-surface px-3.5 text-15 placeholder:text-faint focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
              />
              <button type="button" onClick={addCustom} disabled={!custom.trim()} className="shrink-0 rounded-md bg-brand px-4 text-14 font-semibold text-on-brand disabled:opacity-40">
                확인
              </button>
              <button type="button" onClick={closeCustom} className="shrink-0 rounded-md border border-line bg-surface px-3.5 text-14 font-semibold hover:bg-paper">
                취소
              </button>
            </div>
          )}
        </fieldset>
        <Field label="특이사항" multiline value={note} onChange={(e) => setNote(e.target.value)} placeholder="예: 시럽을 잘 안 먹어요, 열성 경련이 있었어요" helper="가이드를 만들 때 함께 고려해요." />
        {onDelete && (
          <div className="mt-4 flex flex-col gap-2 border-t border-line pt-6">
            <button
              type="button"
              onClick={onDelete}
              className="inline-flex items-center justify-center gap-1.5 self-start rounded-md px-1 py-2 text-15 font-semibold text-danger hover:underline"
            >
              <Trash2 size={18} strokeWidth={1.75} aria-hidden />이 아이 삭제하기
            </button>
            <p className="text-13 text-muted">삭제하면 이 아이의 복약 기록과 건강 기록이 모두 사라지고 되돌릴 수 없어요.</p>
          </div>
        )}
      </Body>
    </AppShell>
  );
}

/**
 * S-02 아이 추가 — 보호자 동의 팝업에서 세 가지 필수 동의를 마친 뒤에만 열려요.
 * 동의는 이 화면으로 넘어올 때 받은 값(location.state.consent)을 써요. 주소로 바로 들어오면 아이 목록으로 돌려보내요.
 */
export function ChildAddScreen(props) {
  const { state } = useLocation();
  const { addChild } = useSelectedChild();
  const consent = state?.consent;
  if (!hasAllConsents(consent)) return <Navigate to="/children" replace />;
  const save = (values) => {
    // 마지막 저장 때도 필수 동의를 한 번 더 확인해요. API로 보낼 본문(명세 3번)의 consent_agreed가 true여야 해요.
    const request = toChildCreateRequest(values, consent);
    if (!hasAllConsents(consent) || request.consent_agreed !== true) {
      props.go('children', undefined, { replace: true });
      return;
    }
    // TODO(API): 자녀 등록 API(BE-2)가 생기면 request를 POST /api/v1/children으로 보내고, 성공했을 때만 목록에 넣어요.
    // 지금은 서버 저장 없이 기존처럼 화면 목록에만 넣어요(동의 기록도 서버에 남지 않아요).
    addChild(values);
    // 등록을 마치면 이 화면을 기록에서 바꿔치기해서, 받은 동의도 함께 사라져요.
    props.go('children', undefined, { replace: true });
  };
  // 등록을 취소하면 이번 동의를 지우고 돌아가요. 앞으로 가기로 다시 들어와도 동의 팝업부터 다시 받아요.
  const cancel = (fallback) => {
    window.history.replaceState({ ...window.history.state, usr: null }, '');
    props.back(fallback);
  };
  return (
    <ChildForm
      {...props}
      back={cancel}
      title="아이 추가"
      initial={{ name: '', birth: '', weight: '', allergies: [], note: '' }}
      onSave={save}
      extraValidate={validateNewChildAge}
    />
  );
}

/** 아이 추가 연령 — 만 18세 미만만 등록해요(API 명세 3번, 문구는 명세 8절 그대로). */
function validateNewChildAge({ birth }) {
  const age = fullAge(parseBirth(birth));
  return age !== null && age >= CHILD_AGE_LIMIT ? { birth: `만 ${CHILD_AGE_LIMIT}세 미만 자녀만 등록할 수 있어요.` } : {};
}

/** S-02 아이 정보 편집 — 목록의 편집 버튼에서 넘겨준 아이를 고쳐요. */
export function ChildEditScreen(props) {
  const { state } = useLocation();
  const { childList, childId, updateChild, removeChild } = useSelectedChild();
  const { forgetChild } = useRecords();
  const [confirming, setConfirming] = useState(false);
  const child = childList.find((c) => c.id === (state?.childId ?? childId));
  if (!child) return <Navigate to="/children" replace />;
  const remove = () => {
    // TODO(API): 아이 삭제 API 연결 후 성공했을 때만 목록에서 지워요.
    forgetChild(child.id);
    removeChild(child.id);
    props.go('children', undefined, { replace: true });
  };
  return (
    <>
      <ChildForm
        key={child.id}
        {...props}
        title={`${child.name} 정보 편집`}
        initial={child}
        onSave={(values) => {
          updateChild(child.id, values);
          props.back('children');
        }}
        onDelete={() => setConfirming(true)}
      />
      <DeleteChildModal open={confirming} name={child.name} onClose={() => setConfirming(false)} onConfirm={remove} />
    </>
  );
}

/**
 * 아이 삭제 재확인 — 되돌릴 수 없다는 점을 알리고, 아이 이름을 그대로 입력해야 삭제 버튼이 켜져요.
 */
function DeleteChildModal({ open, name, onClose, onConfirm }) {
  const [typed, setTyped] = useState('');
  const matches = typed.trim() === name;
  const close = () => {
    setTyped('');
    onClose();
  };
  return (
    <Modal open={open} onClose={close} title={`${name} 삭제`} className="max-w-[440px]">
      <form
        className="flex flex-col gap-5 p-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (matches) onConfirm();
        }}
      >
        <div role="alert" className="flex gap-3 rounded-lg border border-danger/30 bg-danger-soft px-4 py-3.5">
          <AlertTriangle size={20} strokeWidth={2} className="mt-0.5 shrink-0 text-danger" aria-hidden />
          <div className="flex flex-col gap-1">
            <p className="text-15 font-bold text-danger">삭제하면 복구할 수 없어요</p>
            <p className="text-14 text-ink">
              {name}의 프로필과 복약 기록, 건강 기록, 복약 가이드가 모두 영구적으로 지워져요. 삭제한 뒤에는 다시 되살릴 수 없어요.
            </p>
          </div>
        </div>
        <Field
          label={<>확인을 위해 아이 이름 <strong className="font-bold text-ink">{name}</strong>을(를) 입력해 주세요</>}
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder="아이 이름 입력"
          data-autofocus
          autoComplete="off"
          helper={matches ? '이름이 확인됐어요.' : '이름이 정확히 같아야 삭제할 수 있어요.'}
        />
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={close}>취소</Button>
          <button
            type="submit"
            disabled={!matches}
            className="inline-flex h-13 items-center justify-center rounded-lg bg-danger px-5 text-16 font-semibold text-on-brand transition-colors hover:bg-[#8A1F18] disabled:cursor-not-allowed disabled:bg-sunk disabled:text-faint"
          >
            영구 삭제하기
          </button>
        </div>
      </form>
    </Modal>
  );
}
