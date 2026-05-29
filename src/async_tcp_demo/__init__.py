"""Educational asyncio TCP demo package."""

from async_tcp_demo.client import AsyncTCPClient
from async_tcp_demo.config import ClientConfig, ServerConfig
from async_tcp_demo.metrics import MetricsCollector, merge_metrics
from async_tcp_demo.protocol import Message, ProtocolError, decode_message, encode_message
from async_tcp_demo.server import AsyncTCPServer

__all__ = [
    "AsyncTCPClient",
    "AsyncTCPServer",
    "ClientConfig",
    "ServerConfig",
    "MetricsCollector",
    "Message",
    "ProtocolError",
    "decode_message",
    "encode_message",
    "merge_metrics",
]

__version__ = "0.1.0"
