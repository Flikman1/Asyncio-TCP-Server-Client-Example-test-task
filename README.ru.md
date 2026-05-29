# Async TCP Protocol Playground

## Описание

Это учебный проект по asyncio и TCP networking. Он показывает небольшой TCP-сервер и несколько TCP-клиентов, которые обмениваются строковыми сообщениями по простому протоколу `PING`/`PONG`.

Цель проекта — понятная демонстрация сетевого взаимодействия, а не production-архитектура. Здесь нет веб-фреймворков, базы данных, Redis, очередей и оркестрации. Основной фокус:

- `asyncio`
- TCP-сокеты
- несколько одновременных клиентов
- читаемый текстовый протокол
- keepalive
- timeout
- retry
- reconnect
- structured logging в формате JSONL
- базовые метрики
- автоматические тесты

## Возможности

- асинхронный TCP-сервер для нескольких клиентов
- асинхронные клиенты, отправляющие `PING` через случайные интервалы
- ответы `PONG` с тем же `request_id` и `client_id`
- настраиваемая вероятность игнорирования запросов для имитации потери ответа
- периодическая рассылка `KEEPALIVE` от сервера
- клиентские timeout, retry и reconnect
- JSONL-логи для сервера и клиентов
- summary-метрики после demo-режима
- тесты на `pytest` и `pytest-asyncio`

## Архитектура

Проект организован в компактный `src` layout:

- `protocol.py` отвечает за кодирование и декодирование сообщений
- `server.py` обрабатывает TCP-подключения и keepalive-рассылку
- `client.py` управляет отправкой `PING`, обработкой timeout, retry и reconnect
- `logging_config.py` пишет структурированные JSONL-события
- `metrics.py` собирает счётчики и статистику задержек
- `scripts/` содержит CLI-скрипты для demo, отдельного сервера и отдельного клиента

## Протокол сообщений

Протокол строковый и читаемый. Каждое сообщение заканчивается символом `\n`, поэтому и сервер, и клиенты могут использовать `reader.readline()`.

Поддерживаемые типы сообщений:

- `PING`
- `PONG`
- `KEEPALIVE`
- `ERROR`

Примеры:

```text
PING request_id=1 client_id=2
PONG request_id=1 client_id=2 server_time=2026-05-30T12:00:00.123
KEEPALIVE server_time=2026-05-30T12:00:05.000
ERROR message=invalid_request
```

Как это работает:

- клиент отправляет `PING` с уникальным `request_id`
- сервер обычно отвечает `PONG`
- иногда сервер специально пропускает ответ по `drop_rate`
- клиент ждёт `PONG` с соответствующим `request_id`
- если timeout истёк, клиент фиксирует timeout и может сделать retry
- если соединение потеряно, клиент делает reconnect
- сервер периодически отправляет `KEEPALIVE` всем подключённым клиентам

## Структура проекта

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

## Установка

```bash
pip install -e ".[dev]"
```

Нужен Python `3.10+`.

## Использование

### Запуск demo-режима

```bash
python scripts/run_demo.py --clients 5 --duration 60
```

### Запуск сервера

```bash
python scripts/run_server.py --host 127.0.0.1 --port 8888 --drop-rate 0.1 --keepalive-interval 5
```

### Запуск клиента

```bash
python scripts/run_client.py --client-id 1 --host 127.0.0.1 --port 8888
```

## Конфигурация

Параметры сервера:

- `host`
- `port`
- `keepalive_interval`
- `drop_rate`
- `min_response_delay`
- `max_response_delay`
- `log_path`

Параметры клиента:

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

Все CLI-скрипты построены на `argparse`.

## Логи

Логи пишутся в `logs/*.jsonl`. Каждая строка — отдельный JSON-объект.

Пример:

```json
{"timestamp":"2026-05-30T12:00:01.123","level":"info","logger":"client-1:F:\\Asyncio-TCP-Server-Client-Example-test-task\\logs\\client_1.jsonl","event":"ping_sent","client_id":1,"request_id":42,"attempt":1}
{"timestamp":"2026-05-30T12:00:01.551","level":"info","logger":"client-1:F:\\Asyncio-TCP-Server-Client-Example-test-task\\logs\\client_1.jsonl","event":"pong_received","client_id":1,"request_id":42,"latency_ms":428.2}
{"timestamp":"2026-05-30T12:00:03.000","level":"info","logger":"client-1:F:\\Asyncio-TCP-Server-Client-Example-test-task\\logs\\client_1.jsonl","event":"timeout","client_id":1,"request_id":43,"attempt":1}
```

## Метрики

Каждый клиент собирает:

- число отправленных `PING`
- число полученных `PONG`
- число timeout
- число retry
- число reconnect
- success rate
- timeout rate
- average latency
- min latency
- max latency
- p95 latency

После завершения demo-режима печатается общая summary-статистика.

Пример:

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

## Тесты

Запуск проверок:

```bash
pytest
ruff check .
```

Тесты покрывают:

- encode/decode протокола
- запуск сервера и ответы
- доставку keepalive
- отправку `PING`, получение `PONG`, timeout и retry у клиента
- расчёт метрик

## Ограничения

- это учебный проект, а не production-ready сервис
- протокол намеренно простой и поддерживает только пары `key=value`, разделённые пробелами
- значения полей не могут содержать пробелы
- здесь нет TLS, аутентификации, хранилища или сложного контроля backpressure
- метрики живут только в памяти процесса

## Возможные улучшения

- добавить версионирование протокола
- сделать более подробные коды ошибок
- экспортировать метрики в отдельный машиночитаемый формат
- расширить тесты на reconnect и shutdown
- добавить опциональную длительность работы для standalone-клиента
