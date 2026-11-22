---
name: broll-video
description: 把繁體中文的知識型口播（任何產業：健康、睡眠、身心靈、理財…）（錄音或實拍影片＋逐字稿）做成 IG／Reels 直式 9:16 動畫短影音或 B-roll 片段。流程：輸入檢查與逐字時間點 → 分鏡表 → 使用者確認 → 用 Hyperframes（HTML）製作與渲染 → 品質檢查。當使用者提到短影音、衛教短影音、Reels 動畫、B-roll、分鏡表、口播影片配動畫、逐字稿轉畫面、projects/ 底下的影片專案時使用。
---

# 短影音動畫（broll-video）

把「錄音或口播影片＋逐字稿」變成 1080×1920、30fps 的動畫短影音。

**品牌設定在 `brands/<品牌>/`**（說話風格 voice.md、配色 brand.md、產業守則 compliance.md、CTA cta.json）。開工先確認是哪個品牌；`brands/` 只有範例沒有正式品牌時，請使用者先跑 brand-setup 技能。

## 開工前必讀

| 檔案 | 什麼時候讀 |
|---|---|
| `references/compliance.md` ＋ `brands/<品牌>/compliance.md` | **每次都讀**。步驟 1、2、6 都要對照（通用守則＋產業守則） |
| `references/storyboard-rules.md` | 步驟 2 寫分鏡前 |
| `references/design-system.md` ＋ `brands/<品牌>/brand.md` | 步驟 2 寫畫面描述、步驟 4 做畫面前（brand.md 的配色覆蓋 design-system 的色票） |
| `references/cta.md` | 做結尾 CTA 時 |
| `references/cross-section.md` | 主題講到身體構造（皮膚、脂肪細胞、胃、血管…）要畫剖面時；範例 `reference/cross-section-fat.html` |
| `reference/aspartame-2b.html`（repo 根目錄） | 步驟 4 做畫面前，看實際範例 |

## 專案資料夾

```
projects/<影片名稱>/
  inputs/        音檔或影片、transcript.txt（逐字稿，一行一句）
  project.json   （可選）CTA 文字、模式等設定，見 references/cta.md
  storyboard/
    timing/      transcribe.py 的輸出（words.json、lines.json、transcript.srt、alignment.md）
    storyboard.md
    sources.md
  composition/   Hyperframes 專案（步驟 4 才建立）
  output/        影片成品（不進 Git）
```

## 流程：六個步驟，**每一步做完都停下來，等使用者確認才往下**

每一步結束時，用一段簡短訊息回報：做了什麼、產出檔案在哪、需要使用者決定什麼，然後**停止**。

---

### 步驟 1：輸入檢查

1. 執行環境檢查：
   ```bash
   bash .agents/skills/broll-video/scripts/check-setup.sh
   ```
   缺東西就把缺的項目和安裝方式告訴使用者，先不要繼續。
2. 確認 `inputs/` 有：
   - 音檔（m4a/mp3/wav）或影片（mp4/mov）。用 `ffprobe` 讀長度、解析度、fps。
   - 逐字稿 `transcript.txt`。沒有就問使用者；使用者也沒有，就用辨識結果當草稿，請使用者校對。
   - 判斷模式：只有音檔 → **模式 A**；有實拍口播影片 → **模式 B**。使用者另有指定則照指定。
   - **沒有任何聲音、使用者選「無聲模式」** → 模式 A 的無聲版，第 3 點改用 `silent-timing.py`（見下）。
3. 產生逐字時間點（已有 SRT／word-level 時間檔就跳過，直接轉成 lines.json 格式）：
   ```bash
   python3 .agents/skills/broll-video/scripts/transcribe.py \
     projects/<名稱>/inputs/<音檔或影片> \
     --transcript projects/<名稱>/inputs/transcript.txt \
     --out projects/<名稱>/storyboard/timing
   ```
   - 用 faster-whisper large-v3（CPU 約 1～3 倍音檔長度的時間；太慢可加 `--model medium`）。
   - 時間點會對齊回**逐字稿原文**，字幕用字以逐字稿為準。
   - 看 `alignment.md`：相似度低於 80%，或某句差異很大，代表口播和逐字稿可能不一樣，要告訴使用者。
   - **無聲模式**（沒有配音）：用閱讀速度排時間，輸出格式和 transcribe.py 完全相同，另外產生同長度的靜音音檔 `inputs/silent.m4a` 當作後面的音檔：
     ```bash
     python3 .agents/skills/broll-video/scripts/silent-timing.py projects/<名稱>/inputs/transcript.txt \
       --out projects/<名稱>/storyboard/timing [--cps 4.5]
     ```
     閱讀速度預設每秒 4.5 字；數字和專有名詞多的腳本用 4。無聲版的字幕就是主角：字幕可以比平常大一級、停留到下一句出現為止。
     使用者有背景音樂（自己有授權的）→ 剪成同長度並淡出，取代 silent.m4a：
     `ffmpeg -y -i <音樂> -t <總長> -af "afade=t=out:st=<總長-2>:d=2,volume=0.6" -c:a aac projects/<名稱>/inputs/silent.m4a`
     **之後換成真人或 AI 配音**：用新音檔重跑上面的 transcribe.py，分鏡不重做，只把畫面時間換成新的 timing（同 reel-pipeline 步驟 ③-2）。
