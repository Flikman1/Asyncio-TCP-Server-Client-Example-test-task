"""Asyncio TCP client for the educational protocol playground."""

from __future__ import annotations

import asyncio
import contextlib
import random
from typing import cast

from async_tcp_demo.config import ClientConfig
from async_tcp_demo.logging_config import configure_json_logger, log_event
from async_tcp_demo.metrics import MetricsCollector
from async_tcp_demo.protocol import Message, ProtocolError, decode_message, encode_message


class ConnectionLostError(ConnectionError):
    """Raised when the client loses its TCP connection."""


class AsyncTCPClient:
    """Educational asyncio TCP client with timeout, retry, and reconnect logic."""

    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self.logger = configure_json_logger(
            f"client-{self.config.client_id}",
            self.config.log_path,
        )
        self.metrics = MetricsCollector()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._receiver_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._pending_responses: dict[int, asyncio.Future[Message]] = {}
        self._request_counter = 0
        self._connected_once = False

    async def run(self, stop_event: asyncio.Event | None = None) -> MetricsCollector:
        """Run the client until it is stopped or reconnect attempts are exhausted."""

        external_stop = stop_event or asyncio.Event()
        reconnect_attempt = 0
        awaiting_reconnect = False

        try:
            while not self._should_stop(external_stop):
                try:
                    await self._connect()
                    if awaiting_reconnect:
                        self.metrics.record_reconnect()
                        log_event(
                            self.logger,
                            "reconnected",
                            client_id=self.config.client_id,
                            attempt=reconnect_attempt,
                        )
                    else:
                        log_event(
                            self.logger,
                            "connected",
                            client_id=self.config.client_id,
                            host=self.config.host,
                            port=self.config.port,
                        )

                    self._connected_once = True
                    reconnect_attempt = 0
                    awaiting_reconnect = False
                    await self._communication_loop(external_stop)
                except asyncio.CancelledError:
                    raise
                except (ConnectionLostError, OSError) as exc:
                    if self._should_stop(external_stop):
                        break

                    reconnect_attempt += 1
                    if reconnect_attempt > self.config.max_reconnect_attempts:
                        log_event(
                            self.logger,
                            "reconnect_exhausted",
                            client_id=self.config.client_id,
                            attempts=reconnect_attempt - 1,
                            error=str(exc),
                        )
                        break

                    awaiting_reconnect = self._connected_once or awaiting_reconnect
                    log_event(
                        self.logger,
                        "reconnect_scheduled",
                        client_id=self.config.client_id,
                        attempt=reconnect_attempt,
                        delay_s=self.config.reconnect_delay,
                        error=str(exc),
                    )
                    await self._close_connection()
                    await self._sleep_with_stop(self.config.reconnect_delay, external_stop)
                else:
                    break
        finally:
            await self._close_connection()
            log_event(self.logger, "client_stopped", client_id=self.config.client_id)

        return self.metrics

    async def stop(self) -> None:
        """Signal the client to stop and close the active connection."""

        self._stop_event.set()
        await self._close_connection()

    async def _connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(
            host=self.config.host,
            port=self.config.port,
        )

    async def _communication_loop(self, external_stop: asyncio.Event) -> None:
        self._receiver_task = asyncio.create_task(
            self._receive_loop(),
            name=f"client-{self.config.client_id}-receiver",
        )
        try:
            while not self._should_stop(external_stop):
                await self._ensure_receiver_alive()
                await self._sleep_with_stop(
                    random.uniform(
                        self.config.ping_min_interval,
                        self.config.ping_max_interval,
                    ),
                    external_stop,
                )
                if self._should_stop(external_stop):
                    return
                await self._ensure_receiver_alive()
                await self._send_ping_with_retry()
        finally:
            await self._cancel_receiver_task()

    async def _send_ping_with_retry(self) -> None:
        for attempt in range(self.config.max_retries + 1):
            request_id = self._next_request_id()
            future = asyncio.get_running_loop().create_future()
            self._pending_responses[request_id] = future
            started_at = asyncio.get_running_loop().time()

            await self._send_message(
                Message(
                    "PING",
                    {
                        "request_id": str(request_id),
                        "client_id": str(self.config.client_id),
                    },
                )
            )
            self.metrics.record_ping_sent()
            log_event(
                self.logger,
                "ping_sent",
                client_id=self.config.client_id,
                request_id=request_id,
                attempt=attempt + 1,
            )

            try:
                await asyncio.wait_for(future, timeout=self.config.response_timeout)
            except asyncio.TimeoutError:
                pending_future = self._pending_responses.pop(request_id, None)
                if pending_future is not None and not pending_future.done():
                    pending_future.cancel()

                self.metrics.record_timeout()
                log_event(
                    self.logger,
                    "timeout",
                    client_id=self.config.client_id,
                    request_id=request_id,
                    attempt=attempt + 1,
                )

                if attempt < self.config.max_retries:
                    self.metrics.record_retry()
                    log_event(
                        self.logger,
                        "retry",
                        client_id=self.config.client_id,
                        request_id=request_id,
                        next_attempt=attempt + 2,
                    )
                    continue
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                raise ConnectionLostError(str(exc)) from exc

            latency_ms = (asyncio.get_running_loop().time() - started_at) * 1000.0
            self.metrics.record_pong_received(latency_ms)
            log_event(
                self.logger,
                "pong_received",
                client_id=self.config.client_id,
                request_id=request_id,
                latency_ms=round(latency_ms, 3),
            )
            self._pending_responses.pop(request_id, None)
            return

    async def _receive_loop(self) -> None:
        reader = self._require_reader()
        try:
            while True:
                raw_message = await reader.readline()
                if not raw_message:
                    raise ConnectionLostError("server closed the connection")

                try:
                    message = decode_message(raw_message)
                except ProtocolError as exc:
                    log_event(
                        self.logger,
                        "invalid_message",
                        client_id=self.config.client_id,
                        error=str(exc),
                        raw_message=raw_message.decode("ascii", errors="replace").rstrip("\n"),
                    )
                    continue

                if message.message_type == "PONG":
                    await self._handle_pong(message)
                elif message.message_type == "KEEPALIVE":
                    log_event(
                        self.logger,
                        "keepalive_received",
                        client_id=self.config.client_id,
                        server_time=message.fields.get("server_time"),
                    )
                elif message.message_type == "ERROR":
                    log_event(
                        self.logger,
                        "server_error",
                        client_id=self.config.client_id,
                        message=message.fields.get("message", "unknown"),
                    )
                else:
                    log_event(
                        self.logger,
                        "unexpected_message",
                        client_id=self.config.client_id,
                        message_type=message.message_type,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._fail_pending_responses(exc)
            raise

    async def _handle_pong(self, message: Message) -> None:
        try:
            request_id = message.require_int("request_id")
        except ProtocolError as exc:
            log_event(
                self.logger,
                "invalid_pong",
                client_id=self.config.client_id,
                error=str(exc),
            )
            return

        future = self._pending_responses.get(request_id)
        if future is None or future.done():
            log_event(
                self.logger,
                "unexpected_pong",
                client_id=self.config.client_id,
                request_id=request_id,
            )
            return

        future.set_result(message)

    async def _send_message(self, message: Message) -> None:
        writer = self._require_writer()
        payload = encode_message(message.message_type, **message.fields)
        writer.write(payload)
        try:
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError) as exc:
            raise ConnectionLostError("failed to send message") from exc

    async def _close_connection(self) -> None:
        await self._cancel_receiver_task()
        self._fail_pending_responses(ConnectionLostError("connection closed"))

        writer = self._writer
        self._reader = None
        self._writer = None

        if writer is None or writer.is_closing():
            return

        writer.close()
        with contextlib.suppress(ConnectionResetError, BrokenPipeError):
            await writer.wait_closed()

    async def _cancel_receiver_task(self) -> None:
        task = self._receiver_task
        self._receiver_task = None
        if task is None:
            return

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, ConnectionLostError):
            await task

    async def _ensure_receiver_alive(self) -> None:
        task = self._receiver_task
        if task is None:
            raise ConnectionLostError("receiver task is not running")
        if not task.done():
            return

        if task.cancelled():
            raise ConnectionLostError("receiver task was cancelled")

        error = task.exception()
        if error is None:
            raise ConnectionLostError("receiver task stopped unexpectedly")
        raise ConnectionLostError(str(error)) from error

    def _fail_pending_responses(self, error: Exception) -> None:
        for future in self._pending_responses.values():
            if not future.done():
                future.set_exception(error)
        self._pending_responses.clear()

    async def _sleep_with_stop(self, delay: float, external_stop: asyncio.Event) -> None:
        if delay <= 0:
            return

        sleep_task = asyncio.create_task(asyncio.sleep(delay))
        external_task = asyncio.create_task(external_stop.wait())
        internal_task = asyncio.create_task(self._stop_event.wait())
        done, pending = await asyncio.wait(
            {sleep_task, external_task, internal_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        for task in pending:
            with contextlib.suppress(asyncio.CancelledError):
                await task

        completed_sleep = sleep_task in done and not sleep_task.cancelled()
        if completed_sleep:
            await cast(asyncio.Task[None], sleep_task)

    def _next_request_id(self) -> int:
        request_id = self._request_counter
        self._request_counter += 1
        return request_id

    def _require_reader(self) -> asyncio.StreamReader:
        if self._reader is None:
            raise ConnectionLostError("reader is not available")
        return self._reader

    def _require_writer(self) -> asyncio.StreamWriter:
        if self._writer is None:
            raise ConnectionLostError("writer is not available")
        return self._writer

    def _should_stop(self, external_stop: asyncio.Event) -> bool:
        return self._stop_event.is_set() or external_stop.is_set()
