import asyncio
import unittest
from utils.sio_event_driver import SIOEventDriver, SubscribeToken, SIOEvent
from utils.sio_connector import SIOConnector

class TestSIOEventDriver(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connector = SIOConnector(debug=True)
        self.url = "https://bondage-club-server.herokuapp.com/"
        self.headers = {'Origin': 'https://www.bondage-europe.com'}
        await self.connector.connect(self.url, headers=self.headers)
        self.driver = SIOEventDriver(self.connector)

    async def asyncTearDown(self):
        self.driver.stop()
        await self.connector.disconnect()

    async def test_subscribe_and_push_event(self):
        # Subscribe to a test event
        token = await self.driver.subscribe(["*"])

        # Delay login request
        async def emit_event():
            await asyncio.sleep(3)
            await self.connector.emit("AccountLogin", {"AccountName": "vmaid", "Password": "******"})
        asyncio.create_task(emit_event())

        recv_event = await token.wait_event()
        self.assertTrue(len(recv_event) > 0, "no event received")
        self.assertEqual(recv_event[0].event_name, "LoginResponse")
        self.assertEqual(recv_event[0].data["AccountName"], "VMAID")

if __name__ == "__main__":
    unittest.main()
