"""Configuration objects for the asyncio TCP demo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8888


@dataclass(slots=True)
class ServerConfig:
    """Settings for the educational TCP server."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    keepalive_interval: float = 5.0
    drop_rate: float = 0.1
    min_response_delay: float = 0.1
    max_response_delay: float = 1.0
    log_path: Path | str = Path("logs/server.jsonl")

    def __post_init__(self) -> None:
        self.log_path = Path(self.log_path)
        if self.port < 0:
            raise ValueError("port must be >= 0")
        if not 0.0 <= self.drop_rate <= 1.0:
            raise ValueError("drop_rate must be between 0 and 1")
        if self.keepalive_interval <= 0:
            raise ValueError("keepalive_interval must be > 0")
        if self.min_response_delay < 0 or self.max_response_delay < 0:
            raise ValueError("response delays must be >= 0")
        if self.max_response_delay < self.min_response_delay:
            raise ValueError("max_response_delay must be >= min_response_delay")


@dataclass(slots=True)
class ClientConfig:
    """Settings for a single TCP client."""

    client_id: int
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    ping_min_interval: float = 0.3
    ping_max_interval: float = 3.0
    response_timeout: float = 1.5
    max_retries: int = 2
    reconnect_delay: float = 1.0
    max_reconnect_attempts: int = 5
    log_path: Path | str | None = None

    def __post_init__(self) -> None:
        if self.log_path is None:
            self.log_path = Path(f"logs/client_{self.client_id}.jsonl")
        else:
            self.log_path = Path(self.log_path)

        if self.client_id < 0:
            raise ValueError("client_id must be >= 0")
        if self.port < 0:
            raise ValueError("port must be >= 0")
        if self.ping_min_interval < 0 or self.ping_max_interval < 0:
            raise ValueError("ping intervals must be >= 0")
        if self.ping_max_interval < self.ping_min_interval:
            raise ValueError("ping_max_interval must be >= ping_min_interval")
        if self.response_timeout <= 0:
            raise ValueError("response_timeout must be > 0")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.reconnect_delay < 0:
            raise ValueError("reconnect_delay must be >= 0")
        if self.max_reconnect_attempts < 0:
            raise ValueError("max_reconnect_attempts must be >= 0")
