import sounddevice as sd
import numpy as np
import time

class WakeWordDetector:
    def __init__(self, threshold: float = 0.05, rate: int = 16000):
        self.threshold = threshold
        self.rate = rate
        self.is_listening = False

    def wait_for_wake_word(self) -> bool:
        """
        Blocks until the audio energy exceeds the threshold.
        Acts as a simple fallback wake-word detector.
        """
        print("Waiting for wake word (or loud noise)...")
        detected = False
        
        def audio_callback(indata, frames, time_info, status):
            nonlocal detected
            if status:
                print(status)
            # Calculate RMS energy
            rms = np.sqrt(np.mean(indata**2))
            if rms > self.threshold:
                detected = True

        with sd.InputStream(samplerate=self.rate, channels=1, callback=audio_callback):
            while not detected:
                time.sleep(0.1)
                
        print("Wake word detected!")
        return True
