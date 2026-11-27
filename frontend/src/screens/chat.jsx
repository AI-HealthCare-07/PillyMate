import { useEffect, useId, useRef, useState } from 'react';
import { ArrowUp } from 'lucide-react';
import { AppShell, Body, Header } from '../components/ui/layout.jsx';
import { chat as sample } from '../data/sample.js';
import { askChat } from '../api/prescriptionFlow.js';
import { useRecords } from '../state/records.jsx';
import { useSelectedChild } from '../state/selectedChild.jsx';

/** 건강기록 id('rx305') → 서버 처방 id(305). 예시 기록이면 null */
const prescriptionIdOf = (visitId) => (/^rx\d+$/.test(visitId ?? '') ? Number(visitId.slice(2)) : null);

/** 챗봇 프로필 — 로고의 알약 모양 */
function BotAvatar() {
  return (
    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-lav" aria-hidden>
      <svg width={18} height={18} viewBox="0 0 28 28">
        <g transform="rotate(-38 14 14)">
          <path d="M14 9H9a5 5 0 0 0 0 10h5z" className="fill-brand" />
          <path d="M14 9h5a5 5 0 0 1 0 10h-5z" className="fill-mark stroke-brand" strokeWidth={1.2} />
        </g>
      </svg>
    </span>
  );
}

/** 말풍선 — 챗봇은 왼쪽 흰 바탕, 보호자는 오른쪽 브랜드 바탕. 최대 폭 80%, 모서리 14(꼬리 쪽 4) */
function Bubble({ from, warn, children }) {
  if (from === 'me') {
    return (
      <li className="flex justify-end">
        <p className="max-w-[80%] whitespace-pre-line break-words rounded-xl rounded-br-[4px] bg-brand px-4 py-2.5 text-15 text-on-brand lg:max-w-[70%] lg:text-16">{children}</p>
      </li>
    );
  }
  return (
    <li className="flex items-start gap-2">
      <BotAvatar />
      <div className="flex min-w-0 max-w-[85%] flex-col gap-1.5 lg:max-w-[80%]">
        <p className={`whitespace-pre-line break-words rounded-xl rounded-tl-[4px] border bg-surface px-4 py-3 text-15 lg:text-16 ${warn ? 'border-danger' : 'border-line'}`}>{children}</p>
        {warn && <p className="pl-1 text-13 font-semibold text-danger">의사·약사와 꼭 상의해 주세요</p>}
      </div>
    </li>
  );
}

function Typing() {
  return (
    <li className="flex items-start gap-2" aria-label="답변을 쓰고 있어요">
      <BotAvatar />
      <span className="flex gap-1 rounded-xl rounded-tl-[4px] border border-line bg-surface px-4 py-3.5" aria-hidden>
        {[0, 150, 300].map((d) => (
          <span key={d} className="size-1.5 animate-bounce rounded-full bg-lav-plum" style={{ animationDelay: `${d}ms` }} />
        ))}
      </span>
    </li>
  );
}

/** 입력창 — 높이 52, 모서리 22, 보내기 버튼 40 */
function Composer({ onSend, disabled }) {
  const [text, setText] = useState('');
  const inputId = useId();
  const submit = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText('');
  };
  const empty = !text.trim();
  return (
    <form onSubmit={submit} className="flex w-full items-center gap-2 rounded-pill border border-edge/50 bg-surface py-1 pl-5 pr-1 focus-within:border-brand focus-within:ring-2 focus-within:ring-brand-soft">
      <label htmlFor={inputId} className="sr-only">챗봇에게 물어보기</label>
      <input
        id={inputId}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="약에 대해 물어보세요"
        autoComplete="off"
        className="h-11 min-w-0 flex-1 bg-transparent text-16 placeholder:text-faint focus:outline-none"
      />
      <button
        type="submit"
        aria-label="보내기"
        disabled={empty || disabled}
        className={`flex size-11 shrink-0 items-center justify-center rounded-full transition-colors ${empty || disabled ? 'bg-sunk text-faint' : 'bg-brand text-on-brand hover:bg-brand-hover'}`}
      >
        <ArrowUp size={20} strokeWidth={2.25} aria-hidden />
      </button>
    </form>
  );
}

