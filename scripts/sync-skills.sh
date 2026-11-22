#!/usr/bin/env bash
# 技能的正本在 .claude/skills（Claude Code 讀這裡），ChatGPT Codex 讀 .agents/skills。
# 改完 .claude/skills 之後跑這支，把內容複製一份過去：  bash scripts/sync-skills.sh
set -e
cd "$(dirname "$0")/.."
rm -rf .agents/skills
mkdir -p .agents
cp -r .claude/skills .agents/skills
# Codex 用的技能路徑：把說明裡的 .claude/skills 改成 .agents/skills
grep -rl "\.claude/skills" .agents/skills | xargs -r sed -i 's#\.claude/skills#.agents/skills#g'
echo "已同步 $(ls .agents/skills | wc -l) 個技能到 .agents/skills"
