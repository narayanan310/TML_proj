import asyncio
from typing import Callable, Awaitable, Dict, List, Optional
from config.schemas import CANMessage

# Type alias for subscribers: takes a CANMessage and returns nothing (awaitable)
SubscriberCallback = Callable[[CANMessage], Awaitable[None]]

class VirtualCANBus:
    def __init__(self):
        # Dictionary mapping CAN ID to a list of subscriber callbacks
        self._subscribers: Dict[str, List[SubscriberCallback]] = {}
        # Queue is created lazily inside the event loop in run()
        self._queue: Optional[asyncio.Queue] = None
        # Store reference to the running event loop for cross-thread publishing
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Logging callbacks (e.g., for the UI dashboard logger)
        self._log_callbacks: List[Callable[[str], None]] = []

    def subscribe(self, can_id: str, callback: SubscriberCallback):
        """Register a subscriber callback for a specific CAN ID."""
        if can_id not in self._subscribers:
            self._subscribers[can_id] = []
        self._subscribers[can_id].append(callback)

    def add_log_callback(self, callback: Callable[[str], None]):
        """Register a callback to receive all CAN bus logs."""
        self._log_callbacks.append(callback)

    def _log_message(self, message: CANMessage):
        """Format and dispatch a log entry."""
        log_str = f"[{message.id}] source: {message.source} -> {message.command}"
        if message.value is not None:
            log_str += f": {message.value}"
        
        for cb in self._log_callbacks:
            cb(log_str)

    def publish_threadsafe(self, message: CANMessage):
        """Thread-safe publish: can be called from any thread."""
        if self._loop and self._queue:
            asyncio.run_coroutine_threadsafe(self._queue.put(message), self._loop)
        else:
            print("CAN Bus not yet running; message dropped.")

    async def run(self):
        """Main loop: creates the queue here so it belongs to this event loop."""
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        print("Virtual CAN Bus started.")
        while True:
            message: CANMessage = await self._queue.get()
            self._log_message(message)
            
            if message.id in self._subscribers:
                for callback in self._subscribers[message.id]:
                    try:
                        await callback(message)
                    except Exception as e:
                        print(f"Error in subscriber for {message.id}: {e}")
            
            self._queue.task_done()
