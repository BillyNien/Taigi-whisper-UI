"""
Taigi-whisper-UI
= faster-whisper 快速轉錄 + pyannote 講者辨識
跳過 word-level alignment，大幅加快速度同時保留講者標注
"""

import warnings
import os as _os
# 抑制 torchaudio / pyannote 的雜訊警告（MP3 subtype 等）
warnings.filterwarnings("ignore")
_os.environ.setdefault("PYTHONWARNINGS", "ignore")
_os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

try:
    import customtkinter as ctk
except ImportError:
    raise ImportError(
        "找不到 customtkinter！\n"
        "請先執行 start.bat 安裝所有套件，或手動執行 pip install customtkinter"
    )

from tkinter import filedialog, messagebox
import threading
import os
import sys
import json
import time
import io
from datetime import datetime

# ============================================================
# 設定
# ============================================================
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXEC = os.path.join(_SCRIPT_DIR, "venv", "Scripts", "python.exe")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hybrid_config.json")

# Breeze-ASR 模型對照
BREEZE_ENGINES = {
    "Breeze-ASR-25 (中英混語)": {
        "model_id": "MediaTek-Research/Breeze-ASR-25",
        "info": "MediaTek-Research/Breeze-ASR-25 · 中英混語 · transformers pipeline",
        "default_lang": "繁體中文",
        "lock_lang": False,
    },
    "Breeze-ASR-26 (台語)": {
        "model_id": "MediaTek-Research/Breeze-ASR-26",
        "info": "MediaTek-Research/Breeze-ASR-26 · 台語→中文字 · transformers pipeline",
        "default_lang": "台語 (Taigi)",
        "lock_lang": True,
    },
}

# 語言對照表：顯示名稱 -> (whisper 語言碼, 是否需要簡轉繁)
LANGUAGE_MAP = {
    "自動偵測":  (None,  False),
    "繁體中文":  ("zh",  True),
    "簡體中文":  ("zh",  False),
    "英文":      ("en",  False),
    "日文":      ("ja",  False),
    "韓文":      ("ko",  False),
    "粵語":      ("yue", False),
    "法文":      ("fr",  False),
    "德文":      ("de",  False),
    "西班牙文":  ("es",  False),
    "義大利文":  ("it",  False),
    "俄文":      ("ru",  False),
    "葡萄牙文":  ("pt",  False),
    "阿拉伯文":  ("ar",  False),
    "印地文":    ("hi",  False),
    "台語 (Taigi)": ("",   False),  # Breeze-ASR-26 專用
}

# ============================================================
# 顏色（淺色扁平，接近 Windows 系統原生）
# ============================================================
COLORS = {
    "bg": "#f3f3f3",
    "bg_alt": "#e8e8e8",
    "bg_input": "#ffffff",
    "accent": "#0078d4",
    "accent_hover": "#106ebe",
    "text": "#1f1f1f",
    "text_secondary": "#505050",
    "text_muted": "#808080",
    "border": "#c8c8c8",
    "border_light": "#dcdcdc",
    "success": "#107c10",
    "warning": "#ca5010",
    "error": "#c42b1c",
    "btn_bg": "#e1e1e1",
    "btn_hover": "#d0d0d0",
    "phase1": "#0078d4",
    "phase2": "#6b4fbb",
}

FONT_FAMILY = "Microsoft JhengHei UI"
FONT_FAMILY_MONO = "Consolas"

_BREEZE_PKGS = ["transformers", "accelerate"]


def _ensure_transformers(log_fn=None):
    """第一次使用 Breeze 模型時自動安裝 transformers + accelerate"""
    try:
        import transformers  # noqa: F401
        return
    except ImportError:
        pass
    import subprocess as _sp
    pip = os.path.join(os.path.dirname(PYTHON_EXEC), "pip.exe")
    for pkg in _BREEZE_PKGS:
        if log_fn:
            log_fn(f"自動安裝 {pkg}...")
        _sp.check_call([pip, "install", "-q", pkg])
    if log_fn:
        log_fn("安裝完成。")


