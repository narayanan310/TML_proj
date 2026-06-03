from config.schemas import CANMessage
from core.state_manager import VehicleStateManager

class ACModule:
    def __init__(self, state_manager: VehicleStateManager):
        self.state_manager = state_manager

    async def handle_message(self, message: CANMessage):
        """Process AC related CAN messages."""
        # updater must be a plain (sync) function, not async
        def updater(state):
            if message.command == "set_ac_temperature":
                try:
                    val = float(message.value)
                    state.ac_temperature = max(16.0, min(28.0, val))
                except (ValueError, TypeError):
                    pass
            elif message.command == "decrease_temperature":
                try:
                    val = float(message.value)
                    state.ac_temperature = max(16.0, state.ac_temperature - val)
                except (ValueError, TypeError):
                    pass
            elif message.command == "increase_temperature":
                try:
                    val = float(message.value)
                    state.ac_temperature = min(28.0, state.ac_temperature + val)
                except (ValueError, TypeError):
                    pass
            elif message.command == "turn_on_ac":
                state.ac_on = True
            elif message.command == "turn_off_ac":
                state.ac_on = False
            elif message.command == "set_fan_speed":
                try:
                    val = int(message.value)
                    state.fan_speed = max(0, min(6, val))
                except (ValueError, TypeError):
                    pass

        await self.state_manager.update_state(updater)
