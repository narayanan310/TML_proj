from config.schemas import CANMessage
from core.state_manager import VehicleStateManager

class LightModule:
    def __init__(self, state_manager: VehicleStateManager):
        self.state_manager = state_manager

    async def handle_message(self, message: CANMessage):
        """Process Lighting related CAN messages."""
        # updater must be a plain (sync) function, not async
        def updater(state):
            if message.command == "turn_on_headlights":
                state.headlights_on = True
            elif message.command == "turn_off_headlights":
                state.headlights_on = False

        await self.state_manager.update_state(updater)
