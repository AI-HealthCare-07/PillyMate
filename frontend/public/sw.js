// PillyMate 서비스 워커: 웹 푸시를 받아 알림을 띄운다.

// 새 버전이 설치되면 기다리지 않고 바로 적용 (개발 중 sw.js 수정이 바로 반영되도록)
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

// 푸시를 받으면 알림 띄우기. 서버는 {"title": "...", "body": "..."} JSON으로 보낸다.
self.addEventListener("push", (event) => {
  console.log("[sw] push 받음:", event.data ? event.data.text() : "(내용 없음)");
  let title = "PillyMate";
  let body = "💊 약 먹일 시간이에요";

  if (event.data) {
    const text = event.data.text();
    try {
      const data = JSON.parse(text);
      title = data.title ?? title;
      body = data.body ?? body;
    } catch {
      body = text;
    }
  }

  event.waitUntil(
    self.registration
      .showNotification(title, { body })
      .then(() => console.log("[sw] 알림 표시 완료"))
      .catch((err) => console.error("[sw] 알림 표시 실패:", err)),
  );
});

// 알림을 클릭하면 PillyMate 열기
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow("/"));
});
