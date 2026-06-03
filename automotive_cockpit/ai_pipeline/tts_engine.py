import pyttsx3
import threading

class TTSEngine:
    def __init__(self):
        # pyttsx3 needs to be initialized. Sometimes init on main thread and usage on worker fails,
        # but pyttsx3 is notorious for that. We can initialize inside the run method or locally.
        # To be safe across threads, we can use a worker thread for TTS.
        self._queue = []
        self._lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._worker_thread.start()

    def _tts_worker(self):
        # Initialize pyttsx3 inside the worker thread
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        
        while True:
            text = None
            with self._lock:
                if self._queue:
                    text = self._queue.pop(0)
            
            if text:
                engine.say(text)
                engine.runAndWait()
            else:
                import time
                time.sleep(0.1)

    def speak(self, text: str):
        """Queue text to be spoken asynchronously."""
        print(f"TTS Speaking: {text}")
        with self._lock:
            self._queue.append(text)
