---
description: Git add/commit/push 部署更新。用法: /push [commit message]
---

## Git 推送流程

工作目录: `C:\Users\Administrator\Desktop\小米手环直播间销量分析`
规则以 `WORKFLOW.md` 顶部「📦 提交清单」为准。

### 1. 检查状态（先看清改了哪些文件）
```bash
git status
git diff --stat
```

### 2. 精确暂存 → 提交
```bash
git add <本次改动的文件，逐个列出>
git commit -m "$ARGUMENTS"
```
- ⚠️ **禁止 `git add -A` / `git add .`**（项目铁律 2）：工作区常年躺着别人的半成品与临时文件
  （如 `直播间销量汇总工具.html`、`.lexiang-sync-state.json`、`_artifacts/`、`tools/upload_to_lexiang.py`），
  一条 `-A` 会把它们全扫进提交。
- 不确定哪些文件属于本次改动 → **停下来问用户**，不要猜、不要用 `-A` 兜底。
- `$ARGUMENTS` 为空时用默认 message：`chore: 更新数据和页面`

### 3. 推送
```bash
git pull --rebase
git push
```
push 被拒（远程有新提交）：`git stash` → `git pull --rebase` → `git stash pop`（见 `WORKFLOW.md`）。

### 4. 验证
```bash
git log --oneline -1
git status
```

### 注意事项
- 用户说「推送」「帮我推送」「推送一下」「git push」时均执行此流程
- 推送前确认数据完整，用户对数据丢失非常敏感
- 没有任何变更就如实告诉用户，**不要建空提交**
