import { Button } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Logo } from '../components/ui/misc.jsx';
import { AppShell } from '../components/ui/layout.jsx';

/** S-01 로그인 */
export function LoginScreen({ go }) {
  const actions = {
    mobile: (
      <>
        <Button className="w-full" onClick={() => go('upload')}>로그인</Button>
        <Button variant="secondary" className="w-full">처음이에요, 가입할게요</Button>
      </>
    ),
    desktop: null,
  };
  return (
    <AppShell showTabs={false} showTopBar={false} actions={actions}>
      <form
        className="flex flex-1 flex-col gap-9 px-6 pb-6 pt-12 lg:justify-center lg:px-0"
        onSubmit={(e) => { e.preventDefault(); go('upload'); }}
      >
        <Logo size={28} />
        <div className="flex flex-col gap-3">
          <h1 className="text-28 font-bold">처방전 한 장이면<br />아이 약 먹이는 법이<br />정리돼요</h1>
          <p className="text-15 text-muted">사진을 올리면 약 이름과 양을 읽고, 보호자가 확인한 내용으로 복약 가이드를 만들어요.</p>
        </div>
        <div className="flex flex-col gap-4">
          <Field label="이메일" type="email" autoComplete="email" placeholder="parent@example.com" />
          <Field label="비밀번호" type="password" autoComplete="current-password" helper="8자 이상, 영문과 숫자를 섞어 주세요." />
        </div>
        <div className="hidden flex-col gap-2 lg:flex">
          <Button type="submit" className="w-full">로그인</Button>
          <Button variant="secondary" className="w-full">처음이에요, 가입할게요</Button>
        </div>
      </form>
    </AppShell>
  );
}
