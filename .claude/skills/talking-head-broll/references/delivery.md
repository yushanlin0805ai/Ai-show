# 交付

## 檔案

| 檔案 | 給誰 | 大小（59 秒參考） |
|---|---|---|
| `output/<名稱>-合成.mp4` | 直接發布 | ~80MB |
| `output/<名稱>.fcpxml` | DaVinci／Final Cut 開專案 | 幾 KB |
| `output/broll/broll-xx.webm` | CapCut、瀏覽器、網頁 | 每段 < 1.5MB |
| `output/broll/broll-xx.mov` | Premiere、DaVinci、Final Cut（ProRes 4444 含透明） | 每段 60～140MB |
| `output/broll/cut-xx.mp4` | 全部軟體 | 每段 < 1MB |
| `output/broll/captions.webm`、`captions.srt` | 字幕軌／字幕檔 | 1～2MB |
| `output/broll/cue-list.md`（也在 `storyboard/`） | 人工擺放對照表 | — |
| `output/qa/facezone-check.jpg` | 檢查擋臉 | — |

用 `SendUserFile` 傳：合成影片、一個 zip（WebM＋插畫 MP4＋字幕＋cue list＋FCPXML）、檢查圖。
MOV 太大，先問使用者要不要、要分批傳還是放 Google Drive。

```bash
cd projects/<名稱>/output && (cd broll && zip -q ../<名稱>-broll.zip broll-*.webm cut-*.mp4 captions.* cue-list.md) && zip -q <名稱>-broll.zip <名稱>.fcpxml
```

## 時間軸檔怎麼用

`export-timeline.py` 產生 FCPXML 1.10：主軌是原片（含聲音），上一層依 cue list 放好每段 B-roll（透明段用 .mov、插畫用 .mp4）。

- **DaVinci Resolve**：檔案 → 匯入 → 時間軸 → 選 `.fcpxml`；跳出找不到素材時按「重新連結」，指到解壓縮後的資料夾。字幕：在媒體池匯入 `captions.srt` 拖到字幕軌。
- **Final Cut Pro**：檔案 → 匯入 → XML。字幕：檔案 → 匯入 → 字幕（SRT）。
- **Premiere Pro**：不支援 FCPXML。用 DaVinci 匯入後「檔案 → 匯出 → 時間軸 → FCP 7 XML」再給 Premiere，或照 cue-list.md 手動擺；字幕直接匯入 SRT。
- **CapCut**：不支援時間軸檔，照 cue-list.md 擺 WebM／MP4，字幕匯入 SRT。

素材路徑：預設寫雲端機器上的路徑，使用者電腦上一定要重新連結。若知道使用者會把檔案放哪，可以
`python3 export-timeline.py projects/<名稱> --media-root "/Users/<名字>/Downloads/<名稱>"` 先寫好路徑（原片放根目錄、B-roll 放 `broll/`）。
雲端無法實際開剪輯軟體測試，交付時要說明「請匯入後確認」。

## 不進 Git

原片與所有輸出影片、`composition/` 內複製的字型／GSAP／影片、`composition-*` 資料夾、Hyperframes 轉檔快取（`.transcode-cache/`）、
**任何含講者臉的截圖**（`storyboard/faces/`、`qa-frames/`、`samples/assets/`、`output/qa/`）。這些規則都已寫在 `.gitignore`。

## 交付訊息要說的事

1. 每個檔案是什麼、怎麼用（一句話）
2. `verify-output.py` 的結果；有 ⚠ 的段落說明是什麼（例：結論條碰到頭頂上方的安全邊界）
3. 第三方素材授權（licenses.md）、發布前確認出處（sources.md）
4. 提醒關掉 Drive 分享
5. 沒傳的檔案（MOV）要不要
