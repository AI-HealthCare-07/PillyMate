# PillyMate Frontend (React + Tailwind CSS)

Figma "PillyMate 1차 MVP 화면 설계"의 화면, 색, 간격을 옮긴 프론트엔드예요.

## 실행

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

개발 서버는 `/api/*` 요청을 `http://localhost:8000`(FastAPI)으로 넘겨요.
다른 주소를 쓰려면 `VITE_API_PROXY=http://host:port npm run dev`.

## 화면 주소

| 키 | 주소 | 화면 |
| --- | --- | --- |
| `login` | `/login` | S-01 로그인 |
| `children` | `/children` | S-02 아이 목록 |
| `child-add` | `/children/new` | S-02 아이 추가 |
| `upload` | `/upload` | S-03 처방 올리기 |
| `reading` | `/upload/reading` | S-03 읽는 중 |
| `confirm` | `/prescriptions/confirm` | S-04 처방 내용 확인 |
| `guide-loading` | `/guide/loading` | S-05 만드는 중 |
| `guide` | `/guide` | S-05 복약 가이드 |
| `guide-error` | `/guide/error` | S-05 실패 |
| `history` | `/history` | S-07 기록 |
| `chat` | `/chat` | 챗봇 |

화면 컴포넌트는 `go('confirm')`처럼 키로 이동하고, 주소는 `src/App.jsx`의 `ROUTES`에서만 관리해요.

## 구조

- `tailwind.config.js`: Figma 색 변수, 글자 크기(줄 간격·자간 포함), 모서리, 그림자 토큰
- `src/components/ui`: Button, SmallButton, IconButton, Field, Segmented, SelectChip, FilterChip, Tag, Panel, Avatar, ChildSwitcher, Logo, Header, TabBar, NavBar(상단 바: 로고 + 메뉴 드로어), Drawer, Modal, AppShell
- `src/components/rx`: RxPaper(처방전 일러스트), Highlight·LowValue(흐릿함 형광펜), LowConfidenceBanner, MedCard·MedList(약 카드, 고치기·추가·빼기), 가이드 섹션들
- `src/screens`: S-01 ~ S-07 화면 10개
- `src/data/sample.js`: 예시 데이터(실제 의학 정보 아님). API 연동 시 응답으로 바꿔 주세요.

## 반응형

모바일 우선, 1024px(`lg`)부터 데스크톱 배치. 640~1023px에서는 모바일 배치를 560px 폭으로 가운데 정렬해요.
