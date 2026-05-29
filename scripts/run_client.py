"""CLI entry point for running a single asyncio TCP client."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from async_tcp_demo.client import AsyncTCPClient
from async_tcp_demo.config import ClientConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one educational asyncio TCP client.")
    parser.add_argument("--client-id", type=int, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--ping-min-interval", type=float, default=0.3)
    parser.add_argument("--ping-max-interval", type=float, default=3.0)
    parser.add_argument("--response-timeout", type=float, default=1.5)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--reconnect-delay", type=float, default=1.0)
    parser.add_argument("--max-reconnect-attempts", type=int, default=5)
    parser.add_argument("--log-path", default=None)
    return parser


async def async_main(args: argparse.Namespace) -> None:
    config = ClientConfig(
        client_id=args.client_id,
        host=args.host,
        port=args.port,
        ping_min_interval=args.ping_min_interval,
        ping_max_interval=args.ping_max_interval,
        response_timeout=args.response_timeout,
        max_retries=args.max_retries,
        reconnect_delay=args.reconnect_delay,
        max_reconnect_attempts=args.max_reconnect_attempts,
        log_path=args.log_path,
    )
    client = AsyncTCPClient(config)
    try:
        await client.run()
    finally:
        await client.stop()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
