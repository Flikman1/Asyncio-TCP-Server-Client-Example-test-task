"""CLI entry point for running only the asyncio TCP server."""

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

from async_tcp_demo.config import ServerConfig
from async_tcp_demo.server import AsyncTCPServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the educational asyncio TCP server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--keepalive-interval", type=float, default=5.0)
    parser.add_argument("--drop-rate", type=float, default=0.1)
    parser.add_argument("--min-response-delay", type=float, default=0.1)
    parser.add_argument("--max-response-delay", type=float, default=1.0)
    parser.add_argument("--log-path", default=str(PROJECT_ROOT / "logs/server.jsonl"))
    return parser


async def async_main(args: argparse.Namespace) -> None:
    config = ServerConfig(
        host=args.host,
        port=args.port,
        keepalive_interval=args.keepalive_interval,
        drop_rate=args.drop_rate,
        min_response_delay=args.min_response_delay,
        max_response_delay=args.max_response_delay,
        log_path=args.log_path,
    )
    server = AsyncTCPServer(config)
    await server.start()
    print(f"Server listening on {server.host}:{server.port}")

    try:
        await asyncio.Event().wait()
    finally:
        await server.stop()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
