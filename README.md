# Automotive Edge AI Cockpit Simulation

A complete, offline, local software simulation of a Software-Defined Vehicle (SDV) cockpit. The system allows you to interact with simulated vehicle hardware (AC, Sunroof, Headlights) using natural language voice commands, typed text commands, or manual UI sliders. 

Everything runs locally on your machine—no internet connection required.

---

## 🌟 Key Features

1. **Local Voice Assistant**: Instant offline speech-to-text powered by **Vosk**. Just speak commands like *"Turn on the AC"* or *"I'm feeling hot"*.
2. **Context-Aware AI Intelligence**: 
   - Uses a custom **Context Mapper** to instantly translate colloquial phrases (*"I want fresh air"*, *"It's freezing"*) into car functions.
   - Falls back to a localized **Llama 3.2 1B Small Language Model (SLM)** running on CPU to handle complex or explicit commands, constrained strictly to JSON using GBNF grammar to completely eliminate AI hallucinations.
3. **Simulated CAN Bus Architecture**: Commands aren't just magically updating UI labels. The AI translates text to structured JSON intents, routes them over an asynchronous **Virtual CAN Bus**, which is then picked up by isolated hardware modules (AC Module, Sunroof Module).
4. **Real-time Dashboard (PyQt6)**: A modern, threaded GUI that visually represents the vehicle's state in real time, featuring interactive sliders for windows and sunroof.
5. **Multi-Threaded Performance**: The UI, the Async CAN bus, and the AI Speech-to-Text inference all run on completely separate threads for a stutter-free experience.

---

## 🛠 Tech Stack

* **Language:** Python 3.12+
* **GUI Framework:** PyQt6
* **Speech-to-Text (STT):** Vosk (`vosk-model-small-en-us`)
* **Text-to-Speech (TTS):** pyttsx3 (System Native Voice)
* **Small Language Model (SLM):** Meta LLaMA 3.2 1B Instruct (GGUF via `llama-cpp-python`)
* **State & Validation:** Pydantic
* **Concurrency:** `threading` and `asyncio`

---

## 📁 File Structure & Architecture

```text
.
├── README.md                  # Project documentation
├── .gitignore                 # Excludes virtual environments and temp files
└── automotive_cockpit/        # Main application folder
    ├── main.py                # Application entry point. Wires threads, GUI, CAN bus, and AI together.
    ├── requirements.txt       # Python dependencies
    ├── ai_pipeline/           # 🧠 The Brain: Handles all NLP and Audio processing
    │   ├── context_mapper.py  # Fast regex mapper for colloquial phrases (e.g., "I'm hot")
    │   ├── slm_inference.py   # Llama 3.2 Engine forced to output JSON via GBNF grammar
    │   ├── stt_engine.py      # Vosk Speech-to-Text engine
    │   ├── tts_engine.py      # pyttsx3 Text-to-Speech engine
    │   └── wake_word.py       # Detects loud sounds to trigger the microphone
    ├── config/
    │   └── schemas.py         # Pydantic data schemas for CAN messages and Vehicle State
    ├── core/                  # ⚙️ The Nervous System
    │   ├── can_bus.py         # Async event loop acting as a virtual CAN network
    │   └── state_manager.py   # Thread-safe global state store for the vehicle
    ├── modules/               # 🔩 The Simulated Hardware
    │   ├── ac_module.py       # Listens to CAN bus for AC commands
    │   ├── light_module.py    # Listens to CAN bus for Light commands
    │   └── sunroof_module.py  # Listens to CAN bus for Sunroof/Window commands
    └── ui/
        └── dashboard.py       # PyQt6 User Interface with real-time updates and manual overrides
```

---

## 🚀 How to Run

1. **Activate the Virtual Environment:**
   ```bash
   source automotive_cockpit/.venv/bin/activate
   ```
2. **Install Requirements** (if you haven't already):
   ```bash
   pip install -r automotive_cockpit/requirements.txt
   ```
3. **Launch the Application:**
   ```bash
   cd automotive_cockpit
   python main.py
   ```

*(Note: On the first launch, the script will automatically download the 40MB Vosk model and the ~800MB Llama 3.2 model to your HuggingFace/Vosk cache directories).*

---

## 🗣️ Supported Commands Example

You can trigger the assistant by clapping your hands loudly (or making a sharp sound), or by using the text box at the bottom of the dashboard.

**Direct Commands:**
- *"Set AC to 22 degrees"*
- *"Open sunroof to 75 percent"*
- *"Turn on headlights"*
- *"Fan speed maximum"*

**Natural Contextual Phrases:**
- *"I'm freezing"* (Increases temp by 2°C)
- *"I'm sweating"* (Decreases temp by 2°C)
- *"I want some fresh air"* (Opens sunroof to 50%)
- *"It's starting to rain"* (Closes sunroof)
- *"It's getting dark outside"* (Turns on headlights)
