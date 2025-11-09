import threading, queue
import sounddevice as sd
import numpy as np
from typing import Optional, Callable

class PlaybackWorker(threading.Thread):
    def __init__(self, samples: np.ndarray, sr: int, device: Optional[int], log_q: "queue.Queue[str]",
                 on_start: Optional[Callable]=None, on_done: Optional[Callable]=None):
        super().__init__(daemon=True)
        self.samples = samples; self.sr = sr; self.device = device
        self.log_q = log_q; self.on_start = on_start; self.on_done = on_done

    def stop(self) -> None:
        try: sd.stop()
        except Exception: pass

    def run(self) -> None:
        try:
            if self.on_start:
                try: self.on_start()
                except Exception: pass
            sd.play(self.samples, self.sr, device=self.device)
            sd.wait()
        except Exception as e:
            self.log_q.put(f"Playback error: {e}")
        finally:
            if self.on_done:
                try: self.on_done()
                except Exception: pass
