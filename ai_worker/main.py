import asyncio
import signal

from ai_worker.core import default_logger as logger

POLL_INTERVAL_SECONDS = 5


async def run() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    logger.info("AI worker started")
    while not stop_event.is_set():
        # TODO: API ↔ 워커 통신 방식(Redis 큐 등) 확정 후 작업 수신/처리 로직 구현
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)
        except TimeoutError:
            continue
    logger.info("AI worker stopped")


if __name__ == "__main__":
    asyncio.run(run())
