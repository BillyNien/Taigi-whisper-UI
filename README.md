# Taigi-whisper-UI

結合 **faster-whisper / Breeze-ASR（含台語）** 與 **pyannote 說話者辨識**的 Windows 語音轉文字工具，支援 GPU 加速。

> 本工具為個人開發的整合介面，核心辨識能力來自以下開源專案（詳見[致謝](#致謝)）。

---

## 功能特色

- 支援 faster-whisper（多語言）和 MediaTek Breeze-ASR（繁中/台語）雙引擎
- 說話者辨識（diarization），自動區分不同發言人
- 支援輸出 SRT、TXT、JSON 等格式
- 自動下載 FFmpeg，開箱即用
- GPU 自動偵測，無 NVIDIA 顯示卡也可用 CPU 模式

---

## 系統需求

| 項目 | 最低需求 | 建議 |
|------|---------|------|
| 作業系統 | Windows 10 | Windows 10/11 |
| Python | 3.10+ | 3.10 或 3.11 |
| RAM | 8 GB | 16 GB+ |
| 顯示卡 | 無（CPU 模式） | NVIDIA GPU（CUDA）|
| 磁碟空間 | 5 GB | 20 GB+（含模型）|
| 網路 | 首次安裝需要 | — |

---

## 快速開始

### 步驟 1：安裝 Python

前往 [python.org](https://www.python.org/downloads/) 下載 Python 3.10 或更新版本。

> **重要**：安裝時請勾選 **"Add Python to PATH"**

### 步驟 2：下載本程式

點擊頁面右上角的綠色 **Code** 按鈕 → **Download ZIP**，解壓縮到你想要的位置。

### 步驟 3：啟動程式

雙擊資料夾中的 **`start.bat`**。

- **第一次啟動**：會自動安裝所有必要的 Python 套件和 FFmpeg（約 5-20 分鐘，視網路速度）
- **之後啟動**：直接開啟主程式

> FFmpeg 會自動下載到程式資料夾內，不需要額外設定。若你已在系統安裝 FFmpeg，程式會自動偵測並跳過下載。

---

## 首次使用模型——請有心理準備

語音辨識模型很大，**第一次選用某個引擎時，程式會自動從網路下載模型**，這段時間畫面看起來像是沒有反應，請耐心等候，不要強制關閉。

### 各模型大小與下載時間參考

| 引擎 | 模型 | 大小 | 100 Mbps 網路 | 20 Mbps 網路 |
|------|------|------|--------------|-------------|
| faster-whisper | large-v3 | ~3 GB | 約 5–10 分鐘 | 約 20–30 分鐘 |
| Breeze-ASR-25 | 繁中/中英混語 | ~8 GB | 約 15–25 分鐘 | 約 60–90 分鐘 |
| Breeze-ASR-26 | 台語 | **~11 GB** | 約 20–35 分鐘 | 約 90–150 分鐘 |
| pyannote | 說話者辨識 | ~1 GB | 約 3–5 分鐘 | 約 10–15 分鐘 |

> **模型只需下載一次**，之後都從本機快取讀取，啟動速度會快很多。
> 模型預設儲存於 `C:\Users\你的名稱\.cache\huggingface\`，確認磁碟有足夠空間。

### 下載卡住了怎麼辦？

- 關閉程式，重新開啟再試一次，HuggingFace 支援斷點續傳
- 確認沒有開 VPN 或防火牆擋住連線
- 若網路很慢，建議睡前開啟，讓它跑一晚

---

## 說話者辨識（選用功能）

若要使用「說話者辨識」功能，需要 HuggingFace 帳號與 Token：

1. 前往 [huggingface.co](https://huggingface.co) 建立免費帳號
2. 至以下連結同意使用條款：
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
3. 至 [Settings → Access Tokens](https://huggingface.co/settings/tokens) 建立 Token
4. 將 Token 貼入程式介面中的「HuggingFace Token」欄位

---

## 常見問題

**Q：雙擊 start.bat 沒有反應？**  
請確認已安裝 Python 3.10+ 並勾選了「Add Python to PATH」。可在命令提示字元輸入 `python --version` 確認。

**Q：安裝過程出現錯誤？**  
通常是網路問題，請關閉視窗後重新雙擊 `start.bat` 重試。

**Q：程式很慢？**  
預設使用 CPU 模式。若有 NVIDIA 顯示卡，請確認已安裝 NVIDIA 驅動，程式會自動使用 GPU 加速。CPU 模式下，1 分鐘音訊大約需要 3–10 分鐘處理時間，屬正常現象。

**Q：按下「開始辨識」之後畫面沒有反應？**  
如果是**第一次使用該引擎**，程式正在背景下載模型（最大約 11 GB），這段時間看起來像當機但其實正在運作，請等候 10–30 分鐘。可以觀察硬碟燈或網路流量確認是否有在動。

**Q：磁碟空間不夠？**  
模型儲存在 `C:\Users\你的名稱\.cache\huggingface\`，若要清除可直接刪除該資料夾內對應的模型資料夾，下次使用時會重新下載。

**Q：音訊無法載入？**  
請確認程式資料夾內有 `ffmpeg\bin\ffmpeg.exe`。若下載失敗，可刪除 `.installed` 檔後重新執行 `start.bat`，或手動執行 `winget install ffmpeg`。

**Q：說話者辨識結果只有 SPEAKER_00 一個人？**  
請確認音訊中確實有多人發言，且在介面中設定了正確的「最大說話者人數」。若只有一個人說話，pyannote 本來就只會輸出一個說話者。

---

## English Quick Start

1. Install [Python 3.10+](https://www.python.org/downloads/) — check **"Add Python to PATH"**
2. Download and extract this repo (Code → Download ZIP)
3. Double-click `start.bat` — first run auto-installs all dependencies **and FFmpeg**

---

## 致謝

本工具整合了以下開源專案，感謝各團隊的貢獻：

| 專案 | 授權 | 說明 |
|------|------|------|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT | 核心語音辨識引擎 |
| [OpenAI Whisper](https://github.com/openai/whisper) | MIT | faster-whisper 底層模型 |
| [pyannote.audio](https://github.com/pyannote/pyannote-audio) | MIT | 說話者辨識（diarization） |
| [Breeze-ASR-25](https://huggingface.co/MediaTek-Research/Breeze-ASR-25) | Apache 2.0 | MediaTek Research 繁中語音模型 |
| [Breeze-ASR-26](https://huggingface.co/MediaTek-Research/Breeze-ASR-26) | Apache 2.0 | MediaTek Research 台語語音模型 |
| [transformers](https://github.com/huggingface/transformers) | Apache 2.0 | Breeze-ASR 推理框架 |
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | MIT | GUI 框架 |
| [opencc-python-reimplemented](https://github.com/yichen0831/opencc-python-reimplemented) | Apache 2.0 | 簡繁轉換 |

### 模型授權說明

- **Whisper 模型**（large-v2、large-v3 等）：OpenAI MIT License，免費商業使用。
- **Breeze-ASR 模型**：Apache 2.0，免費商業使用，但**不得以 MediaTek 名義進行背書或推廣**。
- **pyannote 模型**（speaker-diarization-3.1）：需在 HuggingFace 上同意使用條款，**禁止商業使用**，僅限個人與研究用途。若有商業需求請參閱 [pyannote 授權說明](https://huggingface.co/pyannote/speaker-diarization-3.1)。

---

## 授權

本專案原始碼以 [MIT License](LICENSE) 授權發布。

本工具本身為免費開源軟體，但所整合的語音模型（尤其是 pyannote diarization 模型）有各自的使用限制，使用前請確認符合各模型的授權條款。
