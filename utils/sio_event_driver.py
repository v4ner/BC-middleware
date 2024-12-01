import asyncio
from typing import Any, List
from asyncio import Event, Lock
from queue import Queue
from threading import Thread

from utils.sio_connector import SIOConnector

class SIOEvent:
    def __init__(self, event_name: str, data: Any):
        self.event_name = event_name
        self.data = data

class SubscribeToken:
    def __init__(self, events: List[str], dispatcher: 'SIOEventDriver'):
        self.events = events
        self.dispatcher = dispatcher
        self.event_queue: Queue = Queue()
        self.event_flag: Event = Event()

    async def wait_event(self) -> List[SIOEvent]:
        await self.event_flag.wait()
        data_list = []
        while not self.event_queue.empty():
            data_list.append(self.event_queue.get())
        self.event_flag.clear()
        return data_list

    def push_event(self, event: SIOEvent):
        self.event_queue.put(event)
        self.event_flag.set()

    def unsubscribe(self):
        self.dispatcher.unsubscribe(self)

class SIOEventDriver:
    def __init__(self, connector: 'SIOConnector'):
        self.connector = connector
        self.tokens: List[SubscribeToken] = []
        self.tokens_lock = Lock()
        self._stop_event = Event()
        self._setup_event_forwarding()
        self._start_daemon_loop()

    def _setup_event_forwarding(self):
        self.connector.register_handler('*', self._create_event_handler('*'))

    def _create_event_handler(self, event: str):
        async def handler(event_name: str, data: Any):
            try:
                sio_event = SIOEvent(event_name, data)
                for token in await self._get_tokens_for_event(event_name):
                    token.push_event(sio_event)
            except Exception as e:
                print(f"Error handling event {event_name}: {e}")
        return handler

    async def subscribe(self, events: List[str]) -> SubscribeToken:        
        token = SubscribeToken(events, self)
        async with self.tokens_lock:
            self.tokens.append(token)
        return token
    
    async def subscribe_all(self) -> SubscribeToken:
        return await self.subscribe(["*"])

    async def unsubscribe(self, token: SubscribeToken):
        async with self.tokens_lock:
            if token in self.tokens:
                self.tokens.remove(token)

    async def _get_tokens_for_event(self, event: str) -> List[SubscribeToken]:
        async with self.tokens_lock:
            return [token for token in self.tokens if event in token.events or "*" in token.events]

    async def _get_all_tokens(self) -> List[SubscribeToken]:
        async with self.tokens_lock:
            return self.tokens

    def _start_daemon_loop(self):
        ''' Prevent thread contention on event_flag, which may delay consumption '''
        async def daemon_loop():
            while not self._stop_event.is_set():
                ''' No lock, just wait next round '''
                for token in self.tokens:
                    if not token.event_queue.empty() and not token.event_flag.is_set():
                        token.event_flag.set()
                await asyncio.sleep(0.1)
        loop = asyncio.get_event_loop()
        loop.create_task(daemon_loop())

    def stop(self):
        self._stop_event.set()
