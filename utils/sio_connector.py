import socketio
import asyncio
from typing import Callable, Dict, Any

class SIOConnector:
    def __init__(self, debug: bool = False):
        self.sio = socketio.AsyncClient(logger=debug, engineio_logger=debug)
        self.event_handlers: Dict[str, Callable] = {}
        self.debug = debug
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        @self.sio.event
        async def connect():
            print("Connected to server")
            
        @self.sio.event
        async def disconnect():
            print("Disconnected from server")
            
        @self.sio.event
        async def connect_error(data):
            print(f"Connection error: {data}")
    
    def register_handler(self, event: str, handler: Callable):
        self.event_handlers[event] = handler
        self.sio.on(event, handler)
        
    async def connect(self, url: str, **kwargs):
        try:
            await self.sio.connect(url, **kwargs)
        except Exception as e:
            print(f"Connection failed: {e}")
            
    async def disconnect(self):
        if self.sio.connected:
            await self.sio.disconnect()
            
    async def emit(self, event: str, data: Any = None, **kwargs):
        try:
            await self.sio.emit(event, data, **kwargs)
        except Exception as e:
            print(f"Failed to emit event: {e}")
            
    async def wait(self):
        await self.sio.wait()
