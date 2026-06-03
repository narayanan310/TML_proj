import threading
from typing import Callable, List
from config.schemas import VehicleState

class VehicleStateManager:
    def __init__(self):
        self.state = VehicleState()
        self._listeners: List[Callable[[VehicleState], None]] = []
        # Use a plain threading.Lock since state updates can come from any thread
        self._lock = threading.Lock()

    def add_listener(self, listener: Callable[[VehicleState], None]):
        """Register a callback to be notified of state changes."""
        self._listeners.append(listener)
        # Notify immediately with current state
        listener(self.state)

    async def update_state(self, updater: Callable[[VehicleState], None]):
        """Update the state safely and notify listeners. Called from async context."""
        with self._lock:
            updater(self.state)
            # Notify all listeners of the new state
            for listener in self._listeners:
                listener(self.state)

    def update_state_sync(self, updater: Callable[[VehicleState], None]):
        """Synchronous state update for use from non-async contexts."""
        with self._lock:
            updater(self.state)
            for listener in self._listeners:
                listener(self.state)

    def get_state(self) -> VehicleState:
        """Returns a copy of the current state."""
        return self.state.model_copy()
