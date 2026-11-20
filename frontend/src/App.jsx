import { useCallback } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { LoginScreen } from './screens/auth.jsx';
import { ChildAddScreen, ChildListScreen } from './screens/children.jsx';
import { ReadingScreen, UploadScreen } from './screens/upload.jsx';
import { ConfirmScreen } from './screens/confirm.jsx';
import { GuideErrorScreen, GuideLoadingScreen, GuideScreen } from './screens/guide.jsx';
import { HistoryScreen } from './screens/history.jsx';

/**
 * 화면 키 → 주소. 화면 컴포넌트는 go('confirm')처럼 키로 이동하고,
 * 실제 주소는 여기 한 곳에서만 관리해요.
 */
export const ROUTES = {
  login: { path: '/login', Screen: LoginScreen },
  children: { path: '/children', Screen: ChildListScreen },
  'child-add': { path: '/children/new', Screen: ChildAddScreen },
  upload: { path: '/upload', Screen: UploadScreen },
  reading: { path: '/upload/reading', Screen: ReadingScreen },
  confirm: { path: '/prescriptions/confirm', Screen: ConfirmScreen },
  'guide-loading': { path: '/guide/loading', Screen: GuideLoadingScreen },
  guide: { path: '/guide', Screen: GuideScreen },
  'guide-error': { path: '/guide/error', Screen: GuideErrorScreen },
  history: { path: '/history', Screen: HistoryScreen },
};

export default function App() {
  const navigate = useNavigate();
  const go = useCallback(
    (key) => {
      navigate(ROUTES[key]?.path ?? '/');
      window.scrollTo(0, 0);
    },
    [navigate],
  );
  return (
    <Routes>
      {Object.entries(ROUTES).map(([key, { path, Screen }]) => (
        <Route key={key} path={path} element={<Screen go={go} onTab={go} />} />
      ))}
      <Route path="*" element={<Navigate to={ROUTES.login.path} replace />} />
    </Routes>
  );
}
