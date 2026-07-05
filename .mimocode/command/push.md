---
description: Git add/commit/push 部署更新。用法: /push [commit message]
---

## Git 推送流程

工作目录: `C:\Users\Administrator\Desktop\小米手环直播间销量分析`

### 1. 检查状态
```bash
git status
git diff --stat
```

### 2. 提交并推送
```bash
git add -A
git commit -m "$ARGUMENTS"
git push
```

如果 `$ARGUMENTS` 为空，使用默认 commit message: `"chore: 更新数据和页面"`

### 3. 验证
```bash
git log --oneline -1
git status
```

### 注意事项
- 用户说"推送"、"帮我推送"、"推送一下"、"git push" 时均执行此流程
- 推送前确认数据完整，用户对数据丢失非常敏感
- 如果没有变更，告知用户即可，不要创建空提交