4. 依兩份 `compliance.md` 檢查逐字稿：禁用詞、不精確說法、需要出處的數字。**只標出來，不修改。**
5. **停下來回報**：模式、長度、時間點品質、逐字稿疑點清單。

### 步驟 2：分鏡表

依 `storyboard-rules.md` 產出 `storyboard/storyboard.md`，同時產出 `storyboard/sources.md` 草稿：
- 逐句判斷要不要畫面、畫面類型（全／小／字／CTA）、畫面描述、理由。
- 秒數一律取自 `timing/lines.json`、`timing/words.json`，不要估。
- 畫面描述要用 `design-system.md` 的元件與顏色名稱。
- 表格後附：畫面清單、規則自檢（連續類型 ≤ 2、每畫面 ≥ 1.5 秒）、逐字稿疑點、需要使用者決定的事。
- sources.md：畫面上每個數字／分級／研究結論一條，狀態「待使用者確認」。

**停下來**，請使用者確認分鏡表與疑點。

### 步驟 3：等使用者確認

- 使用者要求修改 → 改分鏡表 → 再次確認。
- 使用者回覆逐字稿疑點：如果決定修改口播內容，請使用者重錄或提供新逐字稿，回到步驟 1。
- **沒有明確說「確認」「OK」「可以做了」之類的話，不准進入步驟 4。**

### 步驟 4：製作與渲染（Hyperframes）

工具：**Hyperframes**（`hyperframes` npm 套件，Apache 2.0，HTML 原生，需要 Node 22+、ffmpeg、Chrome）。
**不要用 Remotion**（商用授權限制），除非使用者明確要求。

**開工前先確認目前版本的用法，不要憑記憶**：
```bash
npx hyperframes --version
npx hyperframes help render
npx hyperframes doctor
```
官方文件：https://github.com/heygen-com/hyperframes （docs/ 資料夾）、https://hyperframes.heygen.com 。
也可以安裝官方 skills 讓寫法更準：`npx hyperframes skills update`（核心組：/hyperframes、/hyperframes-cli）。

以下是 2026-11 用 v0.9.19 實際做完 example-aspartame 驗證過的作法。**範本：`projects/example-aspartame/composition/index.html`**，新專案從它複製再改最快。

0. 環境變數（每次執行 hyperframes 前設定）：
   ```bash
   export HYPERFRAMES_SKIP_SKILLS=1        # 不要讓 init 自動安裝官方 skills
   export HYPERFRAMES_BROWSER_PATH=<Chrome 路徑>  # 可選；check-setup.sh 會列出找到的 Chrome
   ```
   版本固定用 `npx -y hyperframes@0.9.19`（和 composition/package.json 一致），升級前先跑 `npx hyperframes@latest upgrade --project composition --check`。
1. 建立專案（9:16）：
   ```bash
   cd projects/<名稱>
   npx -y hyperframes@0.9.19 init composition --resolution portrait --audio inputs/<音檔> \
     --skip-transcribe --skip-skills --non-interactive
   rm composition/AGENTS.md   # 和 CLAUDE.md 內容相同
   ```
   （`--skip-transcribe`：時間點用我們自己對齊過逐字稿的版本，不用它內建的 whisper。）
