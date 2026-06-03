from pydantic import BaseModel, Field
from typing import Any, Optional

class VehicleState(BaseModel):
    ac_on: bool = True
    ac_temperature: float = Field(22.0, ge=16.0, le=28.0)
    fan_speed: int = Field(3, ge=0, le=6)
    sunroof_position: int = Field(0, ge=0, le=100) # 0 = Fully Closed, 100 = Fully Open
    window_position: int = Field(0, ge=0, le=100)
    headlights_on: bool = False
    assistant_status: str = "Idle" # Idle, Listening, Processing, Speaking

class CANMessage(BaseModel):
    id: str = Field(..., description="Hexadecimal identifier, e.g., '0x101'")
    source: str = Field(..., description="Origin module, e.g., 'voice_assistant'")
    command: str = Field(..., description="Action string, e.g., 'SET_AC_TEMPERATURE'")
    value: Optional[Any] = None
