"""
Taigi-whisper-Mac  v2
台語・中文語音辨識工具 — Apple Silicon 優化版
"""

import warnings, os as _os
warnings.filterwarnings("ignore")
_os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

# torch 必須在主線程預先 import，否則 macOS MPS 初始化會 crash
try:
    import torch as _torch_preload  # noqa: F401
except Exception:
    pass

try:
    import customtkinter as ctk
except ImportError:
    raise ImportError("找不到 customtkinter！請先執行 start.sh")

from tkinter import filedialog, messagebox
import threading
import queue
import os
import json
import subprocess
import time
from datetime import datetime

# ── 設計系統 ────────────────────────────────────────
BG          = "#0F0F23"
CARD        = "#1A1740"
CARD2       = "#12102A"
BORDER      = "#2D2B5E"
ACCENT      = "#F97316"   # 橘色 — 開始按鈕
ACCENT2     = "#7C3AED"   # 紫色 — 階段 2
SUCCESS     = "#22C55E"
WARNING     = "#F59E0B"
ERROR       = "#EF4444"
TEXT        = "#F8FAFC"
TEXT_MUTED  = "#94A3B8"

ENGINES = ["faster-whisper", "Breeze-ASR-25（繁中）", "Breeze-ASR-26（台語）"]
MODELS  = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
FORMATS = ["srt", "txt", "json"]

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "mac_config.json")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("Taigi Whisper — 語音辨識工具")
        self.geometry("680x920")
        self.minsize(600, 800)
        self.configure(fg_color=BG)

        # 狀態
        self._q          = queue.Queue()
        self._stop_flag  = threading.Event()
        self._is_running = False

        # 設定變數
        self.audio_path     = ctk.StringVar()
        self.engine_var     = ctk.StringVar(value=ENGINES[0])
        self.model_var      = ctk.StringVar(value="medium")
        self.diarize_var    = ctk.BooleanVar(value=False)
        self.hf_token_var   = ctk.StringVar()
        self.min_spk_var    = ctk.StringVar()
        self.max_spk_var    = ctk.StringVar()
        self.fmt_var        = ctk.StringVar(value="srt")
        self.output_dir_var = ctk.StringVar(value=os.path.expanduser("~/Downloads"))

        self._load_config()
        self._build_ui()
        self._poll_queue()   # 啟動 queue 輪詢

    # ════════════════════════════════════════════
    # UI 建立
    # ════════════════════════════════════════════
    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG,
                                        scrollbar_button_color=BORDER,
                                        scrollbar_button_hover_color=ACCENT)
        scroll.pack(fill="both", expand=True)
        scroll.grid_columnconfigure(0, weight=1)
        self._scroll = scroll
        r = 0

        # 標題
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.grid(row=r, column=0, sticky="ew", padx=24, pady=(24, 4))
        ctk.CTkLabel(hdr, text="Taigi Whisper",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(hdr, text="台語・中文語音辨識工具  ｜  Mac 版",
                     font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(anchor="w")
        r += 1

        # 音訊選擇
        self._sec(r, "音訊檔案"); r += 1
        r = self._build_audio(r);  r += 1

        # 辨識設定
        self._sec(r, "辨識設定"); r += 1
        r = self._build_model(r);  r += 1

        # 說話者辨識
        self._sec(r, "說話者辨識（選用）"); r += 1
        r = self._build_diarize(r); r += 1

        # 輸出設定
        self._sec(r, "輸出設定"); r += 1
        r = self._build_output(r); r += 1

        # 按鈕
        r = self._build_actions(r); r += 1

        # 進度
        r = self._build_progress(r); r += 1

        # 日誌
        self._sec(r, "執行日誌"); r += 1
        self._build_log(r)

    def _sec(self, row, title):
        ctk.CTkLabel(self._scroll, text=title,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=TEXT_MUTED
                     ).grid(row=row, column=0, sticky="w", padx=28, pady=(18, 2))

    def _card(self, row, pady=(0, 0)):
        f = ctk.CTkFrame(self._scroll, fg_color=CARD, corner_radius=12,
                         border_width=1, border_color=BORDER)
        f.grid(row=row, column=0, sticky="ew", padx=20, pady=pady)
        f.grid_columnconfigure(0, weight=1)
        return f

    # ── 音訊選擇 ──
    def _build_audio(self, row):
        card = self._card(row)

        drop = ctk.CTkFrame(card, fg_color=CARD2, corner_radius=8,
                            height=88, cursor="hand2")
        drop.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        drop.grid_propagate(False)
        drop.grid_columnconfigure(0, weight=1)

        self._drop_lbl = ctk.CTkLabel(
            drop,
            text="點擊選擇音訊檔案\nm4a · mp3 · wav · mp4 · mov",
            font=ctk.CTkFont(size=12), text_color=TEXT_MUTED, justify="center")
        self._drop_lbl.grid(row=0, column=0, pady=22)

        for w in (drop, self._drop_lbl):
            w.bind("<Button-1>", lambda e: self._browse_audio())

        ctk.CTkLabel(card, textvariable=self.audio_path,
                     font=ctk.CTkFont(size=10), text_color=TEXT_MUTED,
                     wraplength=580, justify="left"
                     ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))
        return row

    # ── 辨識設定 ──
    def _build_model(self, row):
        card = self._card(row)
        card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(card, text="引擎", font=ctk.CTkFont(size=11),
                     text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        ctk.CTkComboBox(card, variable=self.engine_var, values=ENGINES,
                        command=self._on_engine_change,
                        fg_color=CARD2, border_color=BORDER,
                        button_color=BORDER, dropdown_fg_color=CARD,
                        text_color=TEXT
                        ).grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=(0, 14))

        self._model_lbl = ctk.CTkLabel(card, text="模型大小", font=ctk.CTkFont(size=11),
                                       text_color=TEXT_MUTED)
        self._model_lbl.grid(row=0, column=1, sticky="w", padx=(8, 16), pady=(14, 2))
        self._model_combo = ctk.CTkComboBox(card, variable=self.model_var, values=MODELS,
                                            fg_color=CARD2, border_color=BORDER,
                                            button_color=BORDER, dropdown_fg_color=CARD,
                                            text_color=TEXT)
        self._model_combo.grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=(0, 14))
        return row

    # ── 說話者辨識 ──
    def _build_diarize(self, row):
        card = self._card(row)

        # 開關列
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text="啟用說話者辨識",
                     font=ctk.CTkFont(size=13), text_color=TEXT
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, text="自動區分不同講者，需 HuggingFace 免費帳號",
                     font=ctk.CTkFont(size=10), text_color=TEXT_MUTED
                     ).grid(row=1, column=0, sticky="w")
        ctk.CTkSwitch(top, variable=self.diarize_var,
                      command=self._toggle_diarize,
                      progress_color=ACCENT, text=""
                      ).grid(row=0, column=1, rowspan=2)

        # 展開詳情（預設隱藏）
        self._diarize_detail = ctk.CTkFrame(card, fg_color="transparent")
        self._diarize_detail.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(self._diarize_detail, text="HuggingFace Token",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MUTED
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 2))
        ctk.CTkEntry(self._diarize_detail, textvariable=self.hf_token_var,
                     show="*", placeholder_text="hf_xxxxxxxxxxxx",
                     fg_color=CARD2, border_color=BORDER, text_color=TEXT
                     ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))

        ctk.CTkLabel(self._diarize_detail, text="最少講者數",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MUTED
                     ).grid(row=2, column=0, sticky="w", padx=(16, 4), pady=(0, 2))
        ctk.CTkEntry(self._diarize_detail, textvariable=self.min_spk_var,
                     placeholder_text="（選填）",
                     fg_color=CARD2, border_color=BORDER, text_color=TEXT
                     ).grid(row=3, column=0, sticky="ew", padx=(16, 4), pady=(0, 10))

        ctk.CTkLabel(self._diarize_detail, text="最多講者數",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MUTED
                     ).grid(row=2, column=1, sticky="w", padx=(4, 16), pady=(0, 2))
        ctk.CTkEntry(self._diarize_detail, textvariable=self.max_spk_var,
                     placeholder_text="（選填）",
                     fg_color=CARD2, border_color=BORDER, text_color=TEXT
                     ).grid(row=3, column=1, sticky="ew", padx=(4, 16), pady=(0, 10))

        link = ctk.CTkLabel(self._diarize_detail,
                            text="如何申請 Token？點此查看說明",
                            font=ctk.CTkFont(size=10, underline=True),
                            text_color=ACCENT, cursor="hand2")
        link.grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 14))
        link.bind("<Button-1>", lambda e: subprocess.run(
            ["open", "https://huggingface.co/settings/tokens"], check=False))

        self._toggle_diarize()
        return row

    # ── 輸出設定 ──
    def _build_output(self, row):
        card = self._card(row)

        ctk.CTkLabel(card, text="輸出格式", font=ctk.CTkFont(size=11),
                     text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        fmt_row = ctk.CTkFrame(card, fg_color="transparent")
        fmt_row.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))
        for i, fmt in enumerate(FORMATS):
            ctk.CTkRadioButton(fmt_row, text=fmt.upper(),
                               variable=self.fmt_var, value=fmt,
                               fg_color=ACCENT, hover_color=ACCENT,
                               text_color=TEXT
                               ).grid(row=0, column=i, padx=(0, 16))

        ctk.CTkLabel(card, text="儲存目錄", font=ctk.CTkFont(size=11),
                     text_color=TEXT_MUTED).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 4))

        dir_row = ctk.CTkFrame(card, fg_color="transparent")
        dir_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        dir_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(dir_row, textvariable=self.output_dir_var,
                     fg_color=CARD2, border_color=BORDER, text_color=TEXT
                     ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(dir_row, text="選擇", width=64, height=32,
                      fg_color=BORDER, hover_color="#3D3B7A",
                      command=self._browse_output_dir
                      ).grid(row=0, column=1)
        return row

    # ── 操作按鈕 ──
    def _build_actions(self, row):
        f = ctk.CTkFrame(self._scroll, fg_color="transparent")
        f.grid(row=row, column=0, sticky="ew", padx=20, pady=(20, 4))
        f.grid_columnconfigure(0, weight=1)

        self._run_btn = ctk.CTkButton(
            f, text="開始辨識",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=52, corner_radius=12,
            fg_color=ACCENT, hover_color="#EA6C10",
            command=self._start)
        self._run_btn.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self._stop_btn = ctk.CTkButton(
            f, text="停止",
            font=ctk.CTkFont(size=13), height=34, corner_radius=8,
            fg_color=BORDER, hover_color="#3D3B7A",
            state="disabled", command=self._stop)
        self._stop_btn.grid(row=1, column=0, sticky="ew")

        self._status_lbl = ctk.CTkLabel(f, text="",
                                        font=ctk.CTkFont(size=11),
                                        text_color=TEXT_MUTED)
        self._status_lbl.grid(row=2, column=0, pady=(6, 0))
        return row

    # ── 進度 ──
    def _build_progress(self, row):
        f = ctk.CTkFrame(self._scroll, fg_color="transparent")
        f.grid(row=row, column=0, sticky="ew", padx=20, pady=(6, 0))
        f.grid_columnconfigure((0, 1), weight=1)

        def _prog_card(parent, col, title, color):
            c = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10,
                             border_width=1, border_color=BORDER)
            c.grid(row=0, column=col, sticky="ew",
                   padx=(0, 5) if col == 0 else (5, 0))
            c.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(c, text=title, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=color).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
            bar = ctk.CTkProgressBar(c, progress_color=color, height=5)
            bar.set(0)
            bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))
            lbl = ctk.CTkLabel(c, text="等待中", font=ctk.CTkFont(size=10),
                               text_color=TEXT_MUTED)
            lbl.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))
            return bar, lbl

        self._prog1, self._phase1_lbl = _prog_card(f, 0, "階段 1：快速轉錄", ACCENT)
        self._prog2, self._phase2_lbl = _prog_card(f, 1, "階段 2：講者辨識", ACCENT2)
        return row

    # ── 執行日誌 ──
    def _build_log(self, row):
        card = self._card(row, pady=(0, 24))
        self._log_box = ctk.CTkTextbox(card, height=180,
                                       fg_color=CARD2,
                                       font=ctk.CTkFont("Menlo", 11),
                                       text_color=TEXT_MUTED)
        self._log_box.grid(row=0, column=0, sticky="ew", padx=1, pady=1)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="e", padx=12, pady=(0, 12))

        ctk.CTkButton(btns, text="在 Finder 中開啟", width=128, height=28,
                      fg_color=BORDER, hover_color="#3D3B7A",
                      font=ctk.CTkFont(size=11),
                      command=lambda: subprocess.run(
                          ["open", self.output_dir_var.get()], check=False)
                      ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="清除日誌", width=80, height=28,
                      fg_color=BORDER, hover_color="#3D3B7A",
                      font=ctk.CTkFont(size=11),
                      command=lambda: self._log_box.delete("1.0", "end")
                      ).pack(side="left")

    # ════════════════════════════════════════════
    # 事件
    # ════════════════════════════════════════════
    def _browse_audio(self):
        path = filedialog.askopenfilename(
            title="選擇音訊檔案",
            filetypes=[("音訊/影片", "*.m4a *.mp3 *.wav *.mp4 *.mov *.aac *.flac"),
                       ("所有檔案", "*.*")])
        if path:
            self.audio_path.set(path)
            self._drop_lbl.configure(
                text=f"已選擇：{os.path.basename(path)}", text_color=TEXT)

    def _browse_output_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir_var.set(d)

    def _toggle_diarize(self):
        if self.diarize_var.get():
            self._diarize_detail.grid(row=1, column=0, sticky="ew")
        else:
            self._diarize_detail.grid_forget()

    def _on_engine_change(self, _=None):
        is_fw = self.engine_var.get() == "faster-whisper"
        self._model_combo.configure(state="normal" if is_fw else "disabled")
        self._model_lbl.configure(text_color=TEXT_MUTED if is_fw else BORDER)

    # ════════════════════════════════════════════
    # Queue 架構（Thread-safe UI 更新）
    # ════════════════════════════════════════════
    def _poll_queue(self):
        try:
            while True:
                msg = self._q.get_nowait()
                t = msg.get("type")
                if t == "log":
                    self._log_box.insert("end", msg["text"] + "\n")
                    self._log_box.see("end")
                elif t == "prog1":
                    self._set_prog(self._prog1, self._phase1_lbl,
                                   msg["value"], msg.get("label", ""))
                elif t == "prog2":
                    self._set_prog(self._prog2, self._phase2_lbl,
                                   msg["value"], msg.get("label", ""))
                elif t == "status":
                    self._status_lbl.configure(
                        text=msg["text"], text_color=msg.get("color", TEXT_MUTED))
                elif t == "done":
                    self._set_running(False)
                    self._prog1.stop()
                    self._prog2.stop()
                elif t == "error":
                    self._set_running(False)
                    self._prog1.stop()
                    self._prog2.stop()
                    self._status_lbl.configure(
                        text="發生錯誤，請查看執行日誌", text_color=ERROR)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _set_prog(self, bar, lbl, value, label):
        if value == "indeterminate":
            bar.configure(mode="indeterminate")
            bar.start()
        else:
            bar.stop()
            bar.configure(mode="determinate")
            bar.set(float(value))
        lbl.configure(text=label)

    # ════════════════════════════════════════════
    # 辨識控制
    # ════════════════════════════════════════════
    def _start(self):
        audio = self.audio_path.get().strip()
        if not audio:
            messagebox.showerror("請先選擇音訊檔案", "請點擊上方區域選擇音訊檔案！")
            return
        if not os.path.exists(audio):
            messagebox.showerror("檔案不存在", f"找不到：{audio}")
            return

        # 主線程一次讀取所有設定，thread 不碰任何 Tkinter 物件
        params = {
            "audio":        audio,
            "output_dir":   self.output_dir_var.get().strip(),
            "engine":       self.engine_var.get(),
            "model":        self.model_var.get(),
            "diarize":      self.diarize_var.get(),
            "hf_token":     self.hf_token_var.get().strip(),
            "min_speakers": self.min_spk_var.get().strip(),
            "max_speakers": self.max_spk_var.get().strip(),
            "fmt":          self.fmt_var.get(),
        }

        self._save_config()
        self._set_running(True)
        self._stop_flag.clear()

        self._put_log("=" * 50)
        self._put_log(f"開始辨識 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._put_log(f"檔案：{audio}")
        self._put_log("=" * 50)

        threading.Thread(target=self._pipeline, args=(params,), daemon=True).start()

    def _stop(self):
        self._stop_flag.set()
        self._put_log("使用者要求停止...")
        self._q.put({"type": "status", "text": "停止中...", "color": WARNING})

    def _set_running(self, running: bool):
        self._is_running = running
        self._run_btn.configure(state="disabled" if running else "normal")
        self._stop_btn.configure(state="normal" if running else "disabled")
        if running:
            self._status_lbl.configure(text="辨識中...", text_color=ACCENT)

    # ════════════════════════════════════════════
    # 背景 Thread — 辨識邏輯
    # ════════════════════════════════════════════
    def _put_log(self, text):
        self._q.put({"type": "log", "text": text})

    def _put_prog(self, stage, value, label=""):
        self._q.put({"type": f"prog{stage}", "value": value, "label": label})

    def _pipeline(self, params):
        import traceback
        try:
            import torch
            audio      = params["audio"]
            output_dir = params["output_dir"]
            engine     = params["engine"]
            model_name = params["model"]
            fmt        = params["fmt"]
            os.makedirs(output_dir, exist_ok=True)

            # ── 階段 1：轉錄 ──────────────────────────────
            self._put_prog(1, "indeterminate", "載入模型...")

            BREEZE = {
                "Breeze-ASR-25（繁中）": "MediaTek-Research/Breeze-ASR-25",
                "Breeze-ASR-26（台語）": "MediaTek-Research/Breeze-ASR-26",
            }

            if engine in BREEZE:
                # Breeze-ASR 路徑
                model_id = BREEZE[engine]
                from transformers import pipeline as hf_pipeline
                self._put_log(f"[1/2] 載入 Breeze 模型：{model_id}（首次需下載，請耐心等候）")
                pipe = hf_pipeline("automatic-speech-recognition",
                                   model=model_id,
                                   device=torch.device("cpu"),
                                   torch_dtype=torch.float32)

                if self._stop_flag.is_set():
                    raise InterruptedError("使用者停止")

                self._put_prog(1, "indeterminate", "音訊解碼中...")
                self._put_log("[1/2] 用 ffmpeg 解碼音訊...")
                import numpy as np
                SR = 16000
                proc = subprocess.run(
                    ["ffmpeg", "-y", "-i", audio,
                     "-f", "f32le", "-acodec", "pcm_f32le",
                     "-ar", str(SR), "-ac", "1", "-"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if proc.returncode != 0:
                    raise RuntimeError(f"ffmpeg 失敗：{proc.stderr.decode(errors='replace')}")

                audio_np = np.frombuffer(proc.stdout, dtype=np.float32).copy()
                self._put_log(f"[1/2] 音訊長度：{len(audio_np)/SR:.1f}s，開始轉錄...")
                self._put_prog(1, "indeterminate", "轉錄中...")

                out = pipe({"raw": audio_np, "sampling_rate": SR})
                text = out.get("text", "").strip() if isinstance(out, dict) else str(out).strip()
                segments = [_Seg(0.0, len(audio_np) / SR, text)]
                self._put_log(f"[1/2] 完成，{len(segments)} 段")

            else:
                # faster-whisper 路徑
                from faster_whisper import WhisperModel
                fw_compute = "int8"
                self._put_log(f"[1/2] 載入模型：{model_name}  設備：cpu  精度：{fw_compute}")
                model = WhisperModel(model_name, device="cpu", compute_type=fw_compute)

                if self._stop_flag.is_set():
                    raise InterruptedError("使用者停止")

                self._put_prog(1, "indeterminate", "轉錄中...")
                self._put_log("[1/2] 開始轉錄...")
                t0 = time.time()
                segs_gen, info = model.transcribe(audio, language=None,
                                                  beam_size=5, vad_filter=True)
                segments = []
                duration = max(info.duration, 1.0)
                for seg in segs_gen:
                    if self._stop_flag.is_set():
                        raise InterruptedError("使用者停止")
                    segments.append(_Seg(seg.start, seg.end, seg.text.strip()))
                    pct = min(seg.end / duration, 1.0)
                    self._put_prog(1, pct, f"{seg.end:.1f}s / {duration:.1f}s")
                    self._put_log(f"  [{_fmt_t(seg.start)} → {_fmt_t(seg.end)}] {seg.text.strip()}")

                self._put_log(f"[1/2] 完成，{len(segments)} 段，耗時 {time.time()-t0:.1f}s")
                del model

            self._put_prog(1, 1.0, f"完成 {len(segments)} 段")

            # ── 階段 2：說話者辨識（可選）─────────────────
            speaker_map = {}
            if params["diarize"] and params["hf_token"]:
                self._put_prog(2, "indeterminate", "載入模型...")
                self._put_log("[2/2] 載入 pyannote 說話者辨識...")
                from pyannote.audio import Pipeline as PyPipeline
                import numpy as np

                diarize_pipe = PyPipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=params["hf_token"])
                diarize_pipe = diarize_pipe.to(torch.device("cpu"))

                if self._stop_flag.is_set():
                    raise InterruptedError("使用者停止")

                SR = 16000
                proc2 = subprocess.run(
                    ["ffmpeg", "-y", "-i", audio,
                     "-f", "f32le", "-acodec", "pcm_f32le",
                     "-ar", str(SR), "-ac", "1", "-"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                audio_np2 = np.frombuffer(proc2.stdout, dtype=np.float32).copy()
                waveform  = torch.from_numpy(audio_np2).unsqueeze(0)

                kwargs = {}
                if params["min_speakers"]:
                    kwargs["min_speakers"] = int(params["min_speakers"])
                if params["max_speakers"]:
                    kwargs["max_speakers"] = int(params["max_speakers"])

                self._put_log("[2/2] 執行講者辨識...")
                self._put_prog(2, "indeterminate", "分析中...")
                t2 = time.time()
                diarization = diarize_pipe(
                    {"waveform": waveform, "sample_rate": SR}, **kwargs)

                for seg_obj, _, speaker in diarization.itertracks(yield_label=True):
                    for s in segments:
                        overlap = min(s.end, seg_obj.end) - max(s.start, seg_obj.start)
                        if overlap > 0 and speaker not in speaker_map.get(id(s), ""):
                            speaker_map[id(s)] = speaker

                speakers = set(speaker_map.values())
                self._put_log(f"[2/2] 完成 {len(speakers)} 位講者，耗時 {time.time()-t2:.1f}s")
                self._put_prog(2, 1.0, f"完成，{len(speakers)} 位講者")
            else:
                self._put_prog(2, 0.0, "未啟用")

            # ── 輸出 ──────────────────────────────────────
            base     = os.path.splitext(os.path.basename(audio))[0]
            out_path = os.path.join(output_dir, f"{base}.{fmt}")
            _write(out_path, fmt, segments, speaker_map)

            elapsed = 0  # 略
            self._put_log(f"\n完成！輸出：{out_path}")
            self._q.put({"type": "status", "text": f"完成 → {os.path.basename(out_path)}",
                         "color": SUCCESS})

        except InterruptedError as e:
            self._put_log(f"\n{e}")
            self._q.put({"type": "status", "text": "已停止", "color": WARNING})
        except Exception as e:
            self._put_log(f"\n發生錯誤：{e}")
            self._put_log(traceback.format_exc())
            self._q.put({"type": "error"})
        finally:
            self._is_running = False   # 直接設，不排隊
            self._q.put({"type": "done"})

    # ════════════════════════════════════════════
    # 設定存取
    # ════════════════════════════════════════════
    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "engine":       self.engine_var.get(),
                    "model":        self.model_var.get(),
                    "diarize":      self.diarize_var.get(),
                    "hf_token":     self.hf_token_var.get(),
                    "min_speakers": self.min_spk_var.get(),
                    "max_speakers": self.max_spk_var.get(),
                    "fmt":          self.fmt_var.get(),
                    "output_dir":   self.output_dir_var.get(),
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                c = json.load(f)
            self.engine_var.set(c.get("engine", ENGINES[0]))
            self.model_var.set(c.get("model", "medium"))
            self.diarize_var.set(c.get("diarize", False))
            self.hf_token_var.set(c.get("hf_token", ""))
            self.min_spk_var.set(c.get("min_speakers", ""))
            self.max_spk_var.set(c.get("max_speakers", ""))
            self.fmt_var.set(c.get("fmt", "srt"))
            self.output_dir_var.set(c.get("output_dir", os.path.expanduser("~/Downloads")))
        except Exception:
            pass


# ── 輔助類別與函式 ────────────────────────────────
class _Seg:
    def __init__(self, start, end, text):
        self.start = start
        self.end   = end
        self.text  = text


def _fmt_t(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _write(path, fmt, segments, speaker_map):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if fmt == "srt":
            for i, s in enumerate(segments, 1):
                spk = speaker_map.get(id(s), "")
                prefix = f"[{spk}] " if spk else ""
                f.write(f"{i}\n{_fmt_t(s.start)} --> {_fmt_t(s.end)}\n{prefix}{s.text}\n\n")
        elif fmt == "txt":
            for s in segments:
                spk = speaker_map.get(id(s), "")
                prefix = f"[{spk}] " if spk else ""
                f.write(f"{prefix}{s.text}\n")
        elif fmt == "json":
            import json
            json.dump([{"start": s.start, "end": s.end,
                        "speaker": speaker_map.get(id(s), ""),
                        "text": s.text} for s in segments],
                      f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    app = App()
    app.mainloop()
