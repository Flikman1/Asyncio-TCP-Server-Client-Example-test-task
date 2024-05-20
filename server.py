import asyncio
import random
import datetime


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_counter = 0
        self.response_counter = 0
        self.log_file = "server_log.txt"

    async def handle_client(self, reader, writer):
        client_id = self.client_counter
        self.client_counter += 1
        print(f"Client {client_id} connected.")

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                message = data.decode().strip()
                current_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
                log_entry = f"{datetime.datetime.now().strftime('%Y-%m-%d')};{current_time};{message};"

                if random.random() < 0.1:
                    log_entry += "(проигнорировано)"
                    self.log(log_entry)
                    continue

                await asyncio.sleep(random.randint(100, 1000) / 1000.0)
                response_message = f"[{self.response_counter}/{message.split()[0][1:-1]}] PONG ({client_id + 1})"
                self.response_counter += 1
                writer.write((response_message + "\n").encode())
                await writer.drain()

                current_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
                log_entry += f"{current_time};{response_message}"
                self.log(log_entry)
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"Client {client_id} disconnected.")

    def log(self, entry):
        with open(self.log_file, "a") as f:
            f.write(entry + "\n")

    async def keepalive(self):
        while True:
            await asyncio.sleep(5)
            keepalive_message = f"[{self.response_counter}] keepalive"
            self.response_counter += 1
            self.broadcast(keepalive_message)

    def broadcast(self, message):
        for client_writer in self.clients:
            client_writer.write((message + "\n").encode())

    async def start_server(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        async with server:
            await asyncio.gather(server.serve_forever(), self.keepalive())


if __name__ == "__main__":
    server = Server("127.0.0.1", 8888)
    asyncio.run(server.start_server())
