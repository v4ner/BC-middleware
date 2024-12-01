import asyncio
from utils.sio_connector import SIOConnector
from utils.sio_event_driver import SIOEventDriver, SIOEvent

class InteractiveDebugger:
    def __init__(self, url, headers = None):
        self.connector = SIOConnector(debug=True)
        self.driver = SIOEventDriver(self.connector)
        self.url = url
        self.headers = headers or {}
        self.token = None

    async def connect(self):
        await self.connector.connect(self.url, headers=self.headers)
        self.token = await self.driver.subscribe(["*"])
        asyncio.create_task(self._listen_for_events())

    async def _listen_for_events(self):
        while True:
            events = await self.token.wait_event()
            for event in events:
                print(f"Received event: {event.event_name}, data: {event.data}")

    async def send_message(self, event_name, data):
        await self.connector.emit(event_name, data)

    async def disconnect(self):
        await self.connector.disconnect()
        self.driver.stop()

# Example usage
async def main():
    client = InteractiveDebugger(
        url="https://bondage-club-server.herokuapp.com/",
        headers={'Origin': 'https://www.bondage-europe.com'}
    )
    await client.connect()
    await client.send_message("AccountLogin", {"AccountName": "vmaid", "Password": "******"})
    await asyncio.sleep(60)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
