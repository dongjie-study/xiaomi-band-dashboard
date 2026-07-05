---
description: 每日订单数据分析+汇总+推送。用法: /daily-order <Excel文件路径>
---

## 每日订单分析推送流程

用户提供了一个 Excel 订单文件路径: `$ARGUMENTS`

请按以下步骤执行（工作目录: `C:\Users\Administrator\Desktop\小米手环直播间销量分析`）：

### 1. 运行 daily_update.py 处理订单数据
```bash
cd "C:\Users\Administrator\Desktop\小米手环直播间销量分析\sales_analysis"
python daily_update.py "$ARGUMENTS"
```
- 如果报错（如编码问题、列名不匹配），检查 Excel 列名是否匹配（选购商品、订单提交时间、订单应付金额、达人昵称）
- 如果是新月份第一天，可能需要更新 TEAM_MAP 中新增的直播间

### 2. 重新生成当月汇总页面
根据当前月份选择对应脚本：
- 7月: `python generate_july_summary.py`
- 6月: `python generate_june_summary.py`
- 其他月份: 查找 `generate_<月份>_summary.py`

```bash
cd "C:\Users\Administrator\Desktop\小米手环直播间销量分析"
python generate_july_summary.py
```

### 3. 检查变更并推送
```bash
cd "C:\Users\Administrator\Desktop\小米手环直播间销量分析"
git status
git diff --stat
```
确认变更包含: `sales_analysis/history.json`, `sales_analysis/stats_data.js`, 月度汇总 HTML, 图表 PNG。

### 4. Git 提交并推送
```bash
git add -A
git commit -m "feat: 新增X月X日订单数据 - N单 ¥X GMV，更新仪表盘和对比图表"
git push
```
- commit message 中的数字从 daily_update.py 的输出中提取（总单数和总GMV）
- 用"推送"或"git push"即可，不需要用户重复说

### 注意事项
- 用户说"推送"时 = 执行 git push（项目规则）
- 每次添加完新数据都要同步推送（用户明确要求）
- PowerShell 生成的 JSON 可能带 UTF-8 BOM，Python 读取时用 `encoding='utf-8-sig'`
- 服务商分类规则: 我方=小米官方手表/手环/数码旗舰店等; 机械空间=智能穿戴授权号/国补号; 纵横=官方手表直播号; 凝云=手环官方/新品/直播间; 良米=其余
