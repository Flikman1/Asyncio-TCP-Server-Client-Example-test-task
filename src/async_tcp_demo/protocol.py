"""Simple line-based text protocol for the asyncio TCP demo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MESSAGE_TYPES = {"PING", "PONG", "KEEPALIVE", "ERROR"}


class ProtocolError(ValueError):
    """Raised when a protocol message cannot be encoded or decoded."""


@dataclass(slots=True, frozen=True)
class Message:
    """Protocol message represented as a message type and string fields."""

    message_type: str
    fields: dict[str, str] = field(default_factory=dict)

    def require(self, field_name: str) -> str:
        """Return a required field or raise ``ProtocolError``."""

        try:
            return self.fields[field_name]
        except KeyError as exc:
            raise ProtocolError(f"missing required field: {field_name}") from exc

    def require_int(self, field_name: str) -> int:
        """Return a required integer field or raise ``ProtocolError``."""

        value = self.require(field_name)
        try:
            return int(value)
        except ValueError as exc:
            raise ProtocolError(f"field {field_name!r} must be an integer") from exc


def encode_message(message_type: str, **fields: Any) -> bytes:
    """Encode a protocol message into a newline-terminated ASCII payload."""

    normalized_type = message_type.upper()
    if normalized_type not in MESSAGE_TYPES:
        raise ProtocolError(f"unsupported message type: {message_type}")

    parts = [normalized_type]
    for key, value in fields.items():
        _validate_token(key, label="field name")
        string_value = str(value)
        _validate_token(string_value, label=f"value for {key}")
        parts.append(f"{key}={string_value}")

    return (" ".join(parts) + "\n").encode("ascii")


def decode_message(raw_message: bytes | str) -> Message:
    """Decode a newline-terminated text message into a ``Message`` object."""

    if isinstance(raw_message, bytes):
        try:
            text = raw_message.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ProtocolError("message must be ASCII") from exc
    else:
        text = raw_message

    line = text.rstrip("\n")
    if not line:
        raise ProtocolError("empty message")

    parts = line.split()
    if not parts:
        raise ProtocolError("empty message")

    message_type = parts[0].upper()
    if message_type not in MESSAGE_TYPES:
        raise ProtocolError(f"unsupported message type: {parts[0]}")

    fields: dict[str, str] = {}
    for token in parts[1:]:
        if "=" not in token:
            raise ProtocolError(f"invalid field token: {token}")
        key, value = token.split("=", 1)
        if not key:
            raise ProtocolError("field name cannot be empty")
        _validate_token(key, label="field name")
        _validate_token(value, label=f"value for {key}")
        fields[key] = value

    return Message(message_type=message_type, fields=fields)


def _validate_token(token: str, *, label: str) -> None:
    if not token:
        raise ProtocolError(f"{label} cannot be empty")
    if any(character.isspace() for character in token):
        raise ProtocolError(f"{label} cannot contain whitespace")
    if "\n" in token or "\r" in token:
        raise ProtocolError(f"{label} cannot contain line breaks")
    if label == "field name" and "=" in token:
        raise ProtocolError("field names cannot contain '='")