class HybridWhisperGUI:
    """Taigi-whisper-UI 主 GUI"""

    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Taigi-whisper-UI — 快速轉錄 + 講者辨識")
        self.root.geometry("760x860")
        self.root.minsize(680, 640)
        self.root.configure(fg_color=COLORS["bg"])

        self.is_running = False
        self._worker_thread = None
        self._stop_flag = threading.Event()

        self.config = self._load_config()
        self._row = 0
        self._build_ui()

    # ==========================================================
    # UI 建構
    # ==========================================================
    def _build_ui(self):
        self.scrollable = ctk.CTkScrollableFrame(
            self.root, fg_color=COLORS["bg"],
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        self.scrollable.pack(fill="both", expand=True)

        self._build_header()

        self.content = ctk.CTkFrame(self.scrollable, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.content.grid_columnconfigure(1, weight=1)

        self._build_file_section()
        self._build_model_section()
        self._build_diarize_section()
        self._build_output_section()
        self._build_action_section()
        self._build_log_section()

    def _build_header(self):
        ctk.CTkLabel(
            self.scrollable,
            text="Taigi-whisper-UI",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=16, pady=(12, 2))

        ctk.CTkLabel(
            self.scrollable,
            text="faster-whisper 快速轉錄 + pyannote 講者辨識 ｜ 無需 word-align，速度更快",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkFrame(self.scrollable, fg_color=COLORS["border_light"], height=1).pack(
            fill="x", padx=0, pady=(0, 4)
        )

    # ----------------------------------------------------------
    def _build_file_section(self):
        self._section_header("音訊檔案")

        r = self._next_row()
        self._label(self.content, "選擇音訊檔案：").grid(
            row=r, column=0, sticky="e", padx=(0, 8), pady=4
        )

        field = ctk.CTkFrame(self.content, fg_color="transparent")
        field.grid(row=r, column=1, sticky="ew", pady=4)
        field.grid_columnconfigure(0, weight=1)

        self.audio_path_var = ctk.StringVar(value=self.config.get("last_audio_path", ""))
        self._entry(field, self.audio_path_var, placeholder="選擇音訊 / 影片檔案...").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._button(field, "瀏覽", self._browse_audio, width=70).grid(row=0, column=1)

        r = self._next_row()
        ctk.CTkLabel(
            self.content,
            text="支援格式：WAV, MP3, M4A, FLAC, OGG, AAC, WMA, MP4, MKV, AVI, MOV, WEBM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLORS["text_muted"],
        ).grid(row=r, column=1, sticky="w", pady=(0, 4))

    # ----------------------------------------------------------
    def _build_model_section(self):
        self._section_header("辨識設定")

        # 辨識引擎
        r = self._next_row()
        self._label(self.content, "辨識引擎：").grid(
            row=r, column=0, sticky="e", padx=(0, 8), pady=4
        )

        eng_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        eng_frame.grid(row=r, column=1, sticky="ew", pady=4)
        eng_frame.grid_columnconfigure(1, weight=1)

        self.engine_var = ctk.StringVar(value=self.config.get("engine", "faster-whisper"))
        ctk.CTkComboBox(
            eng_frame, values=["faster-whisper"] + list(BREEZE_ENGINES.keys()),
            variable=self.engine_var,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            button_color=COLORS["btn_bg"], button_hover_color=COLORS["btn_hover"],
            dropdown_fg_color=COLORS["bg_input"], dropdown_hover_color=COLORS["bg_alt"],
            dropdown_text_color=COLORS["text"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=28, corner_radius=2, border_width=1,
            state="readonly", width=220,
            command=self._on_engine_change,
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.engine_info_label = ctk.CTkLabel(
            eng_frame, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLORS["text_muted"],
        )
        self.engine_info_label.grid(row=0, column=1, sticky="w")

        self._button(eng_frame, "管理模型...", self._open_model_manager,
                     width=90, height=26).grid(row=0, column=2, padx=(8, 0))

        # 其餘參數
        self.device_var = ctk.StringVar(value=self.config.get("device", "cuda"))
        self._combo_row("執行設備：", ["cuda", "cpu"], self.device_var,
                        command=self._on_device_change)

        self.model_var = ctk.StringVar(value=self.config.get("model", "large-v3"))
        self.model_combo = self._combo_row("模型大小：", [
            "tiny", "base", "small", "medium",
            "large", "large-v1", "large-v2", "large-v3",
        ], self.model_var)

        self.language_var = ctk.StringVar(value=self.config.get("language", "繁體中文"))
        self.language_combo = self._combo_row("辨識語言：", list(LANGUAGE_MAP.keys()),
                                              self.language_var)

        self.task_var = ctk.StringVar(value=self.config.get("task", "transcribe"))
        self.task_combo = self._combo_row("任務模式：", ["transcribe", "translate"],
                                          self.task_var)

        self.compute_var = ctk.StringVar(value=self.config.get("compute_type", "float16"))
        self.compute_combo = self._combo_row("計算精度：", ["float16", "int8", "float32"],
                                             self.compute_var)

        self.batch_size_var = ctk.StringVar(value=str(self.config.get("batch_size", "16")))
        self._combo_row("Batch Size：", ["1", "2", "4", "8", "16", "24", "32"],
                        self.batch_size_var, editable=True)

        self.beam_size_var = ctk.StringVar(value=str(self.config.get("beam_size", "5")))
        self.beam_combo = self._combo_row("Beam Size：", ["1", "3", "5", "8", "10"],
                                          self.beam_size_var, editable=True)

        r = self._next_row()
        self.vad_filter_var = ctk.BooleanVar(value=self.config.get("vad_filter", True))
        self._make_checkbox(self.content, "啟用 VAD 過濾靜音",
                            self.vad_filter_var).grid(row=r, column=1, sticky="w", pady=4)

        self._on_engine_change(self.engine_var.get())

    # ----------------------------------------------------------
    def _build_diarize_section(self):
        self._section_header("講者辨識（Speaker Diarization）")

        r = self._next_row()
        self.diarize_var = ctk.BooleanVar(value=self.config.get("diarize", False))
        self.diarize_switch = ctk.CTkSwitch(
            self.content, text="啟用講者辨識",
            variable=self.diarize_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLORS["text"],
            progress_color=COLORS["accent"],
            fg_color=COLORS["border"],
            button_color="#ffffff",
            button_hover_color="#f0f0f0",
            command=self._toggle_diarize,
        )
        self.diarize_switch.grid(row=r, column=1, sticky="w", pady=4)

        r = self._next_row()
        self._diarize_row = r
        self.diarize_options = ctk.CTkFrame(self.content, fg_color="transparent")
        self.diarize_options.grid_columnconfigure(1, weight=1)

        self.min_speakers_var = ctk.StringVar(value=self.config.get("min_speakers", ""))
        self._subframe_entry_row(self.diarize_options, 0, "最少講者數：",
                                 self.min_speakers_var, placeholder="自動（可不填）")

        self.max_speakers_var = ctk.StringVar(value=self.config.get("max_speakers", ""))
        self._subframe_entry_row(self.diarize_options, 1, "最多講者數：",
                                 self.max_speakers_var, placeholder="自動（可不填）")

        self.hf_token_var = ctk.StringVar(value=self.config.get("hf_token", ""))
        self._subframe_entry_row(self.diarize_options, 2, "HuggingFace Token：",
                                 self.hf_token_var, placeholder="hf_xxxxx", show="*")

        ctk.CTkLabel(
            self.diarize_options,
            text="需要 HuggingFace Access Token，並已在 pyannote/speaker-diarization-3.1 頁面同意授權",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLORS["text_muted"],
            wraplength=500, justify="left",
        ).grid(row=3, column=1, sticky="w", pady=(0, 4))

        self._toggle_diarize()

    # ----------------------------------------------------------
    def _build_output_section(self):
        self._section_header("輸出設定")

        self.output_format_var = ctk.StringVar(value=self.config.get("output_format", "srt"))
        self._combo_row("輸出格式：", ["srt", "txt", "vtt", "json"],
                        self.output_format_var)

        self.initial_prompt_var = ctk.StringVar(value=self.config.get("initial_prompt", ""))
        self._entry_row("Initial Prompt：", self.initial_prompt_var, placeholder="（可不填）")

        self.max_line_chars_var = ctk.StringVar(value=str(self.config.get("max_line_chars", "20")))
        self._entry_row("每行最多字數：", self.max_line_chars_var, placeholder="20")

        self.auto_punct_var = ctk.StringVar(
            value=self.config.get("auto_punct", "自動（基於停頓）"))
        self._combo_row("自動加標點：", ["無", "自動（基於停頓）"], self.auto_punct_var)

        # 儲存目錄
        r = self._next_row()
        self._label(self.content, "儲存目錄：").grid(
            row=r, column=0, sticky="e", padx=(0, 8), pady=4
        )

        dir_field = ctk.CTkFrame(self.content, fg_color="transparent")
        dir_field.grid(row=r, column=1, sticky="ew", pady=4)
        dir_field.grid_columnconfigure(0, weight=1)

        self.output_dir_var = ctk.StringVar(value=self.config.get("output_dir", os.getcwd()))
        self._entry(dir_field, self.output_dir_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._button(dir_field, "選擇...", self._browse_output_dir, width=70).grid(row=0, column=1)

    # ----------------------------------------------------------
    def _build_action_section(self):
        r = self._next_row()
        bar = ctk.CTkFrame(self.content, fg_color="transparent")
        bar.grid(row=r, column=0, columnspan=2, pady=(14, 4))

        self.run_btn = ctk.CTkButton(
            bar, text="開始辨識", width=130, height=32,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            corner_radius=2,
            command=self._start,
        )
        self.run_btn.pack(side="left", padx=4)

        self.stop_btn = ctk.CTkButton(
            bar, text="停止", width=90, height=32,
            fg_color=COLORS["btn_bg"], hover_color=COLORS["btn_hover"],
            text_color=COLORS["text"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            corner_radius=2,
            command=self._stop, state="disabled",
        )
        self.stop_btn.pack(side="left", padx=4)

        # 兩段式進度
        r = self._next_row()
        phases = ctk.CTkFrame(self.content, fg_color="transparent")
        phases.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        phases.grid_columnconfigure((0, 1), weight=1, uniform="ph")

        # Phase 1
        p1 = ctk.CTkFrame(phases, fg_color=COLORS["bg_alt"], corner_radius=2,
                           border_width=1, border_color=COLORS["border_light"])
        p1.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkLabel(p1, text="階段 1：快速轉錄",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                     text_color=COLORS["phase1"]).pack(anchor="w", padx=8, pady=(6, 2))
        self.progress1 = ctk.CTkProgressBar(p1, fg_color=COLORS["border_light"],
                                             progress_color=COLORS["phase1"], height=5,
                                             corner_radius=2)
        self.progress1.pack(fill="x", padx=8, pady=(0, 2))
        self.progress1.set(0)
        self.phase1_label = ctk.CTkLabel(p1, text="等待中",
                                          font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                          text_color=COLORS["text_muted"])
        self.phase1_label.pack(pady=(0, 6))

        # Phase 2
        p2 = ctk.CTkFrame(phases, fg_color=COLORS["bg_alt"], corner_radius=2,
                           border_width=1, border_color=COLORS["border_light"])
        p2.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        ctk.CTkLabel(p2, text="階段 2：講者辨識",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                     text_color=COLORS["phase2"]).pack(anchor="w", padx=8, pady=(6, 2))
        self.progress2 = ctk.CTkProgressBar(p2, fg_color=COLORS["border_light"],
                                             progress_color=COLORS["phase2"], height=5,
                                             corner_radius=2)
        self.progress2.pack(fill="x", padx=8, pady=(0, 2))
        self.progress2.set(0)
        self.phase2_label = ctk.CTkLabel(p2, text="等待中",
                                          font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                          text_color=COLORS["text_muted"])
        self.phase2_label.pack(pady=(0, 6))

        r = self._next_row()
        self.status_label = ctk.CTkLabel(
            self.content, text="就緒",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLORS["text_secondary"],
        )
        self.status_label.grid(row=r, column=0, columnspan=2, pady=(4, 6))

    # ----------------------------------------------------------
    def _build_log_section(self):
        self._section_header("執行日誌")

        r = self._next_row()
        self.log_box = ctk.CTkTextbox(
            self.content, height=200,
            fg_color=COLORS["bg_input"], text_color=COLORS["text"],
            font=ctk.CTkFont(family=FONT_FAMILY_MONO, size=13),
            border_color=COLORS["border"], border_width=1, corner_radius=2,
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        self.log_box.grid(row=r, column=0, columnspan=2, sticky="ew", pady=4)

        r = self._next_row()
        btn_row = ctk.CTkFrame(self.content, fg_color="transparent")
        btn_row.grid(row=r, column=0, columnspan=2, sticky="e", pady=(4, 10))

        self._button(btn_row, "清除日誌",
                     lambda: self.log_box.delete("1.0", "end"),
                     width=80, height=26).pack(side="right", padx=4)
        self._button(btn_row, "開啟輸出資料夾", self._open_output_dir,
                     width=120, height=26).pack(side="right", padx=4)

    # ==========================================================
    # 元件工廠
    # ==========================================================
    def _next_row(self):
        r = self._row
        self._row += 1
        return r

    def _section_header(self, text):
        r = self._next_row()
        ctk.CTkLabel(
            self.content, text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(12, 2))

        r = self._next_row()
        ctk.CTkFrame(self.content, fg_color=COLORS["border_light"], height=1).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )

    def _label(self, parent, text):
        return ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLORS["text"],
        )

    def _entry(self, parent, var, placeholder="", show=None):
        kwargs = {}
        if show:
            kwargs["show"] = show
        return ctk.CTkEntry(
            parent, textvariable=var, placeholder_text=placeholder,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            height=28, corner_radius=2, border_width=1,
            **kwargs,
        )

    def _button(self, parent, text, command, width=80, height=28):
        return ctk.CTkButton(
            parent, text=text, width=width, height=height,
            fg_color=COLORS["btn_bg"], hover_color=COLORS["btn_hover"],
            text_color=COLORS["text"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            corner_radius=2,
            command=command,
        )

    def _combo_row(self, label, values, var, editable=False, command=None):
        r = self._next_row()
        self._label(self.content, label).grid(
            row=r, column=0, sticky="e", padx=(0, 8), pady=4
        )
        combo = ctk.CTkComboBox(
            self.content, values=values, variable=var,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            button_color=COLORS["btn_bg"], button_hover_color=COLORS["btn_hover"],
            dropdown_fg_color=COLORS["bg_input"],
            dropdown_hover_color=COLORS["bg_alt"],
            dropdown_text_color=COLORS["text"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            dropdown_font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            height=28, corner_radius=2, border_width=1,
            state="normal" if editable else "readonly",
            command=command,
        )
        combo.grid(row=r, column=1, sticky="ew", pady=4)
        return combo

    def _entry_row(self, label, var, placeholder="", show=None):
        r = self._next_row()
        self._label(self.content, label).grid(
            row=r, column=0, sticky="e", padx=(0, 8), pady=4
        )
        self._entry(self.content, var, placeholder=placeholder, show=show).grid(
            row=r, column=1, sticky="ew", pady=4
        )

    def _subframe_entry_row(self, parent, row, label, var, placeholder="", show=None):
        self._label(parent, label).grid(row=row, column=0, sticky="e", padx=(0, 8), pady=3)
        self._entry(parent, var, placeholder=placeholder, show=show).grid(
            row=row, column=1, sticky="ew", pady=3
        )

    def _make_checkbox(self, parent, text, var):
        return ctk.CTkCheckBox(
            parent, text=text, variable=var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLORS["text"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#ffffff",
            corner_radius=2, border_width=1,
            checkbox_width=16, checkbox_height=16,
        )

    # ==========================================================
    # 互動邏輯
    # ==========================================================
    def _browse_audio(self):
        path = filedialog.askopenfilename(
            title="選擇音訊 / 影片檔案",
            filetypes=(
                ("音訊/影片", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.wma "
                             "*.mp4 *.mkv *.avi *.mov *.webm"),
                ("所有檔案", "*.*"),
            ),
        )
        if path:
            self.audio_path_var.set(path)
            self._log(f"已選擇：{path}")
            auto_dir = os.path.dirname(path)
            if auto_dir:
                self.output_dir_var.set(auto_dir)

    def _browse_output_dir(self):
        d = filedialog.askdirectory(title="選擇輸出目錄")
        if d:
            self.output_dir_var.set(d)

    def _toggle_diarize(self):
        if self.diarize_var.get():
            self.diarize_options.grid(
                row=self._diarize_row, column=0, columnspan=2, sticky="ew", pady=(0, 4)
            )
        else:
            self.diarize_options.grid_forget()

    def _on_device_change(self, choice=None):
        if self.device_var.get() == "cuda":
            self.compute_combo.configure(values=["float16", "int8", "float32"])
            if self.compute_var.get() not in ("float16", "int8", "float32"):
                self.compute_var.set("float16")
        else:
            self.compute_combo.configure(values=["float32", "int8"])
            if self.compute_var.get() not in ("float32", "int8"):
                self.compute_var.set("float32")

    def _on_engine_change(self, choice=None):
        engine = self.engine_var.get()
        breeze = BREEZE_ENGINES.get(engine)
        is_breeze = breeze is not None
        for combo in (self.model_combo, self.beam_combo, self.task_combo):
            combo.configure(state="disabled" if is_breeze else "readonly")
        if is_breeze:
            self.language_var.set(breeze["default_lang"])
            self.language_combo.configure(
                state="disabled" if breeze["lock_lang"] else "readonly")
            self.engine_info_label.configure(text=breeze["info"])
        else:
            self.language_combo.configure(state="readonly")
            if self.language_var.get() == "台語 (Taigi)":
                self.language_var.set("繁體中文")
            self.engine_info_label.configure(text="")

    def _open_output_dir(self):
        d = self.output_dir_var.get()
        if os.path.isdir(d):
            os.startfile(d)
        else:
            messagebox.showwarning("警告", f"目錄不存在：{d}")

    def _open_model_manager(self):
        """彈出模型管理視窗：列出 HuggingFace 快取中已下載的模型並提供刪除"""
        if self.is_running:
            messagebox.showwarning("無法操作", "請先停止當前辨識作業")
            return
        try:
            from huggingface_hub import scan_cache_dir
            from huggingface_hub import constants as hf_consts
        except ImportError:
            messagebox.showerror(
                "缺少套件",
                "找不到 huggingface_hub 套件。\n"
                f"請執行：{os.path.join(os.path.dirname(PYTHON_EXEC), 'pip.exe')} install huggingface_hub")
            return

        cache_path = getattr(hf_consts, "HF_HUB_CACHE", None) \
            or getattr(hf_consts, "HUGGINGFACE_HUB_CACHE", "")

        win = ctk.CTkToplevel(self.root)
        win.title("已安裝的模型")
        win.geometry("720x520")
        win.configure(fg_color=COLORS["bg"])
        win.transient(self.root)

        header = ctk.CTkFrame(win, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            header, text=f"快取路徑：{cache_path}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLORS["text_muted"],
            anchor="w", justify="left", wraplength=680,
        ).pack(anchor="w", fill="x")

        total_label = ctk.CTkLabel(
            header, text="掃描中...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLORS["text"],
        )
        total_label.pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(win, fg_color=COLORS["border_light"], height=1).pack(
            fill="x", padx=0, pady=4)

        list_frame = ctk.CTkScrollableFrame(
            win, fg_color=COLORS["bg"],
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent"])
        list_frame.pack(fill="both", expand=True, padx=12, pady=4)

        bar = ctk.CTkFrame(win, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(4, 12))

        def _human(n):
            n = float(n)
            for u in ("B", "KB", "MB", "GB", "TB"):
                if n < 1024.0:
                    return f"{n:.1f} {u}"
                n /= 1024.0
            return f"{n:.1f} PB"

        def _refresh():
            for w in list_frame.winfo_children():
                w.destroy()
            try:
                info = scan_cache_dir()
            except Exception as e:
                total_label.configure(text="掃描失敗", text_color=COLORS["error"])
                ctk.CTkLabel(
                    list_frame, text=f"錯誤：{e}",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                    text_color=COLORS["error"], wraplength=660, justify="left",
                ).pack(anchor="w", padx=8, pady=8)
                return

            repos = sorted(info.repos, key=lambda r: -r.size_on_disk)
            total_label.configure(
                text=f"總計：{_human(info.size_on_disk)}  ·  {len(repos)} 個模型",
                text_color=COLORS["text"])

            if not repos:
                ctk.CTkLabel(
                    list_frame, text="（快取中沒有模型）",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                    text_color=COLORS["text_muted"],
                ).pack(anchor="w", padx=8, pady=16)
                return

            for repo in repos:
                row = ctk.CTkFrame(
                    list_frame, fg_color=COLORS["bg_input"],
                    border_color=COLORS["border_light"], border_width=1,
                    corner_radius=2)
                row.pack(fill="x", pady=3, padx=2)
                row.grid_columnconfigure(0, weight=1)

                info_col = ctk.CTkFrame(row, fg_color="transparent")
                info_col.grid(row=0, column=0, sticky="ew", padx=10, pady=6)

                ctk.CTkLabel(
                    info_col, text=repo.repo_id,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                    text_color=COLORS["text"], anchor="w",
                ).pack(anchor="w", fill="x")

                last = datetime.fromtimestamp(repo.last_accessed).strftime("%Y-%m-%d")
                meta = f"{_human(repo.size_on_disk)}  ·  {repo.repo_type}  ·  最後使用 {last}"
                ctk.CTkLabel(
                    info_col, text=meta,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                    text_color=COLORS["text_muted"], anchor="w",
                ).pack(anchor="w", fill="x")

                def _make_delete(r):
                    def _do():
                        if not messagebox.askyesno(
                                "確認刪除",
                                f"確定要刪除此模型嗎？此動作無法復原。\n\n"
                                f"{r.repo_id}\n{_human(r.size_on_disk)}"):
                            return
                        try:
                            import shutil
                            shutil.rmtree(r.repo_path)
                            self._log(f"已刪除模型：{r.repo_id} ({_human(r.size_on_disk)})")
                            _refresh()
                        except Exception as e:
                            messagebox.showerror("刪除失敗", str(e))
                    return _do

                ctk.CTkButton(
                    row, text="刪除", width=70, height=28,
                    fg_color=COLORS["btn_bg"], hover_color="#f5d0cc",
                    text_color=COLORS["error"],
                    border_color=COLORS["border"], border_width=1,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                    corner_radius=2,
                    command=_make_delete(repo),
                ).grid(row=0, column=1, padx=(0, 10), pady=8)

        def _open_cache():
            if cache_path and os.path.isdir(cache_path):
                os.startfile(cache_path)
            else:
                messagebox.showwarning("警告", f"快取資料夾不存在：{cache_path}")

        self._button(bar, "關閉", win.destroy, width=70).pack(side="left", padx=2)
        self._button(bar, "重新整理", _refresh, width=90).pack(side="right", padx=2)
        self._button(bar, "開啟快取資料夾", _open_cache, width=130).pack(side="right", padx=2)

        _refresh()

    # ==========================================================
    # 核心邏輯
    # ==========================================================
    def _start(self):
        if self.is_running:
            return

        audio = self.audio_path_var.get().strip()
        if not audio:
            messagebox.showerror("輸入錯誤", "請先選擇音訊檔案！")
            return
        if not os.path.exists(audio):
            messagebox.showerror("輸入錯誤", f"檔案不存在：{audio}")
            return

        self._save_config()
        self._set_running(True)
        self._stop_flag.clear()

        self._log("=" * 60)
        self._log(f"開始辨識 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"檔案：{audio}")
        self._log("=" * 60)

        self._worker_thread = threading.Thread(target=self._pipeline, daemon=True)
        self._worker_thread.start()

    def _stop(self):
        self._stop_flag.set()
        self._log("使用者要求停止，將在當前步驟結束後中斷...")
        self.status_label.configure(text="停止中...", text_color=COLORS["warning"])

    def _pipeline(self):
        """主要辨識流程（在背景執行緒中執行）"""
        start_time = time.time()
        audio = self.audio_path_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        os.makedirs(output_dir, exist_ok=True)

        try:
            # ==================================================
            # 動態 import
            # ==================================================
            import torch

            engine = self.engine_var.get()
            device = self.device_var.get()
            compute = self.compute_var.get()

            # ==================================================
            # 階段 1：語音轉錄
            # ==================================================
            self._update_phase(1, "indeterminate", "載入模型...")

            # 檢查 GPU 可用性（兩種引擎共用）
            if device == "cuda":
                if torch.cuda.is_available():
                    self._log(f"CUDA 可用：{torch.cuda.get_device_name(0)}")
                else:
                    self._log("CUDA 不可用，改用 CPU（會非常慢）")
                    device = "cpu"
                    if compute == "float16":
                        compute = "int8"

            # --------------------------------------------------
            breeze_cfg = BREEZE_ENGINES.get(engine)
            if breeze_cfg is not None:
                # ── Breeze-ASR：使用 transformers pipeline ──
                model_id = breeze_cfg["model_id"]
                _ensure_transformers(self._log)

                from transformers import pipeline as hf_pipeline

                device_id = 0 if device == "cuda" else -1
                torch_dtype = (torch.float16
                               if (compute == "float16" and device_id == 0)
                               else torch.float32)

                self._log(f"[1/2] 載入模型：{model_id}  "
                          f"設備：{device}  精度：{torch_dtype}")
                pipe = hf_pipeline(
                    "automatic-speech-recognition",
                    model=model_id,
                    device=device_id,
                    torch_dtype=torch_dtype,
                )

                if self._stop_flag.is_set():
                    raise InterruptedError("使用者停止")

                self._update_phase(1, "indeterminate", "載入音訊...")
                self._log("[1/2] 用 ffmpeg 解碼音訊...")
                import subprocess
                import numpy as np
                sample_rate = 16000
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", audio,
                    "-f", "f32le",
                    "-acodec", "pcm_f32le",
                    "-ar", str(sample_rate),
                    "-ac", "1",
                    "-",
                ]
                proc = subprocess.run(
                    ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if proc.returncode != 0:
                    err_msg = proc.stderr.decode("utf-8", errors="replace")
                    raise RuntimeError(f"ffmpeg 解碼失敗：\n{err_msg}")
                audio_np = np.frombuffer(proc.stdout, dtype=np.float32).copy()
                duration_sec = len(audio_np) / sample_rate
                self._log(f"[1/2] 音訊長度：{duration_sec:.1f}s")

                self._update_phase(1, "indeterminate", "VAD 切段中...")
                self._log("[1/2] 執行 silero-VAD 切段...")
                from faster_whisper.vad import get_speech_timestamps, VadOptions

                vad_opts = VadOptions(
                    threshold=0.5,
                    min_speech_duration_ms=400,
                    max_speech_duration_s=25.0,
                    min_silence_duration_ms=1000,
                    speech_pad_ms=300,
                )
                speech_chunks = get_speech_timestamps(
                    audio_np, vad_options=vad_opts, sampling_rate=sample_rate
                )
                if not speech_chunks:
                    raise RuntimeError("VAD 沒有偵測到任何語音段，請檢查音訊。")
                total_chunks = len(speech_chunks)
                self._log(f"[1/2] VAD 偵測到 {total_chunks} 段語音，開始逐段轉錄...")
                self._update_phase(1, 0.0, f"轉錄 0/{total_chunks} 段")

                segments = []
                t0 = time.time()
                for idx, ch in enumerate(speech_chunks):
                    if self._stop_flag.is_set():
                        raise InterruptedError("使用者停止")
                    s_sample, e_sample = int(ch["start"]), int(ch["end"])
                    start_sec = s_sample / sample_rate
                    end_sec = e_sample / sample_rate
                    clip = audio_np[s_sample:e_sample]
                    if len(clip) < int(0.1 * sample_rate):
                        continue
                    try:
                        out = pipe({"raw": clip, "sampling_rate": sample_rate})
                        text = (out.get("text", "").strip()
                                if isinstance(out, dict) else str(out).strip())
                    except Exception as e:
                        self._log(f"  第 {idx+1} 段轉錄失敗：{e}")
                        text = ""
                    pct = (idx + 1) / total_chunks
                    self._update_phase(1, pct,
                        f"{idx+1}/{total_chunks} 段 ({pct*100:.0f}%)")
                    if not text:
                        continue
                    segments.append(_TextSegment(start_sec, end_sec, text))
                    self._log(
                        f"  [{_fmt_time(start_sec)} → {_fmt_time(end_sec)}] {text}")

                t1 = time.time()
                self._log(f"[1/2] 轉錄完成，共 {len(segments)} 段，耗時 {t1-t0:.1f}s")
                self._update_phase(1, 1.0, f"完成 {len(segments)} 段")

                del pipe
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            else:
                # ── faster-whisper 路徑（原有邏輯）────────────
                self._log("載入 faster-whisper 模組...")
                from faster_whisper import WhisperModel

                model_name = self.model_var.get()
                beam_size = int(self.beam_size_var.get())
                lang_display = self.language_var.get().strip()
                lang_code, needs_s2t = LANGUAGE_MAP.get(lang_display, (None, False))
                task = self.task_var.get()
                vad_filter = self.vad_filter_var.get()
                initial_prompt = self.initial_prompt_var.get().strip() or None

                self._log(f"[1/2] 載入模型：{model_name}  設備：{device}  精度：{compute}")
                model = WhisperModel(model_name, device=device, compute_type=compute)

                if self._stop_flag.is_set():
                    raise InterruptedError("使用者停止")

                self._update_phase(1, "indeterminate", "轉錄中...")
                self._log(f"[1/2] 開始轉錄，語言：{lang_display}  beam_size={beam_size}"
                          + ("  (將進行簡→繁轉換)" if needs_s2t else ""))

                t0 = time.time()
                segments_gen, info = model.transcribe(
                    audio,
                    language=lang_code,
                    task=task,
                    beam_size=beam_size,
                    vad_filter=vad_filter,
                    initial_prompt=initial_prompt,
                    word_timestamps=False,
                )

                cc = None
                if needs_s2t:
                    try:
                        from opencc import OpenCC
                        cc = OpenCC("s2t")
                    except Exception as e:
                        self._log(f"OpenCC 載入失敗，跳過簡繁轉換：{e}")
                        cc = None

                segments = []
                duration = info.duration if info.duration > 0 else 1.0

                for seg in segments_gen:
                    if self._stop_flag.is_set():
                        raise InterruptedError("使用者停止")
                    if cc is not None:
                        try:
                            seg.text = cc.convert(seg.text)
                        except AttributeError:
                            seg = _TextSegment(seg.start, seg.end, cc.convert(seg.text))
                    segments.append(seg)
                    pct = min(seg.end / duration, 1.0)
                    self._update_phase(1, pct,
                        f"{seg.end:.1f}s / {duration:.1f}s  ({pct*100:.0f}%)")
                    self._log(
                        f"  [{_fmt_time(seg.start)} → {_fmt_time(seg.end)}] {seg.text.strip()}")

                t1 = time.time()
                self._log(f"[1/2] 轉錄完成，共 {len(segments)} 段，耗時 {t1-t0:.1f}s")
                self._update_phase(1, 1.0, f"完成 {len(segments)} 段")

                del model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            if self._stop_flag.is_set():
                raise InterruptedError("使用者停止")

            # ==================================================
            # 階段 2：pyannote 講者辨識（可選）
            # ==================================================
            speaker_map = None

            if self.diarize_var.get():
                hf_token = self.hf_token_var.get().strip()
                if not hf_token:
                    self._log("未輸入 HuggingFace Token，跳過講者辨識")
                    self._update_phase(2, 0, "已跳過（未設定 Token）")
                else:
                    # ----------------------------------------
                    # 2a. 預先載入音訊（只解碼一次，避免 MP3 反覆重讀）
                    # ----------------------------------------
                    self._update_phase(2, "indeterminate", "載入音訊...")
                    self._log("[2/2] 預先載入音訊為 tensor（避免 MP3 反覆解碼）...")

                    import subprocess
                    import numpy as np
                    t_load0 = time.time()
                    sample_rate = 16000
                    ffmpeg_diar = [
                        "ffmpeg", "-y",
                        "-i", audio,
                        "-f", "f32le",
                        "-acodec", "pcm_f32le",
                        "-ar", str(sample_rate),
                        "-ac", "1",
                        "-",
                    ]
                    proc2 = subprocess.run(
                        ffmpeg_diar, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if proc2.returncode != 0:
                        err_msg = proc2.stderr.decode("utf-8", errors="replace")
                        raise RuntimeError(f"ffmpeg 解碼失敗（diarize）：\n{err_msg}")
                    audio_np2 = np.frombuffer(proc2.stdout, dtype=np.float32).copy()
                    waveform = torch.from_numpy(audio_np2).unsqueeze(0)
                    self._log(f"[2/2] 音訊載入完成：{waveform.shape[1]/sample_rate:.1f}s "
                              f"@ {sample_rate}Hz，耗時 {time.time()-t_load0:.1f}s")

                    # ----------------------------------------
                    # 2b. 載入 pyannote 模型
                    # ----------------------------------------
                    self._log("[2/2] 載入 pyannote 講者辨識模型...")
                    self._update_phase(2, "indeterminate", "載入模型...")

                    from pyannote.audio import Pipeline

                    pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=hf_token,
                    )

                    if pipeline is None:
                        raise RuntimeError(
                            "pyannote 模型載入失敗。請確認：\n"
                            "1. HuggingFace Token 正確\n"
                            "2. 已在 pyannote/speaker-diarization-3.1 頁面同意授權\n"
                            "3. 已在 pyannote/segmentation-3.0 頁面同意授權"
                        )

                    use_gpu = torch.cuda.is_available() and device == "cuda"
                    target_device = torch.device("cuda" if use_gpu else "cpu")
                    pipeline = pipeline.to(target_device)
                    self._log(f"[2/2] pyannote 使用 {'GPU: ' + torch.cuda.get_device_name(0) if use_gpu else 'CPU'}")

                    if self._stop_flag.is_set():
                        raise InterruptedError("使用者停止")

                    # ----------------------------------------
                    # 2c. 執行講者辨識（含進度回報）
                    # ----------------------------------------
                    self._log("[2/2] 執行講者辨識（含即時進度）...")

                    diarize_kwargs = {}
                    min_sp = self.min_speakers_var.get().strip()
                    max_sp = self.max_speakers_var.get().strip()
                    if min_sp:
                        diarize_kwargs["min_speakers"] = int(min_sp)
                    if max_sp:
                        diarize_kwargs["max_speakers"] = int(max_sp)

                    hook = _make_gui_hook(
                        log_fn=self._log,
                        progress_fn=lambda pct, txt: self._update_phase(2, pct, txt),
                        stop_flag=self._stop_flag,
                    )

                    t2 = time.time()
                    diarization = pipeline(
                        {"waveform": waveform, "sample_rate": sample_rate},
                        hook=hook,
                        **diarize_kwargs,
                    )
                    t3 = time.time()
                    self._log(f"[2/2] 講者辨識完成，耗時 {t3-t2:.1f}s")

                    speaker_map = _assign_speakers(segments, diarization)
                    speakers = set(speaker_map.values())
                    self._log(f"[2/2] 偵測到 {len(speakers)} 位講者：{', '.join(sorted(speakers))}")
                    self._update_phase(2, 1.0, f"完成，{len(speakers)} 位講者")
            else:
                self._update_phase(2, 0, "未啟用")

            # ==================================================
            # 後處理：合併相鄰同講者短段 + 自動加標點
            # ==================================================
            try:
                max_chars = int((self.max_line_chars_var.get() or "20").strip())
                max_chars = max(10, min(max_chars, 500))
            except Exception:
                max_chars = 20

            auto_punct_on = self.auto_punct_var.get() == "自動（基於停頓）"

            before = len(segments)
            segments, speaker_map = _merge_adjacent_segments(
                segments, speaker_map,
                max_gap=1.5, max_duration=25.0, max_chars=max_chars,
                comma_gap_threshold=(0.6 if auto_punct_on else None),
            )
            after_merge = len(segments)

            segments, speaker_map = _split_long_segments(
                segments, speaker_map, max_chars=max_chars,
            )
            after_split = len(segments)

            if after_split != before:
                self._log(f"後處理：合併→切分 {before} → {after_merge} → {after_split} 段"
                          f"（每行上限 {max_chars} 字）")

            if auto_punct_on:
                _apply_sentence_period(segments)
                self._log("後處理：已自動補上標點符號（停頓 → 逗號、段末 → 句號）")

            # ==================================================
            # 寫出結果
            # ==================================================
            base = os.path.splitext(os.path.basename(audio))[0]
            fmt = self.output_format_var.get()
            out_path = os.path.join(output_dir, f"{base}.{fmt}")

            _write_output(out_path, fmt, segments, speaker_map)

            elapsed = time.time() - start_time
            self._log(f"\n完成！輸出：{out_path}")
            self._log(f"   總耗時：{elapsed:.1f}s")
            self.root.after(0, lambda: self.status_label.configure(
                text=f"完成 — 耗時 {elapsed:.1f}s", text_color=COLORS["success"]))
            self.root.after(0, lambda: messagebox.showinfo(
                "完成", f"辨識完成！耗時 {elapsed:.1f} 秒\n輸出：{out_path}"))

        except InterruptedError as e:
            self._log(f"\n{e}")
            self.root.after(0, lambda: self.status_label.configure(
                text="已停止", text_color=COLORS["warning"]))
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            self._log(f"\n發生錯誤：{e}")
            self._log(err)
            self.root.after(0, lambda: self.status_label.configure(
                text="錯誤", text_color=COLORS["error"]))
            self.root.after(0, lambda: messagebox.showerror("錯誤", str(e)))
        finally:
            self.root.after(0, lambda: self._set_running(False))

    def _update_phase(self, phase: int, value, label_text: str):
        def _do():
            if phase == 1:
                bar, lbl = self.progress1, self.phase1_label
            else:
                bar, lbl = self.progress2, self.phase2_label

            if value == "indeterminate":
                bar.configure(mode="indeterminate")
                bar.start()
            else:
                bar.stop()
                bar.configure(mode="determinate")
                bar.set(float(value))
            lbl.configure(text=label_text)

        self.root.after(0, _do)

    def _set_running(self, running: bool):
        self.is_running = running
        self.run_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")
        if running:
            self.status_label.configure(text="辨識中...", text_color=COLORS["accent"])

    # ==========================================================
    # 日誌
    # ==========================================================
    def _log(self, msg: str):
        self.root.after(0, self._insert_log, msg)

    def _insert_log(self, msg: str):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    # ==========================================================
    # 設定 I/O
    # ==========================================================
    def _save_config(self):
        cfg = {
            "last_audio_path": self.audio_path_var.get(),
            "engine": self.engine_var.get(),
            "device": self.device_var.get(),
            "model": self.model_var.get(),
            "language": self.language_var.get(),
            "task": self.task_var.get(),
            "compute_type": self.compute_var.get(),
            "batch_size": self.batch_size_var.get(),
            "beam_size": self.beam_size_var.get(),
            "vad_filter": self.vad_filter_var.get(),
            "output_format": self.output_format_var.get(),
            "output_dir": self.output_dir_var.get(),
            "initial_prompt": self.initial_prompt_var.get(),
            "diarize": self.diarize_var.get(),
            "min_speakers": self.min_speakers_var.get(),
            "max_speakers": self.max_speakers_var.get(),
            "hf_token": self.hf_token_var.get(),
            "max_line_chars": self.max_line_chars_var.get(),
            "auto_punct": self.auto_punct_var.get(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_config(self) -> dict:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def run(self):
        self.root.mainloop()


# ==============================================================
# 工具函數
# ==============================================================

class _TextSegment:
    """faster-whisper segment 的替代品（因為原 namedtuple 不可變）"""
    __slots__ = ("start", "end", "text")
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


def _make_gui_hook(log_fn, progress_fn, stop_flag):
    """建立 pyannote 進度 hook，將進度轉發到 GUI"""
    state = {"last_step": None, "last_pct": -1.0}

    def hook(step_name, step_artifact=None, file=None, total=None, completed=None):
        if stop_flag.is_set():
            raise InterruptedError("使用者停止")

        if step_name != state["last_step"]:
            state["last_step"] = step_name
            state["last_pct"] = -1.0
            log_fn(f"  [diarize] >>> {step_name}")

        if total is not None and completed is not None and total > 0:
            pct = completed / total
            int_pct = int(pct * 100)
            if int_pct != int(state["last_pct"] * 100):
                state["last_pct"] = pct
                progress_fn(pct, f"{step_name} {int_pct}%")
                if int_pct % 10 == 0 and int_pct > 0:
                    log_fn(f"  [diarize] {step_name}: {int_pct}% ({completed}/{total})")
        else:
            progress_fn("indeterminate", step_name)
    return hook


def _fmt_time(seconds: float, use_comma=True) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    sep = "," if use_comma else "."
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


_PUNCT_ENDERS = "，。？！；：,.?!;:"


def _merge_adjacent_segments(segments, speaker_map,
                              max_gap: float = 1.5,
                              max_duration: float = 25.0,
                              max_chars: int = 60,
                              comma_gap_threshold=None):
    if not segments:
        return segments, speaker_map

    has_spk = speaker_map is not None
    out_segs = []
    out_map = {} if has_spk else None

    def _emit(seg, spk):
        idx = len(out_segs)
        out_segs.append(seg)
        if has_spk:
            out_map[idx] = spk

    def _join(a_text: str, b_text: str, gap: float) -> str:
        a = a_text.rstrip()
        b = b_text.lstrip()
        if a and a[-1] in _PUNCT_ENDERS:
            return a + b
        if comma_gap_threshold is not None and gap >= comma_gap_threshold:
            return a + "，" + b
        return a + b

    cur = _TextSegment(segments[0].start, segments[0].end, segments[0].text)
    cur_spk = speaker_map.get(0, "UNKNOWN") if has_spk else None

    for i in range(1, len(segments)):
        s = segments[i]
        spk = speaker_map.get(i, "UNKNOWN") if has_spk else None
        gap = s.start - cur.end
        new_duration = s.end - cur.start
        new_chars = len(cur.text) + 1 + len(s.text)

        can_merge = (gap <= max_gap
                     and new_duration <= max_duration
                     and new_chars <= max_chars
                     and (not has_spk or spk == cur_spk))

        if can_merge:
            cur = _TextSegment(cur.start, s.end,
                               _join(cur.text, s.text, gap))
        else:
            _emit(cur, cur_spk)
            cur = _TextSegment(s.start, s.end, s.text)
            cur_spk = spk

    _emit(cur, cur_spk)
    return out_segs, out_map


def _split_long_segments(segments, speaker_map, max_chars: int):
    if not segments or max_chars <= 0:
        return segments, speaker_map

    PUNCT_STRONG = set("。？！；!?;")
    PUNCT_WEAK   = set("，、,")
    WHITESPACE   = set(" \t")

    def _find_cut(text: str, limit: int) -> int:
        n = min(limit, len(text))
        for i in range(n - 1, max(n // 2, 0), -1):
            if text[i] in PUNCT_STRONG:
                return i + 1
        for i in range(n - 1, max(n // 2, 0), -1):
            if text[i] in PUNCT_WEAK:
                return i + 1
        for i in range(n - 1, max(n // 2, 0), -1):
            if text[i] in WHITESPACE:
                return i + 1
        return n

    has_spk = speaker_map is not None
    out_segs = []
    out_map = {} if has_spk else None

    for i, seg in enumerate(segments):
        spk = speaker_map.get(i, "UNKNOWN") if has_spk else None
        text = seg.text.strip()
        if len(text) <= max_chars:
            idx = len(out_segs)
            out_segs.append(_TextSegment(seg.start, seg.end, text))
            if has_spk:
                out_map[idx] = spk
            continue

        parts = []
        cursor = 0
        while cursor < len(text):
            remaining = text[cursor:]
            if len(remaining) <= max_chars:
                parts.append(remaining.strip())
                break
            cut = _find_cut(remaining, max_chars)
            parts.append(remaining[:cut].strip())
            cursor += cut

        parts = [p for p in parts if p]
        if not parts:
            idx = len(out_segs)
            out_segs.append(_TextSegment(seg.start, seg.end, text))
            if has_spk:
                out_map[idx] = spk
            continue

        total_chars = sum(len(p) for p in parts)
        duration = max(seg.end - seg.start, 0.001)
        t = seg.start
        for k, p in enumerate(parts):
            if k == len(parts) - 1:
                p_end = seg.end
            else:
                frac = len(p) / total_chars
                p_end = t + duration * frac
            idx = len(out_segs)
            out_segs.append(_TextSegment(t, p_end, p))
            if has_spk:
                out_map[idx] = spk
            t = p_end

    return out_segs, out_map


def _apply_sentence_period(segments):
    for seg in segments:
        t = seg.text.strip()
        if not t:
            continue
        if t[-1] not in _PUNCT_ENDERS:
            t = t + "。"
        seg.text = t
    return segments


def _assign_speakers(segments, diarization) -> dict:
    result = {}
    for i, seg in enumerate(segments):
        speaker_times = {}
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            overlap_start = max(seg.start, turn.start)
            overlap_end = min(seg.end, turn.end)
            if overlap_end > overlap_start:
                overlap = overlap_end - overlap_start
                speaker_times[speaker] = speaker_times.get(speaker, 0) + overlap
        result[i] = max(speaker_times, key=speaker_times.get) if speaker_times else "UNKNOWN"
    return result


def _write_output(out_path: str, fmt: str, segments, speaker_map):
    with open(out_path, "w", encoding="utf-8") as f:
        if fmt == "srt":
            for i, seg in enumerate(segments):
                speaker = f"[{speaker_map[i]}] " if speaker_map else ""
                f.write(f"{i+1}\n")
                f.write(f"{_fmt_time(seg.start)} --> {_fmt_time(seg.end)}\n")
                f.write(f"{speaker}{seg.text.strip()}\n\n")

        elif fmt == "vtt":
            f.write("WEBVTT\n\n")
            for i, seg in enumerate(segments):
                speaker = f"[{speaker_map[i]}] " if speaker_map else ""
                f.write(f"{_fmt_time(seg.start, use_comma=False)} --> "
                        f"{_fmt_time(seg.end, use_comma=False)}\n")
                f.write(f"{speaker}{seg.text.strip()}\n\n")

        elif fmt == "txt":
            current_speaker = None
            for i, seg in enumerate(segments):
                if speaker_map:
                    spk = speaker_map[i]
                    if spk != current_speaker:
                        current_speaker = spk
                        f.write(f"\n[{spk}]\n")
                f.write(seg.text.strip() + "\n")

        elif fmt == "json":
            import json as _json
            data = []
            for i, seg in enumerate(segments):
                entry = {
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text.strip(),
                }
                if speaker_map:
                    entry["speaker"] = speaker_map[i]
                data.append(entry)
            _json.dump(data, f, ensure_ascii=False, indent=2)


# ==============================================================
if __name__ == "__main__":
    try:
        app = HybridWhisperGUI()
        app.run()
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox as mb
            _r = tk.Tk(); _r.withdraw()
            mb.showerror("Taigi-whisper-UI 啟動失敗",
                         f"錯誤：{e}\n\n{err}")
            _r.destroy()
        except Exception:
            pass
        print(err)
        input("\n按 Enter 關閉...")
