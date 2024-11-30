import asyncio
from typing import Dict, Any, List
from asyncio import Queue, Event
from threading import Lock

from sio_connector import SIOConnector

class SubscribeToken:
    def __init__(self, events: List[str], dispatcher: 'SIOEventDriver'):
        self.events = events
        self.dispatcher = dispatcher
        self.event_data: Dict[str, Any] = {event: None for event in events}
        self.event_flags: Dict[str, Event] = {event: Event() for event in events}

    async def wait_event(self, event: str) -> Any:
        if event in self.event_flags:
            await self.event_flags[event].wait()  # Wait for the event to be triggered
            data = self.event_data[event]
            self.event_flags[event].clear()  # Clear the event flag
            return data
        else:
            raise ValueError(f"Event {event} not subscribed.")

class SIOEventDriver:
    def __init__(self, connector: 'SIOConnector'):
        self.connector = connector
        self.event_queues: Dict[str, Queue] = {}
        self.consumer_events: Dict[str, Event] = {}
        self.tokens: List[SubscribeToken] = []  # Used to store all SubscribeTokens
        self.tokens_lock = Lock()  # Lock to protect self.tokens
        self.stop_event = asyncio.Event()  # Event to stop the event loop
        self._setup_event_forwarding()

    def _setup_event_forwarding(self):
        # Set up forwarding for each event, except default events
        for event in self.connector.event_handlers:
            if event not in ['connect', 'disconnect', 'connect_error']:
                self.event_queues[event] = Queue()
                self.consumer_events[event] = Event()
                self.connector.register_handler(event, self._create_event_handler(event))

    def _create_event_handler(self, event: str):
        # Create an event handler to put data into the queue and set the event
        async def handler(data: Any):
            try:
                await self.event_queues[event].put(data)
                self.consumer_events[event].set()
            except Exception as e:
                print(f"Error handling event {event}: {e}")
        return handler

    def subscribe(self, events: List[str]) -> SubscribeToken:
        # Subscribe to multiple events and return a SubscribeToken object
        token = SubscribeToken(events, self)
        with self.tokens_lock:
            self.tokens.append(token)  # Add the newly created SubscribeToken to the list
        for event in events:
            if event not in self.event_queues:
                self.event_queues[event] = Queue()
                self.consumer_events[event] = Event()
                self.connector.register_handler(event, self._create_event_handler(event))
        return token

    async def start_event_loop(self):
        # Start an async task for each event to process its queue
        tasks = [self._event_loop(event, queue) for event, queue in self.event_queues.items()]
        await asyncio.gather(*tasks)

    async def _event_loop(self, event: str, queue: Queue):
        # Continuously process the queue for the given event
        while not self.stop_event.is_set():
            await self.consumer_events[event].wait()  # Wait for new data
            while not queue.empty():
                data = await queue.get()
                for token in self._get_tokens_for_event(event):
                    token.event_data[event] = data
                    token.event_flags[event].set()  # Set the event flag
            self.consumer_events[event].clear()  # Clear the event to block until new data arrives

    def _get_tokens_for_event(self, event: str) -> List[SubscribeToken]:
        # Get all SubscribeTokens that have subscribed to a specific event
        with self.tokens_lock:
            return [token for token in self.tokens if event in token.events]

    def _get_all_tokens(self) -> List[SubscribeToken]:
        with self.tokens_lock:
            return self.tokens  # Return all stored SubscribeTokens

    def stop(self):
        self.stop_event.set()
