# Async TCP Protocol Playground

## Overview

This repository is an educational asyncio networking project. It demonstrates a small TCP server and multiple TCP clients that exchange line-based text messages over a simple `PING`/`PONG` protocol.

The goal is clarity, not production complexity. There is no web framework, database, message broker, or orchestration layer here. The project focuses on core networking topics:

- `asyncio`
- TCP sockets
- multiple concurrent clients
- a readable text protocol
- keepalive messages
- response timeouts
- retries
- reconnects
- structured JSONL logging
- basic metrics
- automated tests

## Features

- Async TCP server that accepts multiple clients
- Async TCP clients that send `PING` messages at random intervals
- `PONG` replies with matching `request_id` and `client_id`
- Configurable response drops to simulate packet loss or missing replies
- Server-side `KEEPALIVE` broadcasts
- Client-side timeout, retry, and reconnect logic
- Structured JSONL logs for both server and clients
- Metrics summary for demo runs
- `pytest` and `pytest-asyncio` coverage for protocol, server, client, and metrics

## Architecture

The project uses a compact `src` layout:

- `protocol.py` defines message encoding and decoding
- `server.py` owns TCP connection handling and keepalive broadcasting
- `client.py` owns ping loops, timeout handling, retry, and reconnect behavior
- `logging_config.py` writes JSONL events
- `metrics.py` collects runtime counters and latency statistics
- `scripts/` provides CLI entry points for demo, server-only, and client-only modes

## Message Protocol

The protocol is line-based and readable. Every message ends with `\n`, so both server and clients can use `reader.readline()`.

Supported message types:

- `PING`
- `PONG`
- `KEEPALIVE`
- `ERROR`

Examples:

```text
PING request_id=1 client_id=2
PONG request_id=1 client_id=2 server_time=2026-05-30T12:00:00.123
KEEPALIVE server_time=2026-05-30T12:00:05.000
ERROR message=invalid_request
```

Protocol behavior:

- a client sends `PING` with a unique `request_id`
- the server usually replies with `PONG`
- sometimes the server intentionally drops the reply based on `drop_rate`
- the client waits for a matching `PONG`
- if the timeout expires, the client records a timeout and can retry
- if the connection is lost, the client reconnects
- the server periodically sends `KEEPALIVE` to all connected clients

## Project Structure

```text
.
├── README.md
├── README.ru.md
├── pyproject.toml
├── .gitignore
├── logs/
│   └── .gitkeep
├── scripts/
│   ├── run_client.py
│   ├── run_demo.py
│   └── run_server.py
├── src/
│   └── async_tcp_demo/
│       ├── __init__.py
│       ├── client.py
│       ├── config.py
│       ├── logging_config.py
│       ├── metrics.py
│       ├── protocol.py
│       └── server.py
└── tests/
    ├── conftest.py
    ├── test_client.py
    ├── test_metrics.py
    ├── test_protocol.py
    └── test_server.py
```

## Installation

```bash
pip install -e ".[dev]"
```

Python `3.10+` is required.

## Usage

### Run demo

```bash
python scripts/run_demo.py --clients 5 --duration 60
```

### Run server

```bash
python scripts/run_server.py --host 127.0.0.1 --port 8888 --drop-rate 0.1 --keepalive-interval 5
```

### Run client

```bash
python scripts/run_client.py --client-id 1 --host 127.0.0.1 --port 8888
```

## Configuration

Server options:

- `host`
- `port`
- `keepalive_interval`
- `drop_rate`
- `min_response_delay`
- `max_response_delay`
- `log_path`

Client options:

- `client_id`
- `host`
- `port`
- `ping_min_interval`
- `ping_max_interval`
- `response_timeout`
- `max_retries`
- `reconnect_delay`
- `max_reconnect_attempts`
- `log_path`

All CLI entry points are implemented with `argparse`.

## Logs

Logs are written to `logs/*.jsonl`. Each line is one JSON object.

Example:

```json
{"timestamp":"2026-05-30T12:00:01.123","level":"info","logger":"client-1:F:\\Asyncio-TCP-Server-Client-Example-test-task\\logs\\client_1.jsonl","event":"ping_sent","client_id":1,"request_id":42,"attempt":1}
{"timestamp":"2026-05-30T12:00:01.551","level":"info","logger":"client-1:F:\\Asyncio-TCP-Server-Client-Example-test-task\\logs\\client_1.jsonl","event":"pong_received","client_id":1,"request_id":42,"latency_ms":428.2}
{"timestamp":"2026-05-30T12:00:03.000","level":"info","logger":"client-1:F:\\Asyncio-TCP-Server-Client-Example-test-task\\logs\\client_1.jsonl","event":"timeout","client_id":1,"request_id":43,"attempt":1}
```

## Metrics

Each client collects:

- sent `PING` count
- received `PONG` count
- timeout count
- retry count
- reconnect count
- success rate
- timeout rate
- average latency
- min latency
- max latency
- p95 latency

The demo script prints a merged summary when the run ends.

Example:

```text
Demo summary
------------
Clients: 5
Sent PING: 500
Received PONG: 445
Timeouts: 55
Retries: 38
Reconnects: 2
Success rate: 89.0%
Timeout rate: 11.0%
Average latency: 312 ms
Min latency: 101 ms
Max latency: 982 ms
P95 latency: 780 ms
```

## Tests

Run the automated checks with:

```bash
pytest
ruff check .
```

The test suite covers:

- protocol encode/decode
- server startup and responses
- keepalive delivery
- client ping, pong, timeout, and retry behavior
- metrics calculations

## Limitations

- This is an educational project, not a production-ready service
- The protocol is intentionally simple and only supports space-separated key/value pairs
- Message values cannot contain spaces
- There is no TLS, authentication, persistence, or backpressure management
- Metrics stay in memory for the current process only

## Possible Improvements

- add optional protocol versioning
- add richer error codes
- export metrics in a machine-readable file format
- add more reconnect and shutdown integration tests
- support configurable client run duration in standalone mode
