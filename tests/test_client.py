from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from async_tcp_demo.client import AsyncTCPClient
from async_tcp_demo.config import ClientConfig
from async_tcp_demo.protocol import Message, decode_message, encode_message

Handler = Callable[[asyncio.StreamReader, asyncio.StreamWriter, list[Message]], Awaitable[None]]


async def run_client_server_test(
    handler: Handler,
    config: ClientConfig,
    predicate: Callable[[AsyncTCPClient, list[Message]], bool],
) -> tuple[AsyncTCPClient, list[Message]]:
    received_messages: list[Message] = []
    server = await asyncio.start_server(
        lambda reader, writer: handler(reader, writer, received_messages),
        host="127.0.0.1",
        port=0,
    )
    port = int(server.sockets[0].getsockname()[1])
    config.port = port
    client = AsyncTCPClient(config)
    stop_event = asyncio.Event()
    client_task = asyncio.create_task(client.run(stop_event))

    try:
        await asyncio.wait_for(
            _wait_for_condition(lambda: predicate(client, received_messages)),
            timeout=1.0,
        )
    finally:
        stop_event.set()
        await client.stop()
        await asyncio.gather(client_task, return_exceptions=True)
        server.close()
        await server.wait_closed()

    return client, received_messages


async def _wait_for_condition(predicate: Callable[[], bool]) -> None:
    while not predicate():
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_client_sends_ping() -> None:
    async def handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        messages: list[Message],
    ) -> None:
        raw_message = await reader.readline()
        messages.append(decode_message(raw_message))
        writer.write(
            encode_message(
                "PONG",
                request_id=0,
                client_id=1,
                server_time="2026-05-30T12:00:00",
            )
        )
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    client, messages = await run_client_server_test(
        handler,
        ClientConfig(
            client_id=1,
            ping_min_interval=0.01,
            ping_max_interval=0.01,
            response_timeout=0.05,
            max_retries=0,
            reconnect_delay=0.01,
            max_reconnect_attempts=0,
            log_path="logs/test_client_send_ping.jsonl",
        ),
        lambda client, messages: client.metrics.sent_pings >= 1 and len(messages) >= 1,
    )

    assert messages[0].message_type == "PING"
    assert client.metrics.sent_pings >= 1


@pytest.mark.asyncio
async def test_client_handles_pong() -> None:
    async def handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        messages: list[Message],
    ) -> None:
        raw_message = await reader.readline()
        message = decode_message(raw_message)
        messages.append(message)
        writer.write(
            encode_message(
                "PONG",
                request_id=message.fields["request_id"],
                client_id=message.fields["client_id"],
                server_time="2026-05-30T12:00:00",
            )
        )
        await writer.drain()
        await asyncio.sleep(0.1)

    client, _ = await run_client_server_test(
        handler,
        ClientConfig(
            client_id=2,
            ping_min_interval=0.01,
            ping_max_interval=0.01,
            response_timeout=0.05,
            max_retries=0,
            reconnect_delay=0.01,
            max_reconnect_attempts=0,
            log_path="logs/test_client_pong.jsonl",
        ),
        lambda client, _: client.metrics.received_pongs >= 1,
    )

    assert client.metrics.received_pongs >= 1
    assert client.metrics.average_latency is not None


@pytest.mark.asyncio
async def test_client_records_timeout() -> None:
    async def handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        messages: list[Message],
    ) -> None:
        raw_message = await reader.readline()
        messages.append(decode_message(raw_message))
        await asyncio.sleep(0.2)
        writer.close()
        await writer.wait_closed()

    client, _ = await run_client_server_test(
        handler,
        ClientConfig(
            client_id=3,
            ping_min_interval=0.01,
            ping_max_interval=0.01,
            response_timeout=0.05,
            max_retries=0,
            reconnect_delay=0.01,
            max_reconnect_attempts=0,
            log_path="logs/test_client_timeout.jsonl",
        ),
        lambda client, _: client.metrics.timeouts >= 1,
    )

    assert client.metrics.timeouts >= 1


@pytest.mark.asyncio
async def test_client_retries_after_timeout() -> None:
    async def handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        messages: list[Message],
    ) -> None:
        first_message = decode_message(await reader.readline())
        messages.append(first_message)
        second_message = decode_message(await reader.readline())
        messages.append(second_message)
        writer.write(
            encode_message(
                "PONG",
                request_id=second_message.fields["request_id"],
                client_id=second_message.fields["client_id"],
                server_time="2026-05-30T12:00:00",
            )
        )
        await writer.drain()
        await asyncio.sleep(0.1)

    client, messages = await run_client_server_test(
        handler,
        ClientConfig(
            client_id=4,
            ping_min_interval=0.01,
            ping_max_interval=0.01,
            response_timeout=0.05,
            max_retries=1,
            reconnect_delay=0.01,
            max_reconnect_attempts=0,
            log_path="logs/test_client_retry.jsonl",
        ),
        lambda client, messages: (
            client.metrics.retries >= 1
            and client.metrics.received_pongs >= 1
            and len(messages) >= 2
        ),
    )

    assert client.metrics.retries >= 1
    assert client.metrics.received_pongs >= 1
    assert len(messages) >= 2
