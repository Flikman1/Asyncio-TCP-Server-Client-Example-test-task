from __future__ import annotations

import asyncio

import pytest

from async_tcp_demo.config import ServerConfig
from async_tcp_demo.protocol import decode_message, encode_message
from async_tcp_demo.server import AsyncTCPServer


@pytest.mark.asyncio
async def test_server_starts() -> None:
    server = AsyncTCPServer(
        ServerConfig(
            port=0,
            keepalive_interval=1.0,
            drop_rate=0.0,
            min_response_delay=0.0,
            max_response_delay=0.0,
            log_path="logs/test_server_start.jsonl",
        )
    )
    await server.start()
    try:
        assert server.port > 0
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_client_can_connect_to_server() -> None:
    server = AsyncTCPServer(
        ServerConfig(
            port=0,
            keepalive_interval=1.0,
            drop_rate=0.0,
            min_response_delay=0.0,
            max_response_delay=0.0,
            log_path="logs/test_server_connect.jsonl",
        )
    )
    await server.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        try:
            assert len(server.clients) == 1
            assert reader is not None
        finally:
            writer.close()
            await writer.wait_closed()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_server_replies_with_pong() -> None:
    server = AsyncTCPServer(
        ServerConfig(
            port=0,
            keepalive_interval=1.0,
            drop_rate=0.0,
            min_response_delay=0.0,
            max_response_delay=0.0,
            log_path="logs/test_server_pong.jsonl",
        )
    )
    await server.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        try:
            writer.write(encode_message("PING", request_id=1, client_id=42))
            await writer.drain()
            response = await asyncio.wait_for(reader.readline(), timeout=0.2)
            message = decode_message(response)
            assert message.message_type == "PONG"
            assert message.fields["request_id"] == "1"
            assert message.fields["client_id"] == "42"
        finally:
            writer.close()
            await writer.wait_closed()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_server_sends_keepalive() -> None:
    server = AsyncTCPServer(
        ServerConfig(
            port=0,
            keepalive_interval=0.05,
            drop_rate=0.0,
            min_response_delay=0.0,
            max_response_delay=0.0,
            log_path="logs/test_server_keepalive.jsonl",
        )
    )
    await server.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        try:
            response = await asyncio.wait_for(reader.readline(), timeout=0.2)
            message = decode_message(response)
            assert message.message_type == "KEEPALIVE"
        finally:
            writer.close()
            await writer.wait_closed()
    finally:
        await server.stop()
