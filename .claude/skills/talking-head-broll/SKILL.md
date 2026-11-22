---
name: talking-head-broll
description: 實拍口播影片（講者對鏡頭說話）的剪輯流程：從 Google Drive 取片、自動找出講者的臉、做風格樣張、規劃疊加圖卡與全螢幕插畫 B-roll 的分鏡、用 Hyperframes 渲染（合成影片＋透明 B-roll 片段＋透明字幕軌）、切段、產出 cue list 與 DaVinci／Final Cut 時間軸檔（FCPXML），最後自動檢查有沒有擋到臉。當使用者提到實拍、口播、真人影片、B-roll、疊加動畫、合成、剪輯、時間軸、Premiere、DaVinci、Final Cut、cue list，或給了一支自己拍的影片要加動畫時使用。只有錄音、要做純動畫影片請改用 broll-video。
---

# 實拍口播剪輯（talking-head-broll）

把「講者對鏡頭說話的直式影片＋逐字稿」加上動畫，交付三種東西：
1. **合成好的完整影片**（可以直接發）
2. **一段段 B-roll 素材**（透明背景圖卡、全螢幕插畫、透明字幕軌）＋ **cue list**（第幾秒放哪段）
3. **剪輯軟體時間軸檔**（FCPXML：DaVinci／Final Cut 開檔就看到原片與 B-roll 已經擺好）

範例專案（完整跑過一次）：`projects/example-talking-head/`。**新專案從它的 `composition/index.html` 複製再改最快。**

## 開工前必讀

| 檔案 | 什麼時候讀 |
|---|---|
| `references/storyboard.md` | 寫分鏡前：三種畫面、版面、硬性規則 |
| `references/render-pipeline.md` | 做 composition 與渲染前：原理與一定會踩的坑 |
| `references/delivery.md` | 交付前：檔案清單、時間軸檔匯入方式、什麼不進 Git |
| `brands/<品牌>/brand.md` | 有指定品牌時：配色、字型、主特效、CTA 位置 |
| `.claude/skills/broll-video/references/compliance.md` | **每次都讀**：內容守則（禁用詞、出處、趣味入口只當 CTA）；另外讀 `brands/<品牌>/compliance.md` |

## 專案資料夾

```
projects/<名稱>/
  inputs/            原片（不進 Git）、transcript.txt（一行一句）
  project.json       title、brand、mode:"B"、source、cta、caption、face_zone、segments
  storyboard/        timing/（時間點）、storyboard.md、licenses.md、cue-list.md
  samples/           風格樣張（可選）
  composition/       Hyperframes 專案（index.html＝完整版）
  output/            成品（不進 Git）：<名稱>-合成.mp4、<名稱>.fcpxml、broll/、qa/
```

## 流程：每一步做完都停下來，等使用者確認才往下

S=`.claude/skills/talking-head-broll/scripts`，H=`.claude/skills/broll-video/scripts`

### 步驟 1：取得影片與時間點
1. 使用者給 Drive 連結時：請他先開「知道連結的人都能檢視」，然後
   ```bash
   bash $S/fetch-drive.sh "<Drive 連結>" projects/<名稱>/inputs/source.mp4
   ```
   被網路擋住時，雲端環境要允許 `drive.google.com`、`drive.usercontent.google.com`。**不要用 Drive 連接器搬影片**（只能搬小檔）。
2. 規格：直式 1080×1920 最好；橫式要先問使用者講者在哪一側再裁切。
3. 逐字稿存成 `inputs/transcript.txt`，產生時間點（專有名詞用 `--terms`）：
   ```bash
   python3 $H/transcribe.py projects/<名稱>/inputs/source.mp4 --transcript projects/<名稱>/inputs/transcript.txt \
     --out projects/<名稱>/storyboard/timing --terms "專有名詞1,專有名詞2"
   ```
4. 對照 `timing/alignment.md`：口播和逐字稿不同的地方整理成表，**問使用者字幕照口播還是照逐字稿**。
5. 依 compliance.md 檢查逐字稿，疑點標出來問，不自己改。
6. **停下回報**。

### 步驟 2：找臉（臉部安全區）
```bash
pip install "opencv-python-headless<5"   # 第一次
python3 $S/face-zone.py projects/<名稱>/inputs/source.mp4 --project projects/<名稱>
```
寫入 project.json 的 `face_zone`，並產生 `storyboard/faces/face-zone.jpg`（紅框）。**一定要看這張圖**確認紅框框住臉和頭髮；
偵測率低或框歪了，就改用人工抽格判讀，手動改 `face_zone`。動畫的可用區通常是臉上方（例如 y 200～face_zone.y0）。

### 步驟 3：風格樣張（使用者沒指定風格時）
同一句字幕、同一格實拍畫面，做 2～3 種風格（放 `samples/styles/`，用 `npx hyperframes snapshot` 出圖），每種只用 1 個主特效。
主特效先用 `npx hyperframes catalog --query "<英文關鍵字>"` 找，`npx hyperframes add <名稱>` 安裝後讀原始碼確認授權與是否需要網路
（WebGPU 類在雲端軟體渲染不穩，避開）。傳對照圖給使用者選。

### 步驟 4：分鏡表
依 `references/storyboard.md` 寫 `storyboard/storyboard.md`，三種畫面「小／全／字」交錯；需要的話先做插畫 B-roll 的預覽圖。
同時把每段寫進 project.json 的 `segments`（id、start、end、kind、place、line），更新 `licenses.md`。
**停下**，使用者明確說「確認」才往下。

### 步驟 5：製作 composition
照 `references/render-pipeline.md`：複製範本 `projects/example-talking-head/composition/`（index.html、styles/），改段落與時間（取自 words.json），
project.json 設 `caption`（px、line_units、keywords）。然後：
```bash
python3 $H/prepare-composition.py projects/<名稱>
cd projects/<名稱>/composition && npx -y hyperframes@0.9.19 lint . && \
  npx -y hyperframes@0.9.19 check . --at <每段中間的秒數> --caption-zone "x0=0.05;y0=0.72;x1=0.95;y1=0.835"
npx -y hyperframes@0.9.19 snapshot . --at <每段中間的秒數> --no-end -o ../storyboard/qa-frames
```
check 要 0 錯誤；逐張看 snapshot（字型、關鍵字、時間點、有沒有擋臉）。

### 步驟 6：一鍵渲染＋自動檢查
```bash
bash $S/render-all.sh projects/<名稱>
```
依序做：合成影片 → 透明圖卡層 → 透明字幕層 → 切段（`split-broll.py`）→ cue list → 時間軸檔（`export-timeline.py`）→ 檢查（`verify-output.py`）。
約影片長度的 15 倍時間，放背景跑。檢查有 ✗ 就修正重跑（只改動畫可加 `--skip-composite` 省時間，但最後交付前要完整重跑一次）。
⚠（臉部安全區被蓋 1～5%）要看 `output/qa/facezone-check.jpg` 判斷，並在交付時說明。

### 步驟 7：交付
照 `references/delivery.md`：傳合成影片、B-roll 壓縮包（WebM＋插畫 MP4＋字幕＋cue list＋FCPXML）、檢查圖；MOV 太大另外問。
提醒使用者：關掉 Drive 分享、發布前確認 sources／licenses。commit＋push（不含影片與含臉截圖）。
