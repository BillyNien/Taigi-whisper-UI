# Taigi-whisper-UI

結合 **faster-whisper / Breeze-ASR（含台語）** 與 **pyannote 說話者辨識**的語音轉文字工具，支援 **Windows** 與 **macOS（Apple Silicon）** 雙平台。

> 本工具為個人開發的整合介面，核心辨識能力來自各開源專案（詳見[致謝](#致謝)）。

---

## 下載與使用

| 平台 | 資料夾 | 說明文件 |
|------|--------|---------|
| 🪟 Windows 10/11 | [`windows/`](./windows/) | [Windows 使用說明](./windows/README.md) |
| 🍎 macOS（Apple Silicon） | [`mac/`](./mac/) | [macOS 使用說明](./mac/README.md) |

**下載方式**：點擊右上角綠色 **Code** → **Download ZIP**，解壓後進入對應平台的資料夾。

---

## 功能特色

- 支援 faster-whisper（多語言）和 MediaTek Breeze-ASR（繁中／台語）雙引擎
- 說話者辨識（diarization），自動區分不同發言人
- 支援輸出 SRT、TXT、JSON 格式
- GPU 加速（Windows：NVIDIA CUDA；macOS：Apple Silicon MPS）
- 自動下載 FFmpeg（Windows 版），開箱即用

---

## 首次使用模型——請有心理準備

語音辨識模型很大，**第一次選用某個引擎時，程式會自動從網路下載模型**，這段時間畫面看起來像是沒有反應，請耐心等候，不要強制關閉。

| 引擎 | 模型 | 大小 | 100 Mbps 網路 | 20 Mbps 網路 |
|------|------|------|--------------|-------------|
| faster-whisper | large-v3 | ~3 GB | 約 5–10 分鐘 | 約 20–30 分鐘 |
| Breeze-ASR-25 | 繁中/中英混語 | ~8 GB | 約 15–25 分鐘 | 約 60–90 分鐘 |
| Breeze-ASR-26 | 台語 | **~11 GB** | 約 20–35 分鐘 | 約 90–150 分鐘 |
| pyannote | 說話者辨識 | ~1 GB | 約 3–5 分鐘 | 約 10–15 分鐘 |

> **模型只需下載一次**，之後從本機快取讀取。若下載卡住，關閉程式後重開即可（支援斷點續傳）。

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
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | MIT | GUI 框架（Windows） |
| [opencc-python-reimplemented](https://github.com/yichen0831/opencc-python-reimplemented) | Apache 2.0 | 簡繁轉換 |

### 模型授權說明

- **Whisper 模型**：OpenAI MIT License，免費商業使用。
- **Breeze-ASR 模型**：Apache 2.0，免費商業使用，但**不得以 MediaTek 名義進行背書或推廣**。
- **pyannote 模型**：需在 HuggingFace 上同意使用條款，**禁止商業使用**，僅限個人與研究用途。詳見 [pyannote 授權說明](https://huggingface.co/pyannote/speaker-diarization-3.1)。

---

## 授權

本專案原始碼以 [MIT License](LICENSE) 授權發布。各整合模型有各自的使用限制，使用前請確認符合授權條款。
