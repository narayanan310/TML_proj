from config.schemas import CANMessage
from core.state_manager import VehicleStateManager

class SunroofModule:
    def __init__(self, state_manager: VehicleStateManager):
        self.state_manager = state_manager

    async def handle_message(self, message: CANMessage):
        """Process Sunroof and Window related CAN messages."""
        # updater must be a plain (sync) function, not async
        def updater(state):
            if message.command == "open_sunroof":
                try:
                    val = int(message.value)
                    state.sunroof_position = max(0, min(100, val))
                except (ValueError, TypeError):
                    pass
            elif message.command == "close_sunroof":
                state.sunroof_position = 0
            elif message.command == "open_window":
                try:
                    val = int(message.value)
                    state.window_position = max(0, min(100, val))
                except (ValueError, TypeError):
                    pass
            elif message.command == "close_window":
                state.window_position = 0

        await self.state_manager.update_state(updater)
