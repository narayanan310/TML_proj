import sys
import os
import asyncio
import threading

# ── Ensure project root is on sys.path so all internal imports resolve ───────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication

from core.state_manager import VehicleStateManager
from core.can_bus import VirtualCANBus
from config.schemas import CANMessage

from modules.ac_module import ACModule
from modules.sunroof_module import SunroofModule
from modules.light_module import LightModule

from ui.dashboard import DashboardWindow
from ai_pipeline.context_mapper import match_contextual_phrase


# ── Shared SLM / TTS references (set once AI thread initialises them) ────────
_slm = None
_tts = None


def _resolve_intent(text: str) -> dict:
    """
    Two-stage intent resolution:
      1. Fast contextual phrase matcher (regex, no model)
      2. SLM fallback (llama.cpp)
    """
    # Stage 1: check contextual mapper first
    intent = match_contextual_phrase(text)
    if intent:
        print(f"[ContextMapper hit] {intent}")
        return intent

    # Stage 2: SLM inference
    if _slm:
        return _slm.extract_intent(text)

    return None


def _route_and_execute(intent_json: dict, can_bus: VirtualCANBus,
                       state_manager: VehicleStateManager, dashboard: DashboardWindow):
    """
    Given a parsed intent dict, maps it to a CAN ID, publishes to the bus,
    and triggers TTS feedback. Works from any thread.
    """
    if not (intent_json and "function" in intent_json):
        dashboard.signals.log_message.emit("Assistant: Could not parse intent.")
        if _tts:
            _tts.speak("Sorry, I didn't understand that.")
        return

    cmd = intent_json["function"]
    val = intent_json.get("value")

    dashboard.signals.log_message.emit(f"Assistant: Intent → {intent_json}")

    if cmd in ["set_ac_temperature", "decrease_temperature", "increase_temperature",
               "turn_on_ac", "turn_off_ac", "set_fan_speed"]:
        can_id = "0x101"
    elif cmd in ["open_sunroof", "close_sunroof", "open_window", "close_window"]:
        can_id = "0x102"
    elif cmd in ["turn_on_headlights", "turn_off_headlights"]:
        can_id = "0x103"
    else:
        can_id = "0x999"

    msg = CANMessage(id=can_id, source="voice_assistant", command=cmd, value=val)
    can_bus.publish_threadsafe(msg)

    if _tts:
        _tts.speak(f"Done. {cmd.replace('_', ' ')}")


def _process_text_command(text: str, can_bus: VirtualCANBus,
                          state_manager: VehicleStateManager, dashboard: DashboardWindow):
    """
    Called on a short-lived thread whenever the user submits a typed command.
    Tries context mapper first; falls back to SLM. Does NOT go through STT.
    """
    state_manager.update_state_sync(lambda s: setattr(s, "assistant_status", "Processing"))
    intent_json = _resolve_intent(text)
    _route_and_execute(intent_json, can_bus, state_manager, dashboard)
    state_manager.update_state_sync(lambda s: setattr(s, "assistant_status", "Idle"))


