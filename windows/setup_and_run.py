"""
首次啟動安裝程式 - 只使用 Python 標準函式庫
檢查並安裝所有必要套件、自動下載 FFmpeg，安裝完成後啟動主程式
"""
import os
import sys
import shutil
import subprocess
import threading
import urllib.request
import zipfile
import tkinter as tk
from tkinter import ttk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, "venv", "Scripts", "python.exe")
VENV_PIP = os.path.join(SCRIPT_DIR, "venv", "Scripts", "pip.exe")
INSTALLED_MARKER = os.path.join(SCRIPT_DIR, ".installed")
REQUIREMENTS = os.path.join(SCRIPT_DIR, "requirements.txt")
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "taigi_whisper_gui.py")

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_DIR = os.path.join(SCRIPT_DIR, "ffmpeg")
FFMPEG_BIN = os.path.join(FFMPEG_DIR, "bin")
LOCAL_FFMPEG_EXE = os.path.join(FFMPEG_BIN, "ffmpeg.exe")

PACKAGES = [
    "customtkinter",
    "faster-whisper",
    "transformers",
    "accelerate",
    "numpy",
    "pyannote.audio",
    "opencc-python-reimplemented",
    "huggingface_hub",
]


def detect_gpu():
    try:
        result = subprocess.run(
            ["nvidia-smi"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def detect_system_ffmpeg():
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def has_local_ffmpeg():
    return os.path.exists(LOCAL_FFMPEG_EXE)


def build_env_with_ffmpeg():
    env = os.environ.copy()
    if has_local_ffmpeg():
        env["PATH"] = FFMPEG_BIN + os.pathsep + env.get("PATH", "")
    return env


class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Taigi-whisper-UI - 首次安裝")
        self.root.geometry("720x560")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._cancelled = False

        title = tk.Label(
            root,
            text="Taigi-whisper-UI 首次安裝",
            font=("Microsoft JhengHei", 16, "bold"),
        )
        title.pack(pady=(16, 4))

        subtitle = tk.Label(
            root,
            text="正在自動安裝所有必要元件，請稍候。首次安裝可能需要 5-20 分鐘（視網路速度）",
            font=("Microsoft JhengHei", 10),
            fg="#555555",
        )
        subtitle.pack(pady=(0, 12))

        frame = tk.Frame(root)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.log = tk.Text(
            frame,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            wrap="word",
            state="disabled",
        )
        scrollbar = ttk.Scrollbar(frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        self.progress = ttk.Progressbar(root, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=16, pady=(0, 4))

        self.status_label = tk.Label(
            root, text="準備中...", font=("Microsoft JhengHei", 9), fg="#333333"
        )
        self.status_label.pack(pady=(0, 12))

        threading.Thread(target=self._run_install, daemon=True).start()

    def _on_close(self):
        self._cancelled = True
        self.root.destroy()

    def _log(self, text, color=None):
        def _insert():
            self.log.configure(state="normal")
            tag = None
            if color:
                tag = f"color_{color}"
                self.log.tag_configure(tag, foreground=color)
            self.log.insert("end", text + "\n", tag or "")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, _insert)

    def _set_status(self, text):
        self.root.after(0, lambda: self.status_label.configure(text=text))

    def _set_progress(self, value):
        self.root.after(0, lambda: self.progress.configure(value=value))

    def _run_pip(self, args):
        cmd = [VENV_PIP] + args
        self._log(f"\n▶ {' '.join(args)}", color="#569cd6")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=SCRIPT_DIR,
        )
        for line in process.stdout:
            line = line.rstrip()
            if line:
                self._log("  " + line)
            self.root.update_idletasks()
        process.wait()
        return process.returncode == 0

    def _download_ffmpeg(self):
        """下載並解壓 FFmpeg 到 release/ffmpeg/"""
        zip_path = os.path.join(SCRIPT_DIR, "_ffmpeg_download.zip")

        self._log(f"  下載來源：{FFMPEG_URL}")

        last_pct = [-1]

        def report(block_num, block_size, total_size):
            if self._cancelled:
                raise RuntimeError("使用者取消")
            if total_size > 0:
                downloaded = block_num * block_size
                pct = min(100, downloaded * 100 // total_size)
                if pct != last_pct[0] and pct % 5 == 0:
                    last_pct[0] = pct
                    mb_done = downloaded / 1024 / 1024
                    mb_total = total_size / 1024 / 1024
                    self._log(f"  下載中... {pct}%  ({mb_done:.1f} / {mb_total:.1f} MB)")
                    # 進度條：85-95% 之間對應下載進度
                    self._set_progress(85 + int(pct * 0.10))

        try:
            urllib.request.urlretrieve(FFMPEG_URL, zip_path, report)
        except Exception as e:
            self._log(f"  ✗ 下載失敗：{e}", color="#f44747")
            return False

        self._log("  解壓縮中...")
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                names = z.namelist()
                if not names:
                    self._log("  ✗ zip 檔為空", color="#f44747")
                    return False
                top_folder = names[0].split("/")[0]
                z.extractall(SCRIPT_DIR)

            extracted_path = os.path.join(SCRIPT_DIR, top_folder)
            if os.path.exists(FFMPEG_DIR):
                shutil.rmtree(FFMPEG_DIR)
            os.rename(extracted_path, FFMPEG_DIR)

            os.remove(zip_path)
        except Exception as e:
            self._log(f"  ✗ 解壓失敗：{e}", color="#f44747")
            return False

        if not has_local_ffmpeg():
            self._log(f"  ✗ 解壓後找不到 {LOCAL_FFMPEG_EXE}", color="#f44747")
            return False

        return True

    def _run_install(self):
        if self._cancelled:
            return

        self._log("=" * 60, color="#608b4e")
        self._log("  Taigi-whisper-UI 環境安裝程式", color="#608b4e")
        self._log("=" * 60, color="#608b4e")
        self._log("")

        # 步驟 1：偵測硬體
        self._set_status("正在偵測硬體...")
        self._set_progress(5)
        self._log("【步驟 1/4】偵測硬體環境", color="#dcdcaa")
        has_gpu = detect_gpu()
        if has_gpu:
            self._log("  ✓ 偵測到 NVIDIA GPU，將安裝 CUDA 版 PyTorch（速度較快）", color="#4ec9b0")
        else:
            self._log("  ℹ 未偵測到 NVIDIA GPU，將安裝 CPU 版 PyTorch", color="#ce9178")
            self._log("    （若您有 NVIDIA 顯示卡，請確認已安裝 NVIDIA 驅動程式）")

        if self._cancelled:
            return

        # 步驟 2：安裝 PyTorch
        self._set_status("正在安裝 PyTorch...")
        self._set_progress(15)
        self._log("\n【步驟 2/4】安裝 PyTorch", color="#dcdcaa")

        if has_gpu:
            self._log("  安裝 PyTorch（CUDA 12.1 版）- 檔案較大，請耐心等待...")
            ok = self._run_pip(
                ["install", "torch", "torchaudio",
                 "--index-url", "https://download.pytorch.org/whl/cu121"],
            )
        else:
            self._log("  安裝 PyTorch（CPU 版）...")
            ok = self._run_pip(["install", "torch", "torchaudio"])

        if not ok:
            self._log("\n[錯誤] PyTorch 安裝失敗，請檢查網路連線後重試", color="#f44747")
            self._set_status("安裝失敗 - 請關閉視窗重試")
            return

        self._log("  ✓ PyTorch 安裝成功", color="#4ec9b0")

        if self._cancelled:
            return

        # 步驟 3：安裝其他套件
        self._set_status("正在安裝套件...")
        self._log("\n【步驟 3/4】安裝其他必要套件", color="#dcdcaa")

        total = len(PACKAGES)
        for i, pkg in enumerate(PACKAGES):
            if self._cancelled:
                return
            self._set_status(f"正在安裝 {pkg}...")
            progress = 40 + int((i / total) * 40)
            self._set_progress(progress)
            self._log(f"  [{i+1}/{total}] 安裝 {pkg}...")
            ok = self._run_pip(["install", pkg])
            if not ok:
                self._log(f"  ⚠ {pkg} 安裝失敗，繼續嘗試其他套件", color="#ce9178")
            else:
                self._log(f"  ✓ {pkg} 安裝成功", color="#4ec9b0")

        # 步驟 4：安裝 FFmpeg
        self._set_progress(85)
        self._set_status("正在處理 FFmpeg...")
        self._log("\n【步驟 4/4】安裝 FFmpeg", color="#dcdcaa")

        if detect_system_ffmpeg():
            self._log("  ✓ 系統已安裝 FFmpeg，無須下載", color="#4ec9b0")
        elif has_local_ffmpeg():
            self._log("  ✓ 本地已有 FFmpeg（ffmpeg 資料夾）", color="#4ec9b0")
        else:
            self._log("  未找到 FFmpeg，將自動下載可攜版本（約 90 MB）...")
            ok = self._download_ffmpeg()
            if ok:
                self._log("  ✓ FFmpeg 下載並解壓完成", color="#4ec9b0")
                self._log(f"    安裝位置：{FFMPEG_DIR}")
            else:
                self._log("  ⚠ FFmpeg 自動安裝失敗", color="#f44747")
                self._log("    您仍可手動安裝：winget install ffmpeg", color="#ce9178")

        # 建立安裝標記
        with open(INSTALLED_MARKER, "w") as f:
            f.write("installed")

        self._set_progress(100)
        self._log("\n" + "=" * 60, color="#608b4e")
        self._log("  安裝完成！正在啟動主程式...", color="#608b4e")
        self._log("=" * 60, color="#608b4e")
        self._set_status("安裝完成，正在啟動主程式...")

        self.root.after(1500, self._launch_main)

    def _launch_main(self):
        subprocess.Popen(
            [VENV_PYTHON, MAIN_SCRIPT],
            cwd=SCRIPT_DIR,
            env=build_env_with_ffmpeg(),
        )
        self.root.destroy()


def launch_main_directly():
    subprocess.Popen(
        [VENV_PYTHON, MAIN_SCRIPT],
        cwd=SCRIPT_DIR,
        env=build_env_with_ffmpeg(),
    )


def main():
    if os.path.exists(INSTALLED_MARKER):
        launch_main_directly()
        return

    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
