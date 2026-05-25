from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from datetime import datetime
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from services.api.config import ApiSettings
from services.api.repository import ApiRepository
from shared.kafka.messages import ProcessedAQBatchSummaryMessage
from shared.logging_config import get_logger
from shared.time_utils import utc_now


class ConnectionManager:
    def __init__(self, *, duplicate_window: int = 500) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._seen_batches: set[int] = set()
        self._seen_order: deque[int] = deque(maxlen=duplicate_window)
        self.consumer_status: dict[str, Any] = {"status": "not_started"}
        self._logger = get_logger(__name__)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def send_event(self, websocket: WebSocket, *, event: str, data: dict[str, Any] | None = None) -> None:
        await websocket.send_json({"event": event, "timestamp": utc_now().isoformat(), "data": data or {}})

    async def broadcast_processed_batch(self, summary: ProcessedAQBatchSummaryMessage) -> bool:
        if not self._mark_batch_seen(summary.batch_id):
            self._logger.info("websocket_duplicate_batch_skipped", batch_id=summary.batch_id)
            return False
        payload = {"event": "new_readings", "timestamp": utc_now().isoformat(), "data": summary.model_dump(mode="json")}
        async with self._lock:
            connections = list(self._connections)
        stale_connections: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception as exc:
                stale_connections.append(websocket)
                self._logger.warning("websocket_broadcast_failed", batch_id=summary.batch_id, error=str(exc))
        for websocket in stale_connections:
            await self.disconnect(websocket)
        return True

    async def broadcast_timestamp_advance(self, latest_timestamp: datetime) -> None:
        payload = {
            "event": "new_readings",
            "timestamp": utc_now().isoformat(),
            "data": {"latest_timestamp": latest_timestamp.isoformat()},
        }
        async with self._lock:
            connections = list(self._connections)
        stale_connections: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception as exc:
                stale_connections.append(websocket)
                self._logger.warning("websocket_broadcast_failed", error=str(exc))
        for websocket in stale_connections:
            await self.disconnect(websocket)

    async def websocket_loop(self, websocket: WebSocket, *, heartbeat_seconds: float) -> None:
        try:
            while True:
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=heartbeat_seconds)
                except TimeoutError:
                    await self.send_event(websocket, event="heartbeat", data={"active_connections": await self.connection_count()})
        except WebSocketDisconnect:
            await self.disconnect(websocket)

    async def connection_count(self) -> int:
        async with self._lock:
            return len(self._connections)

    def _mark_batch_seen(self, batch_id: int) -> bool:
        if batch_id in self._seen_batches:
            return False
        if len(self._seen_order) == self._seen_order.maxlen:
            oldest = self._seen_order.popleft()
            self._seen_batches.discard(oldest)
        self._seen_order.append(batch_id)
        self._seen_batches.add(batch_id)
        return True


class KafkaLiveFeedConsumer:
    def __init__(self, *, settings: ApiSettings, manager: ConnectionManager) -> None:
        self.settings = settings
        self.manager = manager
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._logger = get_logger(__name__)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_forever(), name="api-kafka-live-feed")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._consume_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.manager.consumer_status = {"status": "degraded", "last_error": str(exc), "checked_at": utc_now().isoformat()}
                self._logger.warning("api_kafka_consumer_retrying", error=str(exc), retry_seconds=self.settings.kafka_retry_seconds)
                await asyncio.sleep(self.settings.kafka_retry_seconds)

    async def _consume_once(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer
        except ModuleNotFoundError as exc:
            self.manager.consumer_status = {"status": "down", "last_error": f"missing dependency: {exc.name}", "checked_at": utc_now().isoformat()}
            await asyncio.sleep(self.settings.kafka_retry_seconds)
            return

        consumer = AIOKafkaConsumer(
            self.settings.processed_aq_topic,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id=self.settings.kafka_group_id,
            enable_auto_commit=True,
            auto_offset_reset="latest",
        )
        await consumer.start()
        self.manager.consumer_status = {"status": "ok", "topic": self.settings.processed_aq_topic, "started_at": utc_now().isoformat()}
        try:
            async for message in consumer:
                if self._stop_event.is_set():
                    break
                await self._handle_message(message.value)
        finally:
            await consumer.stop()

    async def _handle_message(self, payload: bytes) -> None:
        try:
            summary = ProcessedAQBatchSummaryMessage.model_validate_json(payload)
        except Exception as exc:
            self.manager.consumer_status = {"status": "degraded", "last_error": f"invalid processed batch: {exc}", "checked_at": utc_now().isoformat()}
            self._logger.warning("api_processed_batch_invalid", error=str(exc))
            return
        await self.manager.broadcast_processed_batch(summary)
        self.manager.consumer_status = {
            "status": "ok",
            "last_batch_id": summary.batch_id,
            "last_processed_at": _datetime_iso(summary.processed_at),
            "checked_at": utc_now().isoformat(),
        }


def _datetime_iso(value: datetime) -> str:
    return value.isoformat()


class DBLiveFeedNotifier:
    def __init__(self, *, settings: ApiSettings, manager: ConnectionManager, session_factory: object) -> None:
        self.settings = settings
        self.manager = manager
        self.session_factory = session_factory
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._logger = get_logger(__name__)
        self._latest_timestamp: datetime | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_forever(), name="api-db-live-feed")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def _run_forever(self) -> None:
        self.manager.consumer_status = {"status": "ok", "mode": "db_notifier", "started_at": utc_now().isoformat()}
        while not self._stop_event.is_set():
            try:
                async with self.session_factory() as session:
                    repo = ApiRepository(session, self.settings)
                    latest_timestamp = await repo.fetch_latest_aq_timestamp()

                if latest_timestamp is not None and (self._latest_timestamp is None or latest_timestamp > self._latest_timestamp):
                    self._latest_timestamp = latest_timestamp
                    await self.manager.broadcast_timestamp_advance(latest_timestamp)

                self.manager.consumer_status = {
                    "status": "ok",
                    "mode": "db_notifier",
                    "last_observed_timestamp": latest_timestamp.isoformat() if latest_timestamp else None,
                    "checked_at": utc_now().isoformat(),
                }
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.manager.consumer_status = {
                    "status": "degraded",
                    "mode": "db_notifier",
                    "last_error": str(exc),
                    "checked_at": utc_now().isoformat(),
                }
                self._logger.warning("api_db_notifier_retrying", error=str(exc), retry_seconds=self.settings.kafka_retry_seconds)
            await asyncio.sleep(self.settings.kafka_retry_seconds)
