"""Asyncio TCP server for the educational protocol playground."""

from __future__ import annotations

import asyncio
import contextlib
import random
from dataclasses import dataclass, field
from datetime import datetime

from async_tcp_demo.config import ServerConfig
from async_tcp_demo.logging_config import configure_json_logger, log_event
from async_tcp_demo.protocol import Message, ProtocolError, decode_message, encode_message


@dataclass(eq=False, slots=True)
class ClientConnection:
    """A connected client with its writer and write lock."""

    writer: asyncio.StreamWriter
    peername: str
    write_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class AsyncTCPServer:
    """Educational asyncio TCP server with keepalive and dropped responses."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.clients: set[ClientConnection] = set()
        self.logger = configure_json_logger("server", self.config.log_path)
        self._server: asyncio.base_events.Server | None = None
        self._keepalive_task: asyncio.Task[None] | None = None
        self._bound_port = config.port
        self._stopping = False

    @property
    def host(self) -> str:
        return self.config.host

    @property
    def port(self) -> int:
        return self._bound_port

    async def start(self) -> None:
        """Start listening for TCP connections and launch keepalive loop."""

        if self._server is not None:
            return

        self._server = await asyncio.start_server(
            self.handle_client,
            host=self.config.host,
            port=self.config.port,
        )

        sockets = self._server.sockets or []
        if sockets:
            self._bound_port = int(sockets[0].getsockname()[1])

        self._stopping = False
        self._keepalive_task = asyncio.create_task(self._keepalive_loop(), name="server-keepalive")
        log_event(
            self.logger,
            "server_started",
            host=self.config.host,
            port=self._bound_port,
            keepalive_interval=self.config.keepalive_interval,
            drop_rate=self.config.drop_rate,
        )

    async def stop(self) -> None:
        """Stop the server, cancel background tasks, and close all clients."""

        if self._stopping:
            return

        self._stopping = True

        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._keepalive_task
            self._keepalive_task = None

        clients = list(self.clients)
        for connection in clients:
            await self._close_connection(connection)

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        log_event(self.logger, "server_stopped")

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single client connection until it disconnects."""

        connection = ClientConnection(
            writer=writer,
            peername=_format_peername(writer.get_extra_info("peername")),
        )
        self.clients.add(connection)
        log_event(
            self.logger,
            "client_connected",
            peername=connection.peername,
            active_clients=len(self.clients),
        )

        try:
            while True:
                raw_message = await reader.readline()
                if not raw_message:
                    break

                try:
                    message = decode_message(raw_message)
                except ProtocolError as exc:
                    log_event(
                        self.logger,
                        "invalid_message",
                        peername=connection.peername,
                        error=str(exc),
                        raw_message=raw_message.decode("ascii", errors="replace").rstrip("\n"),
                    )
                    await self._send_message(
                        connection,
                        Message("ERROR", {"message": "invalid_request"}),
                    )
                    continue

                log_event(
                    self.logger,
                    "message_received",
                    peername=connection.peername,
                    message_type=message.message_type,
                    fields=message.fields,
                )

                if message.message_type != "PING":
                    await self._send_message(
                        connection,
                        Message("ERROR", {"message": "unexpected_message_type"}),
                    )
                    continue

                await self._handle_ping(connection, message)
        except asyncio.CancelledError:
            raise
        finally:
            await self._close_connection(connection)
            log_event(
                self.logger,
                "client_disconnected",
                peername=connection.peername,
                active_clients=len(self.clients),
            )

    async def _handle_ping(self, connection: ClientConnection, message: Message) -> None:
        try:
            request_id = message.require_int("request_id")
            client_id = message.require_int("client_id")
        except ProtocolError:
            await self._send_message(connection, Message("ERROR", {"message": "invalid_ping"}))
            return

        if random.random() < self.config.drop_rate:
            log_event(
                self.logger,
                "ping_dropped",
                peername=connection.peername,
                request_id=request_id,
                client_id=client_id,
            )
            return

        response_delay = random.uniform(
            self.config.min_response_delay,
            self.config.max_response_delay,
        )
        if response_delay > 0:
            await asyncio.sleep(response_delay)

        server_time = datetime.now().isoformat(timespec="milliseconds")
        pong_message = Message(
            "PONG",
            {
                "request_id": str(request_id),
                "client_id": str(client_id),
                "server_time": server_time,
            },
        )
        await self._send_message(connection, pong_message)
        log_event(
            self.logger,
            "pong_sent",
            peername=connection.peername,
            request_id=request_id,
            client_id=client_id,
            response_delay_ms=round(response_delay * 1000.0, 3),
        )

    async def _keepalive_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.config.keepalive_interval)
                if not self.clients:
                    continue

                keepalive_message = Message(
                    "KEEPALIVE",
                    {"server_time": datetime.now().isoformat(timespec="milliseconds")},
                )
                recipients = 0
                for connection in list(self.clients):
                    try:
                        await self._send_message(connection, keepalive_message)
                    except ConnectionError:
                        await self._close_connection(connection)
                    else:
                        recipients += 1

                if recipients:
                    log_event(self.logger, "keepalive_sent", recipients=recipients)
        except asyncio.CancelledError:
            pass

    async def _send_message(self, connection: ClientConnection, message: Message) -> None:
        if connection.writer.is_closing():
            raise ConnectionError("writer is closing")

        payload = encode_message(message.message_type, **message.fields)
        async with connection.write_lock:
            connection.writer.write(payload)
            try:
                await connection.writer.drain()
            except ConnectionResetError as exc:
                raise ConnectionError("connection reset during drain") from exc

    async def _close_connection(self, connection: ClientConnection) -> None:
        if connection not in self.clients:
            writer = connection.writer
            if not writer.is_closing():
                writer.close()
                with contextlib.suppress(ConnectionResetError, BrokenPipeError):
                    await writer.wait_closed()
            return

        self.clients.discard(connection)
        writer = connection.writer
        if writer.is_closing():
            return

        writer.close()
        with contextlib.suppress(ConnectionResetError, BrokenPipeError):
            await writer.wait_closed()


def _format_peername(peername: object) -> str:
    if isinstance(peername, tuple) and len(peername) >= 2:
        return f"{peername[0]}:{peername[1]}"
    return "unknown"