def run_ai_pipeline(state_manager: VehicleStateManager, can_bus: VirtualCANBus,
                    dashboard: DashboardWindow):
    """
    Worker thread: loads AI subsystems, then runs the voice interaction loop.
    Text commands bypass this loop entirely and go via _process_text_command().
    """
    global _slm, _tts

    dashboard.signals.log_message.emit("System: Loading AI subsystems (Whisper + LLaMA)...")

    from ai_pipeline.wake_word import WakeWordDetector
    from ai_pipeline.stt_engine import STTEngine
    from ai_pipeline.slm_inference import SLMInferenceEngine
    from ai_pipeline.tts_engine import TTSEngine

    wake_word = WakeWordDetector(threshold=0.05)
    stt = STTEngine()   # Vosk — auto-loads from ~/.cache/vosk/
    _slm = SLMInferenceEngine()
    _tts = TTSEngine()

    dashboard.signals.log_message.emit(
        "System: AI Ready ✓  |  Make a sound/clap to trigger voice, or type in the text box below."
    )

    def update_status(s):
        state_manager.update_state_sync(lambda st: setattr(st, "assistant_status", s))

    update_status("Idle")

    # ── Voice interaction loop ────────────────────────────────────────────
    while True:
        try:
            # 1. Wait for audio trigger
            wake_word.wait_for_wake_word()

            # 2. Record + transcribe
            update_status("Listening")
            dashboard.signals.log_message.emit("VoiceAssistant: Listening...")
            audio_data = stt.record_audio(duration=5)

            update_status("Processing")
            dashboard.signals.log_message.emit("VoiceAssistant: Transcribing...")
            transcript = stt.transcribe(audio_data)

            if not transcript:
                dashboard.signals.log_message.emit(
                    "VoiceAssistant: Silence detected — tip: use text box if mic is unclear."
                )
                update_status("Idle")
                continue

            dashboard.signals.log_message.emit(f"VoiceAssistant: Heard → \"{transcript}\"")

            # 3. Context mapper → SLM (fallback) → CAN → State → UI
            intent_json = _resolve_intent(transcript)
            _route_and_execute(intent_json, can_bus, state_manager, dashboard)

            update_status("Speaking")

        except Exception as e:
            print(f"[AI Pipeline Error]: {e}")
            dashboard.signals.log_message.emit(f"[Error]: {e}")

        update_status("Idle")


def start_can_bus_loop(loop: asyncio.AbstractEventLoop, can_bus: VirtualCANBus):
    """Run the CAN bus asyncio event loop on its dedicated thread."""
    asyncio.set_event_loop(loop)
    loop.run_until_complete(can_bus.run())


def main():
    # 1. Qt Application — must be on the main thread
    app = QApplication(sys.argv)

    # 2. Core components
    state_manager = VehicleStateManager()
    can_bus = VirtualCANBus()

    # 3. Dashboard
    dashboard = DashboardWindow()

    # Wire state → UI (thread-safe pyqtSignal)
    state_manager.add_listener(lambda s: dashboard.signals.state_updated.emit(s))
    # Wire CAN bus log → UI logger
    can_bus.add_log_callback(lambda msg: dashboard.signals.log_message.emit(msg))

    # ── Text command: short-lived thread for SLM, non-blocking ───────────────
    dashboard.signals.text_command_submitted.connect(
        lambda text: threading.Thread(
            target=_process_text_command,
            args=(text, can_bus, state_manager, dashboard),
            daemon=True
        ).start()
    )

    # ── Slider command: direct CAN publish, no SLM needed ─────────────────
    def _on_slider_command(cmd: str, value: int):
        can_id = "0x102"   # sunroof/window module
        msg = CANMessage(id=can_id, source="slider", command=cmd, value=value)
        can_bus.publish_threadsafe(msg)

    dashboard.signals.slider_command.connect(_on_slider_command)

    # 4. Vehicle subsystem modules
    ac_module = ACModule(state_manager)
    sunroof_module = SunroofModule(state_manager)
    light_module = LightModule(state_manager)

    can_bus.subscribe("0x101", ac_module.handle_message)
    can_bus.subscribe("0x102", sunroof_module.handle_message)
    can_bus.subscribe("0x103", light_module.handle_message)

    # 5. CAN bus thread (own asyncio loop)
    can_loop = asyncio.new_event_loop()
    can_thread = threading.Thread(
        target=start_can_bus_loop, args=(can_loop, can_bus),
        daemon=True, name="CANBusThread"
    )
    can_thread.start()

    # 6. AI voice pipeline thread
    ai_thread = threading.Thread(
        target=run_ai_pipeline, args=(state_manager, can_bus, dashboard),
        daemon=True, name="AIThread"
    )
    ai_thread.start()

    # 7. Launch UI (blocks until window closed)
    dashboard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
