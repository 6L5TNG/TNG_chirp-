import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time, queue, threading, os
import numpy as np

from tng_chirp.core.version import VERSION
from tng_chirp.core.settings import load_settings, save_settings
from tng_chirp.core.i18n import Translator
from tng_chirp.core.presets import DEFAULT_PRESETS

from tng_chirp.dsp.synth import text_to_wave
from tng_chirp.dsp.marker import build_marker_sequence
from tng_chirp.dsp.signature import build_signature_sequence
from tng_chirp.dsp.beeps import parse_beep_spec_ms, build_beeps_sequence

from tng_chirp.audio.playback import PlaybackWorker
from tng_chirp.audio.tune import ContinuousTune
from tng_chirp.audio.monitor import InputMonitor

from tng_chirp.ui.settings_dialog import SettingsDialog

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

# Action button colors (fixed)
BTN_BG="#E8E8E8"; BTN_FG="#202020"; BTN_ACTIVE_BG="#D5D5D5"
TX_ACTIVE_BG="#B00020"; TX_ACTIVE_FG="#FFFFFF"
TUNE_ACTIVE_BG="#B00020"; TUNE_ACTIVE_FG="#FFFFFF"
MON_ON_BG="#32C852"; MON_ON_FG="#FFFFFF"
MON_OFF_BG=BTN_BG; MON_OFF_FG=BTN_FG
HOVER_DARKEN="#CFCFCF"

class ChirpApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"TNG_Chirp {VERSION}")
        self.geometry("1400x880")
        self.minsize(1200,780)

        self.settings = load_settings()
        self.trans = Translator(self.settings.get("language","ko"))

        self.log_q: "queue.Queue[str]" = queue.Queue()

        self.play_worker=None
        self.tune_thread=None
        self.tune_stop_event=None
        self.test_tune_active=False

        self.monitor=None
        self.monitor_queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self.monitor_enabled=True
        self._last_rx_chunk=np.zeros(0,dtype=np.float32)

        self.tx_samples=None
        self.tx_sr=48000
        self.tx_index=0
        self.tx_active_flag=False
        self.tx_chunk_len=0.25
        self.tx_total_samples=0

        self.wf_freqs=None
        self.wf_data=None
        self.wf_img=None
        self.wf_lock=threading.Lock()

        self.rx_level_var=tk.IntVar(value=0)
        self.tx_level_var=tk.IntVar(value=0)
        self._tune_blink=False

        self.report_callback_exception=self._tk_exception_handler

        self._build_menu()
        self._build_layout()
        self.apply_settings(self.settings)
        self._start_monitor_stream()

        self.after(120,self._poll_log_queue)
        self.after(300,self._monitor_update_loop)
        self.after(400,self._update_rx_gauge)
        self.after(500,self._update_tx_gauge)
        self.after(260,self._update_leds)

    # ------------- i18n -------------
    def t(self,k,d): return self.trans.tr(k,d)

    # ------------- Error handler -------------
    def _tk_exception_handler(self,exc,val,tb):
        self.log(f"ERROR: {val}")
        try: messagebox.showerror("Error", self.t("error.unexpected","Unexpected error. See log."))
        except Exception: pass

    # ------------- Menu (File + Help only) -------------
    def _build_menu(self):
        m=tk.Menu(self)

        filem=tk.Menu(m, tearoff=0)
        filem.add_command(label=self.t("menu.settings.dialog","Settings..."), command=lambda: SettingsDialog(self,self.settings))
        filem.add_separator()
        filem.add_command(label=self.t("menu.exit","Exit"), command=self.quit)
        m.add_cascade(label=self.t("menu.file","File"), menu=filem)

        helpm=tk.Menu(m, tearoff=0)
        helpm.add_command(label=self.t("menu.about","About"), command=self._show_about)
        m.add_cascade(label=self.t("menu.help","Help"), menu=helpm)

        self.config(menu=m)
        self.menubar=m

    def update_menu_language(self):
        self.trans=Translator(self.settings.get("language","ko"))
        self._build_menu()
        self.callsign_disp.set(f"{self.t('general.callsign','Callsign')}: {self.settings.get('callsign','') or '(none)'}")
        self.grid_disp.set(f"{self.t('general.grid','Grid')}: {self.settings.get('grid','') or '(none)'}")

    def _show_about(self):
        messagebox.showinfo(self.t("menu.about","About"),
                            f"TNG_Chirp {VERSION}\nCallsign: {self.settings.get('callsign','')}\nGrid: {self.settings.get('grid','')}")

    # ------------- Layout -------------
    def _build_layout(self):
        header=ttk.Frame(self)
        header.pack(fill=tk.X,padx=10,pady=6)

        self.callsign_disp=tk.StringVar(value=f"Callsign: {self.settings.get('callsign','') or '(none)'}")
        ttk.Label(header,textvariable=self.callsign_disp).pack(side=tk.LEFT,padx=(4,16))
        self.grid_disp=tk.StringVar(value=f"Grid: {self.settings.get('grid','') or '(none)'}")
        ttk.Label(header,textvariable=self.grid_disp).pack(side=tk.LEFT,padx=(0,16))

        ttk.Separator(header,orient=tk.VERTICAL).pack(side=tk.LEFT,fill=tk.Y,padx=12)
        ttk.Label(header,text="Speed:").pack(side=tk.LEFT,padx=(4,2))
        self.speed_var=tk.StringVar(value=self.settings.get("default_preset","Normal"))
        for p in ["Slow","Normal","Fast","VeryFast"]:
            ttk.Radiobutton(header,text=p,value=p,variable=self.speed_var,command=self._on_speed_changed)\
                .pack(side=tk.LEFT,padx=3)

        # Action buttons cluster
        act=ttk.Frame(header); act.pack(side=tk.RIGHT,padx=10)
        self.tx_button=tk.Button(act,text="Transmit TX",width=12,command=self.start_tx)
        self._style_button(self.tx_button); self.tx_button.pack(side=tk.LEFT,padx=3)
        self.tune_button=tk.Button(act,text="Tune",width=8,command=self.toggle_tune)
        self._style_button(self.tune_button); self.tune_button.pack(side=tk.LEFT,padx=3)
        self.stop_button=tk.Button(act,text="Halt TX",width=10,state=tk.DISABLED,command=self.stop_tx)
        self._style_button(self.stop_button); self.stop_button.pack(side=tk.LEFT,padx=3)
        self.save_button=tk.Button(act,text="Save WAV...",width=12,command=self.save_wav_dialog)
        self._style_button(self.save_button); self.save_button.pack(side=tk.LEFT,padx=3)
        self.decode_button=tk.Button(act,text="Decode",width=8,command=self._decode_stub)
        self._style_button(self.decode_button); self.decode_button.pack(side=tk.LEFT,padx=3)
        self.monitor_button=tk.Button(act,text="Monitor",width=10,command=self._toggle_monitor)
        self._style_button(self.monitor_button); self.monitor_button.pack(side=tk.LEFT,padx=3)

        # LEDs
        led_holder=ttk.Frame(header); led_holder.pack(side=tk.RIGHT,padx=10)
        self.tx_led_canvas=tk.Canvas(led_holder,width=20,height=20,highlightthickness=0,bg=self.cget("bg"))
        self.tx_led_canvas.pack(side=tk.LEFT,padx=6)
        self.tx_led_id=self.tx_led_canvas.create_oval(2,2,18,18,fill="#333333",outline="#111111")
        self.rx_led_canvas=tk.Canvas(led_holder,width=20,height=20,highlightthickness=0,bg=self.cget("bg"))
        self.rx_led_canvas.pack(side=tk.LEFT,padx=6)
        self.rx_led_id=self.rx_led_canvas.create_oval(2,2,18,18,fill="#333333",outline="#111111")

        # Panes
        body=ttk.PanedWindow(self,orient=tk.HORIZONTAL); body.pack(fill=tk.BOTH,expand=True,padx=10,pady=(0,6))
        left=ttk.PanedWindow(body,orient=tk.VERTICAL); body.add(left,weight=0)
        right=ttk.Frame(body); body.add(right,weight=1)

        # Transmit message
        msg_frame=ttk.LabelFrame(left,text="Transmit Message")
        left.add(msg_frame,weight=1)
        self.text_widget=tk.Text(msg_frame,width=54,height=12,wrap="word")
        self.text_widget.pack(fill=tk.BOTH,expand=True,padx=6,pady=6)
        self.text_widget.insert("1.0","CQ CQ TEST")

        # Transmit Controls (NO speed sliders here)
        ctrl=ttk.LabelFrame(left,text="Transmit Controls")
        left.add(ctrl,weight=0)
        ttk.Label(ctrl,text="Amplitude:").grid(row=0,column=0,sticky="w",padx=6,pady=4)
        self.amp_var=tk.DoubleVar(value=self.settings.get("amp",0.8))
        ttk.Scale(ctrl,from_=0.1,to=1.0,orient=tk.HORIZONTAL,variable=self.amp_var)\
            .grid(row=0,column=1,columnspan=3,sticky="we",padx=6,pady=4)

        ttk.Label(ctrl,text="Beep amp:").grid(row=1,column=0,sticky="w",padx=6,pady=4)
        self.beep_amp_var=tk.DoubleVar(value=self.settings.get("beep_amp",0.7))
        ttk.Scale(ctrl,from_=0.1,to=1.0,orient=tk.HORIZONTAL,variable=self.beep_amp_var)\
            .grid(row=1,column=1,columnspan=3,sticky="we",padx=6,pady=4)

        ttk.Label(ctrl,text="Direction:").grid(row=2,column=0,sticky="w",padx=6,pady=4)
        self.dir_var=tk.StringVar(value="up")
        ttk.Combobox(ctrl,state="readonly",values=["up","down"],width=9,textvariable=self.dir_var)\
            .grid(row=2,column=1,sticky="w",padx=6,pady=4)
        ttk.Label(ctrl,text="Preamble:").grid(row=2,column=2,sticky="e",padx=6,pady=4)
        self.preamble_var=tk.IntVar(value=0)
        ttk.Spinbox(ctrl,from_=0,to=20,width=6,textvariable=self.preamble_var)\
            .grid(row=2,column=3,sticky="w",padx=6,pady=4)

        # Decoded RX
        rx_dec_frame=ttk.LabelFrame(left,text="Decoded RX")
        left.add(rx_dec_frame,weight=1)
        self.decoded_text=tk.Text(rx_dec_frame,width=54,height=10,wrap="word")
        self.decoded_text.pack(fill=tk.BOTH,expand=True,padx=6,pady=6)
        self.decoded_text.insert("1.0","(No decoded data yet)")

        # Waterfall
        wf_frame=ttk.LabelFrame(right,text="Waterfall")
        wf_frame.pack(fill=tk.BOTH,expand=True,padx=6,pady=6)
        if MATPLOTLIB_AVAILABLE:
            self.fig=Figure(figsize=(9.6,6.4),dpi=100)
            self.ax=self.fig.add_subplot(111); self.ax.set_axis_off()
            self.canvas=FigureCanvasTkAgg(self.fig,master=wf_frame)
            self.canvas_widget=self.canvas.get_tk_widget()
            self.canvas_widget.pack(fill=tk.BOTH,expand=True)
        else:
            ttk.Label(wf_frame,text="matplotlib not installed").pack(padx=20,pady=20)

        gauge_bar=ttk.Frame(wf_frame); gauge_bar.pack(fill=tk.X,padx=6,pady=4)
        ttk.Label(gauge_bar,text="RX dB").pack(side=tk.LEFT)
        self.rx_gauge=ttk.Progressbar(gauge_bar,orient=tk.HORIZONTAL,length=160,mode="determinate",maximum=100,
                                      variable=self.rx_level_var)
        self.rx_gauge.pack(side=tk.LEFT,padx=8)
        ttk.Label(gauge_bar,text="TX dB").pack(side=tk.LEFT)
        self.tx_gauge=ttk.Progressbar(gauge_bar,orient=tk.HORIZONTAL,length=160,mode="determinate",maximum=100,
                                      variable=self.tx_level_var)
        self.tx_gauge.pack(side=tk.LEFT,padx=8)

        # Log
        log_frame=ttk.LabelFrame(self,text="Log")
        log_frame.pack(fill=tk.BOTH,expand=False,padx=10,pady=(0,8))
        self.log_text=tk.Text(log_frame,wrap="char",height=8)
        self.log_text.pack(fill=tk.BOTH,expand=True)
        self._apply_log_font()

        self._init_waterfall()

    # ------------- Styling -------------
    def _style_button(self,b: tk.Button):
        b.configure(bg=BTN_BG,fg=BTN_FG,activebackground=BTN_ACTIVE_BG,relief="raised",bd=1,highlightthickness=0)
        def on_enter(e):
            if b is self.monitor_button:
                b.config(bg=MON_ON_BG if self.monitor_enabled else HOVER_DARKEN,
                         fg=MON_ON_FG if self.monitor_enabled else BTN_FG)
            elif b is self.tx_button and self.tx_active_flag:
                b.config(bg="#A0001C")
            elif b is self.tune_button and self.test_tune_active:
                b.config(bg="#A0001C")
            else:
                b.config(bg=HOVER_DARKEN)
        def on_leave(e): self._refresh_button(b)
        b.bind("<Enter>",on_enter); b.bind("<Leave>",on_leave)

    def _refresh_button(self,b: tk.Button):
        if b is self.monitor_button:
            b.config(bg=MON_ON_BG if self.monitor_enabled else MON_OFF_BG,
                     fg=MON_ON_FG if self.monitor_enabled else MON_OFF_FG); return
        if b is self.tx_button:
            b.config(bg=TX_ACTIVE_BG if self.tx_active_flag else BTN_BG,
                     fg=TX_ACTIVE_FG if self.tx_active_flag else BTN_FG); return
        if b is self.tune_button:
            b.config(bg=TUNE_ACTIVE_BG if self.test_tune_active else BTN_BG,
                     fg=TUNE_ACTIVE_FG if self.test_tune_active else BTN_FG); return
        if b is self.stop_button:
            b.config(bg="#E0E0E0",fg=BTN_FG); return
        b.config(bg=BTN_BG,fg=BTN_FG)

    def _apply_transmit_button_state(self, tx_active: bool, tune_active: bool):
        self.tx_active_flag=tx_active
        self.test_tune_active=tune_active
        for b in [self.tx_button,self.tune_button,self.stop_button,self.save_button,self.decode_button,self.monitor_button]:
            self._refresh_button(b)

    # ------------- Waterfall -------------
    def _init_waterfall(self):
        max_freq=int(self.settings.get("max_freq",3000))
        rows=int(self.settings.get("wf_max_rows",240))
        bins=256
        self.wf_freqs=np.linspace(0,max_freq,bins)
        self.wf_data=np.full((rows,bins),-120.0,dtype=np.float32)
        self._draw_initial_wf()

    def reinit_waterfall(self):
        self._init_waterfall()

    def _draw_initial_wf(self):
        if not MATPLOTLIB_AVAILABLE: return
        arr=self.wf_data
        vmax=np.max(arr); vmin=vmax-float(self.settings.get("wf_drange_db",60.0))
        self.ax.clear()
        self.wf_img=self.ax.imshow(arr,aspect='auto',origin='lower',
                                   extent=[self.wf_freqs[0],self.wf_freqs[-1],0,arr.shape[0]],
                                   cmap=self.settings.get("wf_colormap","magma"),
                                   vmin=vmin,vmax=vmax,interpolation='nearest')
        self.ax.set_axis_off()
        try: self.canvas.draw_idle()
        except Exception: pass

    def _make_slice(self,samples: np.ndarray):
        if samples.size==0: return None
        sr=int(self.settings.get("sr",48000)); max_freq=int(self.settings.get("max_freq",3000))
        nper=int(self.settings.get("wf_nperseg",512))
        data=samples[-nper:] if samples.size>=nper else np.pad(samples,(nper-samples.size,0))
        win=np.hanning(nper)
        spec=np.fft.rfft(data*win)
        freqs=np.fft.rfftfreq(nper,1.0/sr)
        mask=freqs<=max_freq
        freqs=freqs[mask]; mag_db=20.*np.log10(np.abs(spec[mask])+1e-12)
        try:
            return np.interp(self.wf_freqs,freqs,mag_db,left=mag_db[0],right=mag_db[-1]).astype(np.float32)
        except Exception:
            return np.full_like(self.wf_freqs,-120.0,dtype=np.float32)

    def _push_slice(self,slice_vals: np.ndarray):
        if slice_vals is None or slice_vals.size!=self.wf_data.shape[1]: return
        with self.wf_lock:
            self.wf_data[:-1]=self.wf_data[1:]
            self.wf_data[-1]=slice_vals
            arr=self.wf_data
        if self.wf_img is not None:
            vmax=np.max(arr); vmin=vmax-float(self.settings.get("wf_drange_db",60.0))
            self.wf_img.set_data(arr); self.wf_img.set_clim(vmin=vmin,vmax=vmax)
            try: self.canvas.draw_idle()
            except Exception: pass

    # ------------- Monitor -------------
    def _start_monitor_stream(self):
        sr=int(self.settings.get("sr",48000))
        fps=self.settings.get("wf_fps")
        if fps is not None:
            try:
                fps=int(fps); interval_s=1.0/max(4,fps)
                blocksize=max(128,int(sr*interval_s))
            except Exception:
                blocksize=max(256,int(sr*0.4))
        else:
            interval_s=float(self.settings.get("wf_chunk_seconds",0.4))
            blocksize=max(256,int(sr*interval_s))
        device_in=self.settings.get("audio_input_index")
        self.monitor=InputMonitor(sr,device_in,blocksize,self.monitor_queue,self.log_q)
        self.monitor.start()
        self.monitor_enabled=True
        self._refresh_button(self.monitor_button)

    def _stop_monitor_stream(self):
        if self.monitor: self.monitor.stop()
        self.monitor_enabled=False
        self._refresh_button(self.monitor_button)

    def _toggle_monitor(self):
        if self.monitor_enabled: self._stop_monitor_stream()
        else: self._start_monitor_stream()

    def _monitor_update_loop(self):
        fps=self.settings.get("wf_fps")
        if fps is not None:
            try: interval_ms=int(1000/max(4,int(fps)))
            except Exception: interval_ms=int(float(self.settings.get("wf_chunk_seconds",0.4))*1000)
        else:
            interval_ms=int(float(self.settings.get("wf_chunk_seconds",0.4))*1000)

        if self.monitor_enabled and self.monitor and self.monitor.active:
            chunks=[]
            try:
                while not self.monitor_queue.empty() and len(chunks)<8:
                    chunks.append(self.monitor_queue.get_nowait())
            except Exception: pass
            if chunks:
                samples=np.concatenate(chunks)
                self._push_slice(self._make_slice(samples))
                self._last_rx_chunk=samples
        self.after(interval_ms,self._monitor_update_loop)

    # ------------- Gauges -------------
    def _update_rx_gauge(self):
        rms=0.0
        if self._last_rx_chunk.size>0:
            rms=np.sqrt(np.mean(self._last_rx_chunk**2))
        db=20.*np.log10(rms+1e-9); db_clamped=max(-60.0,min(0.0,db))
        self.rx_level_var.set(int((db_clamped+60.)/60.*100))
        self.after(350,self._update_rx_gauge)

    def _update_tx_gauge(self):
        if self.tx_active_flag and self.tx_samples is not None:
            seg=int(self.tx_chunk_len*self.tx_sr)
            start=self.tx_index
            end=min(self.tx_samples.size,start+seg)
            chunk=self.tx_samples[start:end]
            if chunk.size>0:
                rms=np.sqrt(np.mean(chunk**2))
                db=20.*np.log10(rms+1e-9); db_clamped=max(-60.0,min(0.0,db))
                self.tx_level_var.set(int((db_clamped+60.)/60.*100))
                if not self.test_tune_active:
                    self._push_slice(self._make_slice(chunk))
            self.tx_index=end
        else:
            self.tx_level_var.set(0)
        self.after(int(self.tx_chunk_len*1000),self._update_tx_gauge)

    # ------------- LEDs -------------
    def _update_leds(self):
        rx_lvl=self.rx_level_var.get()/100.0
        if self.monitor_enabled:
            g=int(0x33+rx_lvl*(0xFF-0x33))
            rx_color=f"#00{g:02X}{int(0x30+rx_lvl*(0x66-0x30)):02X}"
        else:
            rx_color="#222222"
        self.rx_led_canvas.itemconfig(self.rx_led_id, fill=rx_color)
        if self.test_tune_active:
            self._tune_blink=not self._tune_blink
            self.tx_led_canvas.itemconfig(self.tx_led_id, fill=("#FF6020" if self._tune_blink else "#4A0A0A"))
        elif self.tx_active_flag and self.tx_samples is not None:
            seg=int(self.tx_chunk_len*self.tx_sr)
            start=max(0,self.tx_index-seg)
            chunk=self.tx_samples[start:self.tx_index]
            if chunk.size>0:
                spec=np.fft.rfft(chunk*np.hanning(chunk.size))
                freqs=np.fft.rfftfreq(chunk.size,1.0/self.tx_sr)
                mag=np.abs(spec)
                centroid=float(np.sum(freqs*mag)/np.sum(mag)) if mag.sum()>0 else 0.0
                max_freq=int(self.settings.get("max_freq",3000))
                norm=min(1.0,centroid/max_freq)
                r=int(0x40+norm*(0xFF-0x40)); g=int(0x05+norm*(0x80-0x05))
                color=f"#{r:02X}{g:02X}10"
            else:
                color="#330000"
            self.tx_led_canvas.itemconfig(self.tx_led_id, fill=color)
        else:
            self.tx_led_canvas.itemconfig(self.tx_led_id, fill="#333333")
        self.after(200,self._update_leds)

    # ------------- Logging -------------
    def log(self,msg):
        if msg.endswith("\n"): msg=msg[:-1]
        if self.settings.get("show_log_timestamp",True):
            stamp=time.strftime("%H:%M:%S"); line=f"[{stamp}] {msg}\n"
        else:
            line=msg+"\n"
        self.log_q.put(line)

    def _poll_log_queue(self):
        try:
            while True:
                line=self.log_q.get_nowait()
                self.log_text.insert(tk.END,line)
                if self.settings.get("log_autoscroll",True):
                    self.log_text.see(tk.END)
        except queue.Empty: pass
        self.after(120,self._poll_log_queue)

    # ------------- Preset speed radios -------------
    def _on_speed_changed(self):
        key=self.speed_var.get()
        self.settings["default_preset"]=key
        pmap={
            "Slow": self.settings.get("preset_slow", DEFAULT_PRESETS["Slow"]),
            "Normal": self.settings.get("preset_normal", DEFAULT_PRESETS["Normal"]),
            "Fast": self.settings.get("preset_fast", DEFAULT_PRESETS["Fast"]),
            "VeryFast": self.settings.get("preset_veryfast", DEFAULT_PRESETS["VeryFast"]),
        }
        d,g=pmap.get(key, DEFAULT_PRESETS["Normal"])
        self.settings["slider_dur_ms"]=d*1000.0
        self.settings["slider_gap_ms"]=g*1000.0
        save_settings(self.settings)
        self.log(f"Preset set: {key} dur={d:.3f}s gap={g:.3f}s")

    def _speed_scale(self,dur_s):
        norm=self.settings.get("preset_normal",DEFAULT_PRESETS["Normal"])[0]
        try: norm=float(norm)
        except Exception: norm=DEFAULT_PRESETS["Normal"][0]
        if norm<=0: norm=DEFAULT_PRESETS["Normal"][0]
        return max(0.05,min(20.0,dur_s/norm))

    def _current_preset_tuple(self):
        name=self.settings.get("default_preset","Normal")
        key="preset_veryfast" if name.lower()=="veryfast" else f"preset_{name.lower()}"
        return self.settings.get(key, DEFAULT_PRESETS.get(name, DEFAULT_PRESETS["Normal"]))

    # ------------- Sample assembly -------------
    def _assemble_samples(self,text,sr,dur_s,gap_s,amp,beep_amp,direction,preamble):
        parts=[]; scale=self._speed_scale(dur_s)
        sig=build_signature_sequence(self.settings,sr,amp=beep_amp,speed_scale=scale)
        if sig.size>0: parts.append(sig); parts.append(np.zeros(int(round(0.03*sr)),dtype=np.float32))
        marker=build_marker_sequence(self.settings,sr,amp=beep_amp,speed_scale=scale)
        if marker.size>0: parts.append(marker); parts.append(np.zeros(int(round(0.03*sr)),dtype=np.float32))
        start_seq=parse_beep_spec_ms(self.settings.get("start_beep",""))
        if self.settings.get("enable_beeps",True) and start_seq:
            parts.append(build_beeps_sequence(start_seq,sr,amp=beep_amp,
                                              speed_scale=(scale if self.settings.get("link_beeps_speed",True) else 1.0)))
        body=text_to_wave(text,sr,dur_s,gap_s,amp,direction,preamble)
        if body.size>0: parts.append(body)
        end_seq=parse_beep_spec_ms(self.settings.get("end_beep",""))
        if self.settings.get("enable_beeps",True) and end_seq:
            parts.append(np.zeros(int(round(0.02*sr)),dtype=np.float32))
            parts.append(build_beeps_sequence(end_seq,sr,amp=beep_amp,
                                              speed_scale=(scale if self.settings.get("link_beeps_speed",True) else 1.0)))
        if not parts: return np.zeros(0,dtype=np.float32)
        out=np.concatenate(parts)
        peak=float(np.max(np.abs(out))) or 1.0
        if peak>1.0: out=out/peak*0.99
        return out.astype(np.float32)

    # ------------- TX start / stop -------------
    def start_tx(self):
        if self.play_worker and self.play_worker.is_alive():
            messagebox.showinfo("TX","Already transmitting."); return
        dur_s,gap_s=self._current_preset_tuple()
        try: dur_s=float(self.settings.get("slider_dur_ms",dur_s*1000.0))/1000.0
        except Exception: pass
        try: gap_s=float(self.settings.get("slider_gap_ms",gap_s*1000.0))/1000.0
        except Exception: pass
        text=self.text_widget.get("1.0",tk.END).strip()
        if not text:
            messagebox.showerror("Input","Enter text first."); return
        amp=float(self.amp_var.get()); beep_amp=float(self.beep_amp_var.get())
        direction=self.dir_var.get(); preamble=int(self.preamble_var.get())
        sr=int(self.settings.get("sr",48000))
        samples=self._assemble_samples(text,sr,dur_s,gap_s,amp,beep_amp,direction,preamble)
        if samples.size==0:
            messagebox.showinfo("TX","Nothing to transmit."); return
        def on_start():
            self.stop_button.config(state=tk.NORMAL)
            self._apply_transmit_button_state(True,self.test_tune_active)
            self.log("TX ON")
        def on_done():
            self.after(0,self._tx_finished)
        device_out=self.settings.get("audio_output_index")
        self.play_worker=PlaybackWorker(samples,sr,device_out,self.log_q,on_start=on_start,on_done=on_done)
        self.play_worker.start()

    def stop_tx(self):
        if not self.play_worker: return
        w=self.play_worker
        try: w.stop()
        except Exception: pass
        def waiter(th):
            try: th.join(timeout=3.0)
            except Exception: pass
            self.after(0,self._tx_finished)
        threading.Thread(target=waiter,args=(w,),daemon=True).start()

    def _tx_finished(self):
        self.play_worker=None
        self.stop_button.config(state=tk.DISABLED)
        self._apply_transmit_button_state(False,self.test_tune_active)
        self.log("Transmit finished")
        self.tx_active_flag=False

    # ------------- Tune -------------
    def toggle_tune(self):
        if self.test_tune_active: self._stop_tune()
        else: self._start_tune()

    def _start_tune(self):
        sr=int(self.settings.get("sr",48000))
        amp=float(self.beep_amp_var.get())
        device_out=self.settings.get("audio_output_index")
        self.tune_stop_event=threading.Event()
        self.tune_thread=ContinuousTune(500.0,sr,device_out,self.tune_stop_event,self.log_q,amplitude=amp)
        try: self.tune_thread.start()
        except Exception as e:
            messagebox.showerror("Tune",f"Failed: {e}"); return
        self.test_tune_active=True
        self._apply_transmit_button_state(self.tx_active_flag,True)
        self.log("Tune ON")

    def _stop_tune(self):
        if self.tune_stop_event: self.tune_stop_event.set()
        def waiter(th):
            if th:
                try: th.join(timeout=2.0)
                except Exception: pass
            self.after(0,self._tune_finished)
        threading.Thread(target=waiter,args=(self.tune_thread,),daemon=True).start()

    def _tune_finished(self):
        self.tune_thread=None
        self.tune_stop_event=None
        self.test_tune_active=False
        self._apply_transmit_button_state(self.tx_active_flag,False)
        self.log("Tune OFF")

    # ------------- Save WAV -------------
    def save_wav_dialog(self):
        text=self.text_widget.get("1.0",tk.END).strip()
        if not text:
            messagebox.showerror("Input","Enter text first."); return
        fn=filedialog.asksaveasfilename(defaultextension=".wav",filetypes=[("WAV files","*.wav")])
        if not fn: return
        if os.path.exists(fn):
            if not messagebox.askyesno("Overwrite", f"File exists: {os.path.basename(fn)}\nOverwrite?"): return
        dur_s,gap_s=self._current_preset_tuple()
        try: dur_s=float(self.settings.get("slider_dur_ms",dur_s*1000.0))/1000.0
        except Exception: pass
        try: gap_s=float(self.settings.get("slider_gap_ms",gap_s*1000.0))/1000.0
        except Exception: pass
        amp=float(self.amp_var.get()); beep_amp=float(self.beep_amp_var.get())
        sr=int(self.settings.get("sr",48000))
        direction=self.dir_var.get(); preamble=int(self.preamble_var.get())
        start_seq=parse_beep_spec_ms(self.settings.get("start_beep","")) if self.settings.get("enable_beeps",True) else []
        end_seq=parse_beep_spec_ms(self.settings.get("end_beep","")) if self.settings.get("enable_beeps",True) else []
        parts=[]; scale=self._speed_scale(dur_s)
        sig=build_signature_sequence(self.settings,sr,amp=beep_amp,speed_scale=scale)
        if sig.size>0: parts.append(sig); parts.append(np.zeros(int(round(0.03*sr)),dtype=np.float32))
        marker=build_marker_sequence(self.settings,sr,amp=beep_amp,speed_scale=scale)
        if marker.size>0: parts.append(marker); parts.append(np.zeros(int(round(0.03*sr)),dtype=np.float32))
        if start_seq:
            parts.append(build_beeps_sequence(start_seq,sr,amp=beep_amp,
                                              speed_scale=(scale if self.settings.get("link_beeps_speed",True) else 1.0)))
        body=text_to_wave(text,sr,dur_s,gap_s,amp,direction,preamble)
        if body.size>0: parts.append(body)
        if end_seq:
            parts.append(np.zeros(int(round(0.02*sr)),dtype=np.float32))
            parts.append(build_beeps_sequence(end_seq,sr,amp=beep_amp,
                                              speed_scale=(scale if self.settings.get("link_beeps_speed",True) else 1.0)))
        if not parts:
            messagebox.showinfo("Nothing","No samples."); return
        samples=np.concatenate(parts).astype(np.float32)
        try:
            from scipy.io.wavfile import write as wavwrite
            wavwrite(fn,sr,np.int16(np.clip(samples,-1.0,1.0)*32767))
            messagebox.showinfo("Saved",f"WAV saved: {fn}")
        except Exception as e:
            messagebox.showerror("Save error",f"Failed: {e}")

    # ------------- Apply settings after dialog save -------------
    def apply_settings(self, settings: dict):
        self.settings.update(settings)
        self.speed_var.set(self.settings.get("default_preset","Normal"))
        self.callsign_disp.set(f"Callsign: {self.settings.get('callsign','') or '(none)'}")
        self.grid_disp.set(f"Grid: {self.settings.get('grid','') or '(none)'}")
        self._apply_log_font()
        self._apply_transmit_button_state(self.tx_active_flag,self.test_tune_active)
        self.reinit_waterfall()

    def _apply_log_font(self):
        size=int(self.settings.get("log_font_size",11))
        try: self.log_text.configure(font=("Consolas",size))
        except Exception: self.log_text.configure(font=("Courier",size))

    def _decode_stub(self):
        self.log("Decode pressed (stub)")

def main():
    app=ChirpApp()
    app.mainloop()

if __name__=="__main__":
    main()
