import { useState } from 'react';
import { AlertTriangle, Check, Pencil } from 'lucide-react';
import { Navigate, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Avatar, Panel, SectionLabel, SelectChip } from '../components/ui/misc.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { children as sample } from '../data/sample.js';
import { useSelectedChild } from '../state/selectedChild.jsx';

/** S-02 아이 목록 — 줄을 누르면 그 아이가 선택되고, 편집 버튼으로 아이 정보를 고쳐요. */
export function ChildListScreen({ go, onTab }) {
  const { childId: selected, selectChild } = useSelectedChild();
  return (
    <AppShell tab="children" onTab={onTab} header={<Header title="아이" />}>
      <Body className="gap-5">
        <p className="text-15 text-muted">고른 아이의 기록만 보여 드리고, 처방을 올릴 때도 그 아이 정보로 가이드를 만들어요. 체중과 알레르기는 최신으로 유지해 주세요.</p>
        <Panel as="ul" aria-label="아이 목록">
          {sample.map((c, j) => {
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
        <Button variant="secondary" className="w-full" onClick={() => go('child-add')}>아이 추가하기</Button>
      </Body>
    </AppShell>
  );
}

const ALLERGIES = ['없음', '페니실린', '세팔로스포린', '이부프로펜'];

/** 아이 추가·편집 공통 폼. 저장은 API 연결 전이라 목록으로 돌아가기만 해요. */
function ChildForm({ back, onTab, title, initial }) {
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
  const save = <Button className="w-full lg:w-auto lg:min-w-[160px]" onClick={() => back('children')}>저장하기</Button>;
  return (
    <AppShell tab="children" onTab={onTab} showTabs={false} header={<Header title={title} onBack={() => back('children')} />} actions={{ mobile: save }}>
      <Body className="gap-5">
        <Field label="이름 또는 별명" defaultValue={initial.name} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="생년월일" defaultValue={initial.birth} inputMode="numeric" />
          <Field label="체중" defaultValue={initial.weight} inputMode="decimal" />
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
        <Field label="특이사항" multiline defaultValue={initial.note} placeholder="예: 시럽을 잘 안 먹어요, 열성 경련이 있었어요" helper="가이드를 만들 때 함께 고려해요." />
      </Body>
    </AppShell>
  );
}

/** S-02 아이 추가 */
export function ChildAddScreen(props) {
  return <ChildForm {...props} title="아이 추가" initial={{ name: '지우', birth: '2022.03.14', weight: '16.2 kg', allergies: ['페니실린'], note: '' }} />;
}

/** S-02 아이 정보 편집 — 목록의 편집 버튼에서 넘겨준 아이를 고쳐요. */
export function ChildEditScreen(props) {
  const { state } = useLocation();
  const { childId } = useSelectedChild();
  const child = sample.find((c) => c.id === (state?.childId ?? childId));
  if (!child) return <Navigate to="/children" replace />;
  return <ChildForm key={child.id} {...props} title={`${child.name} 정보 편집`} initial={child} />;
}
