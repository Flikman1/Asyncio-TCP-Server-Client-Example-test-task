import asyncio
import random
import datetime

class Client:
    def __init__(self, host, port, client_id):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.log_file = f"client_{client_id}_log.txt"
        self.request_counter = 0

    async def send_ping(self, writer):
        while True:
            await asyncio.sleep(random.randint(300, 3000) / 1000.0)
            message = f"[{self.request_counter}] PING"
            self.request_counter += 1
            current_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self.log(f"{datetime.datetime.now().strftime('%Y-%m-%d')};{current_time};{message};", False)
            writer.write((message + "\n").encode())
            await writer.drain()

    async def receive_pong(self, reader):
        while True:
            data = await reader.readline()
            if not data:
                break

            message = data.decode().strip()
            current_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            if message.endswith("keepalive"):
                self.log(f"{datetime.datetime.now().strftime('%Y-%m-%d')};;{current_time};{message}", False)
            else:
                self.log(f";;{current_time};{message}", False)

    async def run(self):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        await asyncio.gather(self.send_ping(writer), self.receive_pong(reader))

    def log(self, entry, add_date=True):
        with open(self.log_file, "a") as f:
            if add_date:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d')};{entry}\n")
            else:
                f.write(f"{entry}\n")

if __name__ == "__main__":
    clients = [Client("127.0.0.1", 8888, i) for i in range(2)]
    asyncio.run(asyncio.gather(*[client.run() for client in clients]))
