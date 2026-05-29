"""CLI entry point for running the server and multiple clients in one demo process."""

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
from async_tcp_demo.config import ClientConfig, ServerConfig
from async_tcp_demo.metrics import merge_metrics
from async_tcp_demo.server import AsyncTCPServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the educational asyncio TCP demo.")
    parser.add_argument("--clients", type=int, default=5)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--keepalive-interval", type=float, default=5.0)
    parser.add_argument("--drop-rate", type=float, default=0.1)
    parser.add_argument("--min-response-delay", type=float, default=0.1)
    parser.add_argument("--max-response-delay", type=float, default=1.0)
    parser.add_argument("--ping-min-interval", type=float, default=0.3)
    parser.add_argument("--ping-max-interval", type=float, default=3.0)
    parser.add_argument("--response-timeout", type=float, default=1.5)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--reconnect-delay", type=float, default=1.0)
    parser.add_argument("--max-reconnect-attempts", type=int, default=5)
    parser.add_argument("--server-log-path", default=str(PROJECT_ROOT / "logs/server.jsonl"))
    parser.add_argument("--client-log-dir", default=str(PROJECT_ROOT / "logs"))
    return parser


async def async_main(args: argparse.Namespace) -> None:
    server = AsyncTCPServer(
        ServerConfig(
            host=args.host,
            port=args.port,
            keepalive_interval=args.keepalive_interval,
            drop_rate=args.drop_rate,
            min_response_delay=args.min_response_delay,
            max_response_delay=args.max_response_delay,
            log_path=args.server_log_path,
        )
    )
    await server.start()
    print(f"Demo server listening on {server.host}:{server.port}")

    stop_event = asyncio.Event()
    client_log_dir = Path(args.client_log_dir)
    clients = [
        AsyncTCPClient(
            ClientConfig(
                client_id=client_id,
                host=args.host,
                port=server.port,
                ping_min_interval=args.ping_min_interval,
                ping_max_interval=args.ping_max_interval,
                response_timeout=args.response_timeout,
                max_retries=args.max_retries,
                reconnect_delay=args.reconnect_delay,
                max_reconnect_attempts=args.max_reconnect_attempts,
                log_path=client_log_dir / f"client_{client_id}.jsonl",
            )
        )
        for client_id in range(args.clients)
    ]

    tasks = [
        asyncio.create_task(client.run(stop_event), name=f"client-{client.config.client_id}")
        for client in clients
    ]
    interrupted = False
    try:
        await asyncio.sleep(args.duration)
    except asyncio.CancelledError:
        interrupted = True
    finally:
        stop_event.set()
        for client in clients:
            await client.stop()
        await asyncio.gather(*tasks, return_exceptions=True)
        await server.stop()

    summary = merge_metrics([client.metrics for client in clients])
    print()
    print(summary.format_summary(clients=args.clients))
    if interrupted:
        raise asyncio.CancelledError


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