2. 寫 `composition/index.html`（照 demo 範本）：
   - 根元素：`<div id="root" data-composition-id="main" data-start="0" data-duration="<長度>" data-width="1080" data-height="1920">`
   - **GSAP 不走 CDN**：`<script src="vendor/gsap.min.js">`。init 產生的 CDN 網址要換掉（公司或雲端網路常擋 CDN）。
   - 字型：`@font-face` 指向 `fonts/NotoSansTC-*.otf` 與 `fonts/NotoColorEmoji.ttf`（emoji 也用內附字型，Mac／Windows 渲染結果才會一致）。
   - 每個畫面（或「同一畫面＋疊加的小物件」）是一個 `<section class="clip scene">`，帶 `data-start`、`data-duration`；秒數照分鏡表。
   - 音訊：`<audio data-start="0" data-duration="<長度>" src="<音檔檔名，URL 編碼>">`。模式 B 的原片音訊不放進 B-roll 片段。
   - 動畫：一個 paused 的 GSAP timeline，`window.__timelines["main"] = tl`。元素出現時間取自 `timing/words.json`。
     用範本裡的 `fadeUp／slideIn／pop／fadeIn／fadeOut／breathe`（對應 design-system.md 第 5 節）。
     初始隱藏用 `gsap.set(...)`，**不要用 `tl.set(..., 0)`**（第 0 格不會生效，lint 會警告）。呼吸循環要有限次數。
   - 第 0 格就要有標題（縮圖）。
   - 字幕：留 `<!-- CAPTIONS:BEGIN -->…<!-- CAPTIONS:END -->` 標記；CTA 元素加 `data-cta="question|keyword|action|action-tail"`；CTA 大字出現後隱藏字幕用 `#captions` 的 `data-hide-from`。
3. 填入素材與變數（每次改了逐字稿、時間點、CTA 都要重跑）：
   ```bash
   npm install   # repo 根目錄，第一次才需要（安裝 GSAP）
   python3 .agents/skills/broll-video/scripts/prepare-composition.py projects/<名稱>
   ```
   會複製字型、GSAP、音檔到 composition/（都不進 Git），依 transcript.srt 產生字幕、依 project.json 填 CTA。
4. 預覽（可選）：`npx hyperframes preview --background`，看完 `npx hyperframes preview --stop`。
5. 渲染前先過步驟 6 的 lint 與 check，再依下方「兩種模式」渲染。

### 步驟 5：兩種模式的輸出

**模式 A：只有錄音 → 完整動畫影片**
```bash
npx -y hyperframes@0.9.19 render --output ../output/<名稱>.mp4 --fps 30 --quality high
```
內容：全部畫面＋字幕＋錄音＋結尾 CTA。

**模式 B：實拍口播 → 改用 `talking-head-broll` 技能**

實拍口播影片（取片、找臉、樣張、疊加圖卡＋插畫 B-roll、三種版本渲染、切段、cue list、時間軸檔、自動檢查）
的完整流程在 `.agents/skills/talking-head-broll/SKILL.md`。本技能的 `transcribe.py`、`prepare-composition.py`、
`compliance.md` 會被它沿用。

### 步驟 6：品質檢查（通過才交付）

1. Lint 與 check（渲染前，**錯誤必須是 0**）：
   ```bash
   cd projects/<名稱>/composition
   npx -y hyperframes@0.9.19 lint .
   npx -y hyperframes@0.9.19 check . --at <每個畫面中段與換場點，逗號分隔> --snapshots \
     --caption-zone "x0=0.07;y0=0.71;x1=0.93;y1=0.83"
   ```
   `check` 會檢查文字超框、重疊、對比、音訊。判讀方式：
   - `nested_structure_needs_subcomposition`、`composition_file_too_large`、`timeline_track_too_dense`：只影響官方 Studio 編輯器的顯示，可以不理。
   - `line_unread`（字幕停留太短）：字幕跟著口播速度走，口播快就會出現，不用改；但**畫面上的固定文字**（標題、註腳）出現這個警告就要提早出現。
   - 刻意的重疊（例如小卡片蓋在變暗的前一畫面上）：在那段文字加 `data-layout-allow-overlap`，被蓋住的區塊加 `data-layout-allow-occlusion`。
   - `first_frame_empty`：第 0 格要有標題。
2. 抽格截圖（每個畫面至少一張，加上每個畫面換場點）：
   ```bash
   npx -y hyperframes@0.9.19 snapshot . --at 2.5,10.4,18.7 --no-end -o ../storyboard/qa
   ```
   逐張看：
   - 字幕沒有超出畫面或兩行以上
   - 中文字型是 Noto Sans TC（不是方框 □、不是明體／文泉驛）
   - 物件在安全區內；模式 B 沒有擋到臉
3. 同步檢查：對照 `timing/words.json`，抽 3～5 個關鍵字（數字、物件名稱），確認那一秒的截圖上該元素剛出現（誤差 ≤ 0.2 秒）。
4. 渲染後用 `ffprobe` 確認：1080×1920、30fps、長度與音檔相差 < 0.1 秒、有音軌（模式 A）。
5. 再跑一次 `compliance.md` 的禁用詞掃描（掃 composition HTML）。
6. 交付時回報：輸出檔路徑、截圖、檢查結果，並提醒「**發布前請逐條確認 sources.md**」。

任何一項不通過：修正後重跑步驟 6，不要直接交付。
