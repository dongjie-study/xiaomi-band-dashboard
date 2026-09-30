---
description: 每日订单数据分析+汇总+推送。用法: /daily-order <Excel文件路径>
---

## 每日订单推送流程

用户提供了一个 Excel 订单文件路径: `$ARGUMENTS`
工作目录: `C:\Users\Administrator\Desktop\小米手环直播间销量分析`

> ⚠️ 本文件只是**入口**。规则以 `WORKFLOW.md` 顶部「⚡ 每日执行清单」为唯一准绳 ——
> 先读它，按 **🅰️ 收到 x.xx日订单.xlsx → 7 步** 执行，不要跳步、不要凭记忆简化。

### 0. 先认清规则与归属
- 日常流程 / 自校验 / 提交清单 / 回报格式 → `WORKFLOW.md`
- 字段含义、页面结构、脚本谁死谁活 → `docs/00-索引.md`
- 直播间属于哪个团队 → `直播间分类.md`；**没出现过的新直播间先问用户**，不要静默归「良米」

### 1. 先看进度，避免重复入库
```bash
cd "C:/Users/Administrator/Desktop/小米手环直播间销量分析"
python band11_review.py status
```
`history 最新` 已经等于手上这份文件的日期 → **停下来问用户**是覆盖还是忽略，不要直接重跑。

### 2. 入库（只走 run_all.py，不要单独跑 daily_update.py）
```bash
python run_all.py sales "$ARGUMENTS"
```
- 列名逐月会变（`订单提交时间`/`支付完成时间`、`直播间名称`/`达人昵称`），**看含义不看字面**
- 报错先查列名是否含 `选购商品` + `订单状态` + `订单应付金额` + 一个时间列 + 一个直播间列
- 单独跑 `daily_update.py` 会绕过自校验与页面刷新，禁止

### 3. 自校验
按 `WORKFLOW.md`「✅ 自校验三条铁律」逐条核对，**有一条不过就停下来查**，不许带着疑问提交。

### 4. 看事实 → 写总结 → 落库
```bash
python band11_review.py context x.xx
# 写 sales_analysis/daily_review_input/YYYY-MM-DD.json（rating/good/bad/watch，每段 ≤90 字）
python band11_review.py add YYYY-MM-DD
python generate_band11_target.py   # 跑前先关掉 Excel 里打开的进度表，否则 PermissionError
```
首销月附加步骤（上面前三条）只在 **2026-09-07 ~ 10-07** 需要，之后跳过。

### 5. 提交推送
```bash
git status
git diff --stat                        # 确认没有多余文件被带进来
git add <精确列出本次改动的文件>         # ⚠️ 禁止 git add -A：工作区常年躺着别人的半成品
git commit -m "feat: x.xx日订单数据更新 - N单 ¥X"
git pull --rebase && git push
```
- commit message 里的总单数 / 总 GMV 取自 `run_all.py` 的输出
- 用户说「推送」= 执行 `git push`；日期前缀的 Excel 视为授权跑完整条流程

### 6. 回报
按 `WORKFLOW.md`「📣 回报格式」一次性给结论，不要中途逐步确认。

### 月度汇总页（不是每日必做）
当月月度页由 `tools/generate_<月份>_summary.py` 生成（**生成的 HTML 不要手改**），需要时再跑；
完整脚本清单见 `docs/05-脚本清单.md`。
