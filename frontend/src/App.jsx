import { useCallback } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { LoginScreen } from './screens/auth.jsx';
import { ChildAddScreen, ChildEditScreen, ChildListScreen } from './screens/children.jsx';
import { ReadingScreen, UploadScreen } from './screens/upload.jsx';
import { ConfirmScreen } from './screens/confirm.jsx';
import { GuideErrorScreen, GuideLoadingScreen, GuideScreen } from './screens/guide.jsx';
import { HistoryScreen } from './screens/history.jsx';
import { ChatScreen } from './screens/chat.jsx';
import { HomeScreen } from './screens/home.jsx';
import { SelectedChildProvider } from './state/selectedChild.jsx';
import { RecordsProvider } from './state/records.jsx';

/**
 * 화면 키 → 주소. 화면 컴포넌트는 go('confirm')처럼 키로 이동하고,
 * 실제 주소는 여기 한 곳에서만 관리해요. 넘길 값이 있으면 go('child-edit', { childId })처럼 둘째 인자로 줘요.
 * 잠깐 거쳐 가는 화면(읽는 중, 만드는 중)에서 넘어갈 때는 go(key, undefined, { replace: true })로
 * 방문 기록을 바꿔치기해서, 뒤로가기를 눌렀을 때 그 화면으로 다시 돌아가지 않게 해요.
 */
export const ROUTES = {
  login: { path: '/login', Screen: LoginScreen },
  home: { path: '/home', Screen: HomeScreen },
  children: { path: '/children', Screen: ChildListScreen },
  'child-add': { path: '/children/new', Screen: ChildAddScreen },
  'child-edit': { path: '/children/edit', Screen: ChildEditScreen },
  upload: { path: '/upload', Screen: UploadScreen },
  reading: { path: '/upload/reading', Screen: ReadingScreen },
  confirm: { path: '/prescriptions/confirm', Screen: ConfirmScreen },
  'guide-loading': { path: '/guide/loading', Screen: GuideLoadingScreen },
  guide: { path: '/guide', Screen: GuideScreen },
  'guide-error': { path: '/guide/error', Screen: GuideErrorScreen },
  history: { path: '/history', Screen: HistoryScreen },
  chat: { path: '/chat', Screen: ChatScreen },
};

export default function App() {
  const navigate = useNavigate();
  const go = useCallback(
    (key, state, { replace = false } = {}) => {
      navigate(ROUTES[key]?.path ?? '/', { state, replace });
      window.scrollTo(0, 0);
    },
    [navigate],
  );
  // 뒤로가기 — 앱 안에서 온 이전 화면이 있으면 그리로, 주소로 바로 들어온 경우엔 fallback 화면으로 가요.
  const back = useCallback(
    (fallback = 'home') => {
      if ((window.history.state?.idx ?? 0) > 0) navigate(-1);
      else go(fallback, undefined, { replace: true });
    },
    [navigate, go],
  );
  return (
    <SelectedChildProvider>
      <RecordsProvider>
      <Routes>
        {Object.entries(ROUTES).map(([key, { path, Screen }]) => (
          <Route key={key} path={path} element={<Screen go={go} back={back} onTab={go} />} />
        ))}
        <Route path="*" element={<Navigate to={ROUTES.login.path} replace />} />
      </Routes>
      </RecordsProvider>
    </SelectedChildProvider>
  );
}
