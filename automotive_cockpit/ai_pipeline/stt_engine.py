"""
stt_engine.py — Vosk Speech-to-Text Engine
-------------------------------------------
Replaces faster-whisper with Vosk for much lighter, faster,
offline-capable speech recognition optimised for short car commands.

Vosk advantages over Whisper for this use case:
  - ~40MB model vs ~150MB for Whisper base.en
  - Near-instant transcription (no batch inference wait)
  - Designed for short, command-style utterances
  - Lower CPU load — keeps the AI thread free for SLM inference
  - No AVX2 / GPU requirements
"""

import sounddevice as sd
import numpy as np
import os
import json
import zipfile
import urllib.request
from vosk import Model, KaldiRecognizer, SetLogLevel

# Suppress Vosk's internal verbose logging
SetLogLevel(-1)

# ── Model config ──────────────────────────────────────────────────────────────
VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"
VOSK_MODEL_URL  = f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"
VOSK_MODEL_DIR  = os.path.join(os.path.expanduser("~"), ".cache", "vosk", VOSK_MODEL_NAME)
SAMPLE_RATE     = 16000   # Vosk expects 16kHz mono audio


class STTEngine:
    def __init__(self):
        self._ensure_model()
        print(f"Loading Vosk model from: {VOSK_MODEL_DIR}")
        self.model = Model(VOSK_MODEL_DIR)
        self.sample_rate = SAMPLE_RATE
        print("Vosk STT ready ✓")

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _ensure_model(self):
        """Download and extract the Vosk model if it isn't already cached."""
        if os.path.isdir(VOSK_MODEL_DIR):
            print(f"Vosk model found: {VOSK_MODEL_DIR}")
            return

        cache_dir = os.path.dirname(VOSK_MODEL_DIR)
        os.makedirs(cache_dir, exist_ok=True)
        zip_path = os.path.join(cache_dir, f"{VOSK_MODEL_NAME}.zip")

        print(f"Downloading Vosk model ({VOSK_MODEL_NAME}) ~40MB...")
        urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path)

        print("Extracting model...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(cache_dir)
        os.remove(zip_path)
        print(f"Vosk model ready at: {VOSK_MODEL_DIR}")

    # ── Recording ─────────────────────────────────────────────────────────────

    def record_audio(self, duration: int = 5) -> np.ndarray:
        """
        Record audio for `duration` seconds using the system default microphone.
        Returns a float32 numpy array at 16kHz mono.
        """
        print(f"Recording for {duration} seconds...")
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        return recording.flatten()

    # ── Transcription ─────────────────────────────────────────────────────────

    def _is_silent(self, audio: np.ndarray, threshold: float = 0.004) -> bool:
        """Return True when the recording contains only background noise."""
        rms = float(np.sqrt(np.mean(audio ** 2)))
        print(f"  Audio RMS: {rms:.4f}")
        return rms < threshold

    def transcribe(self, audio_data: np.ndarray = None) -> str:
        """
        Convert a numpy float32 audio array → transcribed text string.

        Vosk works on raw PCM int16 bytes. We:
          1. Optionally record fresh audio if none is provided.
          2. Silence-check to skip empty recordings immediately.
          3. Convert float32 → int16.
          4. Feed chunks to KaldiRecognizer and collect the final result.

        Returns an empty string on silence or unrecognisable input.
        """
        if audio_data is None:
            audio_data = self.record_audio()

        # Skip if silent
        if self._is_silent(audio_data):
            print("  Skipping transcription: silent audio.")
            return ""

        print("Transcribing with Vosk...")

        # Convert float32 → int16 PCM (Vosk's required format)
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val * 0.95   # normalise
        pcm_int16 = (audio_data * 32767).astype(np.int16)
        raw_bytes = pcm_int16.tobytes()

        # Create a fresh recognizer for each utterance
        rec = KaldiRecognizer(self.model, self.sample_rate)
        rec.SetWords(False)   # We only need the text, not word-level timing

        # Feed audio in chunks (512 samples at a time) — mimics real-time stream
        chunk_size = 512 * 2   # 512 int16 samples = 1024 bytes
        for i in range(0, len(raw_bytes), chunk_size):
            rec.AcceptWaveform(raw_bytes[i : i + chunk_size])

        # Get final result
        final_json  = json.loads(rec.FinalResult())
        text        = final_json.get("text", "").strip()

        print(f"Transcription: '{text}'")
        return text
