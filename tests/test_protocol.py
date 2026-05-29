from __future__ import annotations

import pytest

from async_tcp_demo.protocol import Message, ProtocolError, decode_message, encode_message


def test_encode_ping() -> None:
    payload = encode_message("PING", request_id=1, client_id=2)
    assert payload == b"PING request_id=1 client_id=2\n"


def test_decode_ping() -> None:
    message = decode_message(b"PING request_id=7 client_id=3\n")
    assert message == Message("PING", {"request_id": "7", "client_id": "3"})


def test_encode_pong() -> None:
    payload = encode_message("PONG", request_id=1, client_id=2, server_time="2026-05-30T12:00:00")
    assert payload == b"PONG request_id=1 client_id=2 server_time=2026-05-30T12:00:00\n"


def test_decode_keepalive() -> None:
    message = decode_message("KEEPALIVE server_time=2026-05-30T12:00:00\n")
    assert message.message_type == "KEEPALIVE"
    assert message.fields["server_time"] == "2026-05-30T12:00:00"


def test_invalid_message_raises_protocol_error() -> None:
    with pytest.raises(ProtocolError):
        decode_message("PING request_id\n")
