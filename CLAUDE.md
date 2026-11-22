# 給 AI 的說明（Claude Code 讀這個檔；ChatGPT Codex 讀 AGENTS.md，內容相同）

這個 repo 是做 IG／Reels 知識型短影音的工具包。使用者大多不寫程式，請用繁體中文、白話回覆。

- 技能在 `.agents/skills/`（Codex）和 `.claude/skills/`（Claude Code），內容相同。
- 使用者想做影片 → 用 reel-pipeline 技能。`brands/` 底下沒有正式品牌（只有 `_example-` 開頭的範例）→ 先用 brand-setup 技能。
- **每一步做完都停下來**，等使用者確認才往下。
- 畫面上的數字、研究都要有出處（`storyboard/sources.md`），守則在 `broll-video/references/compliance.md` 和 `brands/<品牌>/compliance.md`。
- 不要把任何金鑰（API key）寫進檔案或 commit。
- 做完一個段落就 commit，讓使用者在 GitHub 看得到；素材和成品不進 Git（見 `.gitignore`），要交給使用者的 mp4 用 `git add -f`。
- 剛建好環境、或渲染出錯時，先跑 `bash .claude/skills/broll-video/scripts/check-setup.sh` 看缺什麼。
