# Taigi-whisper-Mac

macOS（Apple Silicon）版本，移植自 [Taigi-whisper-UI](https://github.com/BillyNien/Taigi-whisper-UI)。  
全新 v2 版本，解決 macOS 執行穩定性問題，介面重新設計。

---

## 功能特色

- 支援 faster-whisper（多語言）和 MediaTek Breeze-ASR（繁中／台語）雙引擎
- 說話者辨識（diarization），自動區分不同發言人
- 支援輸出 SRT、TXT、JSON 格式
- 深色主題介面，直覺易用
- Apple Silicon MPS 加速（faster-whisper 使用 CPU 保穩定）

---

## 系統需求

| 項目 | 需求 |
|------|------|
| 作業系統 | macOS（Apple Silicon M1/M2/M3，或 Intel） |
| Python | 3.11 |
| [uv](https://github.com/astral-sh/uv) | `brew install uv` |
| ffmpeg | `brew install ffmpeg` |

---

## 快速開始

```bash
cd mac
chmod +x start.sh
./start.sh
```

第一次執行會自動建立虛擬環境並安裝所有套件（需幾分鐘），之後直接執行即可。

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

> **模型只需下載一次**，之後從本機快取讀取。  
> 模型預設儲存於 `~/.cache/huggingface/`，確認磁碟有足夠空間。

### 下載卡住了怎麼辦？

- 關閉程式，重新執行 `./start.sh` 再試，HuggingFace 支援斷點續傳
- 確認沒有開 VPN 或防火牆擋住連線
- 若網路很慢，建議睡前開啟讓它跑一晚

---

## 說話者辨識（選用功能）

若要使用「說話者辨識」功能，需要 HuggingFace 帳號與 Token：

1. 前往 [huggingface.co](https://huggingface.co) 建立免費帳號
2. 至以下連結同意使用條款：
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
3. 至 [Settings → Access Tokens](https://huggingface.co/settings/tokens) 建立 Token（選 Read 權限即可）
4. 將 Token 貼入程式介面中的「HuggingFace Token」欄位

> Token 僅儲存於本機設定檔，不會上傳任何地方。

---

## 與 Windows 版的差異

| 項目 | Windows | Mac |
|------|---------|-----|
| 字型 | Microsoft JhengHei | PingFang TC |
| 加速方式 | CUDA / CPU | MPS / CPU |
| 開啟資料夾 | `os.startfile` | `open`（Finder）|
| pyannote 設備 | GPU | CPU（MPS 穩定性問題）|
| 啟動腳本 | `start.bat` | `start.sh`（使用 `uv`）|

---

## 常見問題

**Q：執行 start.sh 出現「permission denied」？**
```bash
chmod +x start.sh
```

**Q：按下「開始辨識」之後畫面沒有反應？**  
如果是**第一次使用該引擎**，程式正在背景下載模型（最大約 11 GB），這段時間看起來像當機但其實正在運作，請等候 10–150 分鐘（依網速而定）。可以開「活動監視器」→「網路」確認是否有流量。

**Q：程式很慢？**  
faster-whisper 使用 CPU 模式（穩定性最佳），1 分鐘音訊大約需要 3–5 分鐘。Breeze-ASR 台語版較慢屬正常。

**Q：磁碟空間不夠？**  
模型儲存在 `~/.cache/huggingface/`，若要清除可直接刪除對應的模型資料夾，下次使用時會重新下載。

**Q：說話者辨識一直失敗？**  
請確認：① HuggingFace Token 正確且有效；② 已在 pyannote 頁面點擊同意授權（需登入 HuggingFace）；③ Token 有 Read 權限。

---

## 測試環境

M2 MacBook Pro，macOS Sequoia，Python 3.11。  
三個引擎均測試通過：faster-whisper、Breeze-ASR-25、Breeze-ASR-26（台語）。