/**
 * 챗봇 — 지금 고른 아이의 가장 최근 가이드(서버 처방)를 바탕으로 복약 질문에 답해요.
 * POST /prescriptions/{id}/chat. 대화는 서버에 저장하지 않아서, 최근 대화를 history로 같이 보내요.
 * 서버 가이드가 없으면(예시 데이터) 예전처럼 예시 답변을 보여 줘요.
 */
export function ChatScreen({ onTab }) {
  const { child } = useSelectedChild();
  const { guidesOf } = useRecords();
  const guides = child ? guidesOf(child.id) : [];
  // 서버에 올린 처방의 가이드를 먼저 골라요(최근 것부터). 없으면 예시 가이드
  const guide = guides.find((g) => prescriptionIdOf(g.visitId)) ?? null;
  const prescriptionId = prescriptionIdOf(guide?.visitId);
  const childName = child?.name ?? sample.childName;
  const context = guide?.title ?? sample.context;

  const greeting = () =>
    prescriptionId
      ? [{ id: 'hello', from: 'bot', text: `${childName}의 ${context} 처방에 대해 궁금한 걸 물어보세요. 먹이는 법, 보관, 부작용 같은 걸 알려 드릴게요.` }]
      : sample.messages;
  const [messages, setMessages] = useState(greeting);
  const [waiting, setWaiting] = useState(false);
  const endRef = useRef(null);

  // 아이나 처방이 바뀌면 대화를 새로 시작해요(다른 아이의 대화가 섞이지 않게).
  useEffect(() => {
    setMessages(greeting());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prescriptionId, child?.id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' });
  }, [messages, waiting]);

  const send = async (text) => {
    const before = messages.filter((m) => !m.error && m.id !== 'hello');
    setMessages((m) => [...m, { id: crypto.randomUUID(), from: 'me', text }]);
    setWaiting(true);
    if (!prescriptionId) {
      setTimeout(() => {
        setMessages((m) => [...m, { id: crypto.randomUUID(), from: 'bot', text: sample.demoReply }]);
        setWaiting(false);
      }, 1000);
      return;
    }
    try {
      const res = await askChat(prescriptionId, text, before);
      setMessages((m) => [...m, { id: crypto.randomUUID(), from: 'bot', text: res.reply, warn: res.needs_professional }]);
    } catch (error) {
      setMessages((m) => [...m, { id: crypto.randomUUID(), from: 'bot', text: error.message, error: true }]);
    } finally {
      setWaiting(false);
    }
  };

  const composer = <Composer onSend={send} disabled={waiting} />;

  return (
    <AppShell tab="chat" onTab={onTab} width="reading" header={<Header title="챗봇" />} actions={{ mobile: composer }}>
      <Body className="gap-5 pt-1 lg:gap-6">
        <p className="border-b border-line pb-4 text-13 text-muted">
          {childName}의 {context} 처방을 바탕으로 답해요. 답변은 참고용이고, 진단이나 처방을 대신하지 않아요.
        </p>

        <ol className="flex flex-col gap-4" aria-label="대화" aria-live="polite">
          {messages.map((m) => <Bubble key={m.id} from={m.from} warn={m.warn}>{m.text}</Bubble>)}
          {waiting && <Typing />}
        </ol>

        {!waiting && (
          <div className="flex flex-wrap gap-2 pl-10" role="group" aria-label="추천 질문">
            {sample.suggestions.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => send(q)}
                className="min-h-11 rounded-pill border border-line bg-surface px-4 py-2 text-left text-14 font-medium text-ink hover:border-edge/50 hover:bg-paper"
              >
                {q}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </Body>
    </AppShell>
  );
}
