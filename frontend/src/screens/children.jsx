import { useState } from 'react';
import { AlertTriangle, Check } from 'lucide-react';
import { Button } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Avatar, Panel, SectionLabel, SelectChip } from '../components/ui/misc.jsx';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { children as sample } from '../data/sample.js';

/** S-02 아이 목록 */
export function ChildListScreen({ go, onTab }) {
  const [selected, setSelected] = useState(sample[0].id);
  return (
    <AppShell tab="children" onTab={onTab} header={<Header title="아이" />}>
      <Body className="gap-5">
        <p className="text-15 text-muted">처방을 올릴 때 고른 아이 정보로 가이드를 만들어요. 체중과 알레르기는 최신으로 유지해 주세요.</p>
        <Panel as="ul" aria-label="아이 목록">
          {sample.map((c, j) => {
            const on = c.id === selected;
            return (
              <li key={c.id} className={`flex items-center gap-3.5 py-4 pl-4 pr-3 ${j ? 'border-t border-line' : ''}`}>
                <Avatar name={c.name} size={44} />
                <div className="flex flex-1 flex-col gap-0.5">
                  <p className="text-17 font-semibold">{c.name}</p>
                  <p className="text-14 text-muted">{c.age}, {c.weight}</p>
                  {c.allergy ? (
                    <p className="flex items-center gap-1.5 text-14 font-medium text-danger">
                      <AlertTriangle size={16} strokeWidth={2} aria-hidden />{c.allergy}
                    </p>
                  ) : (
                    <p className="text-14 text-muted">알레르기 없음</p>
                  )}
                </div>
                {on ? (
                  <span className="flex items-center gap-1 px-2 py-2.5 text-14 font-semibold text-brand">
                    <Check size={18} strokeWidth={2.25} aria-hidden />선택됨
                  </span>
                ) : (
                  <button type="button" onClick={() => setSelected(c.id)} className="rounded-md border border-line px-3.5 py-2.5 text-14 font-semibold hover:bg-paper">
                    선택
                  </button>
                )}
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

/** S-02 아이 추가 */
export function ChildAddScreen({ go, onTab }) {
  const [allergy, setAllergy] = useState(['페니실린']);
  const toggle = (a) =>
    setAllergy((prev) => (a === '없음' ? ['없음'] : prev.includes(a) ? prev.filter((x) => x !== a) : [...prev.filter((x) => x !== '없음'), a]));
  const save = <Button className="w-full lg:w-auto lg:min-w-[160px]" onClick={() => go('children')}>저장하기</Button>;
  return (
    <AppShell tab="children" onTab={onTab} showTabs={false} header={<Header title="아이 추가" onBack={() => go('children')} />} actions={{ mobile: save }}>
      <Body className="gap-5">
        <Field label="이름 또는 별명" defaultValue="지우" />
        <div className="grid grid-cols-2 gap-3">
          <Field label="생년월일" defaultValue="2022.03.14" inputMode="numeric" />
          <Field label="체중" defaultValue="16.2 kg" inputMode="decimal" />
        </div>
        <fieldset className="flex flex-col gap-2.5">
          <legend className="contents"><SectionLabel>알레르기</SectionLabel></legend>
          <div className="flex flex-wrap gap-2">
            {ALLERGIES.map((a) => (
              <SelectChip key={a} selected={allergy.includes(a)} onClick={() => toggle(a)}>{a}</SelectChip>
            ))}
            <SelectChip add>직접 입력</SelectChip>
          </div>
        </fieldset>
        <Field label="특이사항" multiline placeholder="예: 시럽을 잘 안 먹어요, 열성 경련이 있었어요" helper="가이드를 만들 때 함께 고려해요." />
      </Body>
    </AppShell>
  );
}
