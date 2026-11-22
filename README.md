# short-video-kit：AI 知識型短影音工具包

把「一個點子」做成 IG／Reels 直式動畫短影音：腳本 → 配音 → 動畫（含剖面動畫）→ IG 說明文字。
任何產業都能用：健康、睡眠、身心靈、理財、教育……每個人有自己的品牌設定。

**第一次用，請看 [使用說明.md](使用說明.md)。**

## 支援的 AI 工具

| 工具 | 技能放在 | 狀態 |
|---|---|---|
| Claude Code（claude.ai/code） | `.claude/skills/` | 已實際做過多支影片 |
| ChatGPT Codex（chatgpt.com/codex） | `.agents/skills/`（內容和上面相同） | 測試中，第一次請和老師一起跑 |

## 技能一覽

| 技能 | 做什麼 | 什麼時候說 |
|---|---|---|
| brand-setup | 一題一題問你，建立自己的品牌設定 | 「幫我設定品牌」 |
| reel-pipeline | 總指揮：點子 → 腳本 → 配音 → 動畫 → 說明文字 | 「用 reel-pipeline，主題是＿＿」 |
| broll-video | 錄音＋逐字稿 → 純動畫影片（含剖面模式） | 已經有錄音時 |
| talking-head-broll | 真人出鏡影片 → 加上圖卡與動畫 | 已經有自己拍的影片時 |
| ig-reel、ig-caption、ig-carousel、ig-repurpose、ig-plan、ig-profile、ig-human | IG 腳本、說明文字、輪播、延伸題目、排程、個人檔案健檢（第三方，MIT，見 `licenses/`） | 由 reel-pipeline 叫用，也可以單獨用 |

## 資料夾

```
brands/
  _example-sleep/        範例：熬夜族保健品品牌
  _example-wellness/     範例：身心靈品牌（產品還在定位中）
  <你的品牌>/            brand-setup 會幫你建立
projects/
  example-aspartame/     範例：純動畫影片（錄音模式）
  example-talking-head/  範例：真人出鏡影片的動畫合成
  <影片名稱>/            每支影片一個資料夾
reference/               畫面風格範例、剖面零件庫
fonts/                   思源黑體（Noto Sans TC，OFL 授權）
setup.sh                 雲端環境的安裝腳本
scripts/sync-skills.sh   改了 .claude/skills 之後，同步到 .agents/skills
```

## 規則

- 素材（錄音、影片）和成品 mp4 不進 Git（見 `.gitignore`），放 Google Drive。
- 畫面上的每個數字都要有出處，發布前逐條確認 `storyboard/sources.md`。
- 每一步 AI 都會停下來等你確認。
