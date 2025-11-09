import sounddevice as sd
import threading, queue
import numpy as np
from typing import Optional, Callable

class InputMonitor:
    """
    Simple audio input monitor:
      - Opens an InputStream
      - Callback pushes captured mono float32 samples to a queue
    """
    def __init__(self, sr: int, device: Optional[int], blocksize: int, sample_queue: "queue.Queue[np.ndarray]", log_q: "queue.Queue[str]"):
        self.sr = sr
        self.device = device
        self.blocksize = blocksize
        self.sample_queue = sample_queue
        self.log_q = log_q
        self.stream: Optional[sd.InputStream] = None
        self.active = False

    def _callback(self, indata, frames, time_info, status):
        if status:
            try:
                self.log_q.put(f"Input status: {status}")
            except Exception:
                pass
        try:
            # Take first channel only (mono)
            chunk = np.copy(indata[:, 0]).astype(np.float32)
            self.sample_queue.put(chunk)
        except Exception:
            pass

    def start(self):
        if self.active:
            return
        try:
            self.stream = sd.InputStream(samplerate=self.sr,
                                         channels=1,
                                         dtype='float32',
                                         blocksize=self.blocksize,
                                         callback=self._callback,
                                         device=self.device)
            self.stream.start()
            self.active = True
            self.log_q.put("Monitor started")
        except Exception as e:
            self.log_q.put(f"Monitor start failed: {e}")
            self.active = False
            self.stream = None

    def stop(self):
        if not self.active:
            return
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass
        self.stream = None
        self.active = False
        self.log_q.put("Monitor stopped")
