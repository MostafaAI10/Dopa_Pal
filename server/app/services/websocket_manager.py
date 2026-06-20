"""
WebSocket connection manager with Redis pub/sub for real-time broadcasts.

Manages per-user WebSocket connections and fans out state/task mutation events
from any backend process to all connected Electron clients via Redis channels.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("dopapal.ws")

CHANNEL_PREFIX = "dopapal:user:"


class ConnectionManager:
    """Tracks active WebSocket connections per user and relays Redis pub/sub messages."""

    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)
        self._redis: Redis | None = None
        self._subscriber_task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Initialize Redis client and start the subscriber loop."""
        self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await self._redis.ping()
            logger.info("Redis connection established for pub/sub")
        except Exception:
            logger.warning("Redis unavailable — WebSocket broadcasts will be local-only")
            self._redis = None
            return
        self._subscriber_task = asyncio.create_task(self._subscribe_loop())

    async def shutdown(self) -> None:
        """Tear down subscriber and Redis connection."""
        if self._subscriber_task and not self._subscriber_task.done():
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self._connections[user_id].append(websocket)
        logger.info("WS connected: user_id=%d  total=%d", user_id, len(self._connections[user_id]))

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        conns = self._connections.get(user_id)
        if conns and websocket in conns:
            conns.remove(websocket)
            if not conns:
                del self._connections[user_id]
        logger.info("WS disconnected: user_id=%d", user_id)

    # ------------------------------------------------------------------
    # Publishing (called from HTTP request handlers)
    # ------------------------------------------------------------------

    async def publish(self, user_id: int, event: str, data: dict[str, Any]) -> None:
        """Publish an event through Redis so all server instances receive it."""
        message = json.dumps({"event": event, "data": data})
        if self._redis:
            await self._redis.publish(f"{CHANNEL_PREFIX}{user_id}", message)
        else:
            # Fallback: direct local broadcast when Redis is down
            await self._send_to_user(user_id, message)

    # ------------------------------------------------------------------
    # Internal fan-out
    # ------------------------------------------------------------------

    async def _send_to_user(self, user_id: int, raw_message: str) -> None:
        """Send a raw JSON string to all WebSocket connections for a user."""
        dead: list[WebSocket] = []
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_text(raw_message)
            except (WebSocketDisconnect, RuntimeError):
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, user_id)

    async def _subscribe_loop(self) -> None:
        """Listen on Redis pub/sub for user-scoped channels and fan out."""
        if not self._redis:
            return
        pubsub = self._redis.pubsub()
        await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
        try:
            async for message in pubsub.listen():
                if message["type"] != "pmessage":
                    continue
                channel: str = message["channel"]
                # channel = "dopapal:user:42"
                try:
                    user_id = int(channel.rsplit(":", 1)[1])
                except (ValueError, IndexError):
                    continue
                await self._send_to_user(user_id, message["data"])
        except asyncio.CancelledError:
            await pubsub.punsubscribe()
            await pubsub.aclose()
            raise


# Module-level singleton; initialized during app lifespan
manager = ConnectionManager()
