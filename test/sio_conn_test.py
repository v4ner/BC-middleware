import asyncio
import unittest
import logging

from utils.sio_connector import SIOConnector

logging.basicConfig(level=logging.DEBUG)

class TestSIOConnector(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connector = SIOConnector(debug=True)
        self.url = "https://bondage-club-server.herokuapp.com/"
        self.headers = {'Origin': 'https://www.bondage-europe.com'}
        self.login_response_event = asyncio.Event()
        
        @self.connector.sio.event
        async def LoginResponse(data):
            print(f"LoginResponse received: {data}")
            self.login_response_event.set()
        
        print("Connecting to server")
        await self.connector.connect(self.url, headers=self.headers)

    async def asyncTearDown(self):
        await self.connector.disconnect()

    async def test_connect_and_emit(self):
        await self.connector.emit("AccountLogin", {"AccountName": "vmaid", "Password": "******"})
        await self.login_response_event.wait()
        self.assertTrue(self.login_response_event.is_set())

if __name__ == "__main__":
    unittest.main()
