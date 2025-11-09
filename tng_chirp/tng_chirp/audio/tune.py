import threading
import sounddevice as sd
import numpy as np
from typing import Optional

class ContinuousTune(threading.Thread):
    def __init__(self, freq: float, sr: int, device: Optional[int], stop_event: threading.Event,
                 log_q: "queue.Queue[str]", amplitude: float = 0.7):
        super().__init__(daemon=True)
        self.freq=freq; self.sr=sr; self.device=device; self.stop_event=stop_event; self.log_q=log_q
        self.amplitude=amplitude; self.phase=0.0; self.stream: Optional[sd.OutputStream]=None

    def _callback(self, outdata, frames, time_info, status):
        t = (np.arange(frames) + self.phase) / float(self.sr)
        out = (np.sin(2.0 * np.pi * self.freq * t) * self.amplitude).astype(np.float32)
        outdata[:, 0] = out
        self.phase = (self.phase + frames) % self.sr

    def run(self):
        try:
            self.stream = sd.OutputStream(samplerate=self.sr, channels=1, dtype='float32',
                                          callback=self._callback, device=self.device, latency='low')
            self.stream.start()
            while not self.stop_event.wait(0.05):
                pass
        except Exception as e:
            self.log_q.put(f"Tune error: {e}")
        finally:
            try:
                if self.stream:
                    self.stream.stop(); self.stream.close()
            except Exception:
                pass
