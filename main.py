import asyncio
import multiprocessing
import time

from server import Server
from client import Client


def start_server():
    server = Server("127.0.0.1", 8888)
    asyncio.run(server.start_server())


def start_client(client_id):
    client = Client("127.0.0.1", 8888, client_id)
    asyncio.run(client.run())


if __name__ == "__main__":
    server_process = multiprocessing.Process(target=start_server)
    client_processes = [multiprocessing.Process(target=start_client, args=(i,)) for i in range(2)]

    server_process.start()
    for p in client_processes:
        p.start()

    time.sleep(300)  # Запуск на 5 минут

    server_process.terminate()
    for p in client_processes:
        p.terminate()

    server_process.join()
    for p in client_processes:
        p.join()

