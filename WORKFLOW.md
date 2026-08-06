# 每日数据处理工作流

## 🚨 核心判断：看文件名

| 文件名包含 | 执行动作 | 目标 |
|-----------|---------|------|
| **x.xx日订单** | 只更新 sales_analysis | 竞品销量看板 |
| **x.xx日业绩** | 只更新 业绩demo.html | 主播业绩面板 |

**两个流程互不交叉，不要同时执行。**

---

## 一、收到「x.xx日订单」→ 只更新销量看板

### 确认文件特征
列：选购商品 / 订单提交时间 / 订单状态 / 订单应付金额 / 直播间名称

### 步骤
```bash
# 1. 更新 业绩demo.html 的 DAILY_RECORDS（update_daily_html.py 会自动做这一步）
python update_daily_html.py "C:\Users\Administrator\Desktop\x.xx日订单.xlsx"

# 2. 更新 sales_analysis 销量看板
python run_all.py sales "C:\Users\Administrator\Desktop\x.xx日订单.xlsx"

# 3. 提交并推送
git add -A && git commit -m "feat: x.xx日订单数据更新" && git push
```

---

## 二、收到「x.xx日业绩」→ 只更新业绩面板

### 确认文件特征（Excel 格式）

每个直播间纵向堆叠排列：

| 起始行 | 直播间 |
|--------|--------|
| 第1行 | 小米数码旗舰店 |
| 第27行 | 小米官方手环直播间 |
| ... | 依次往下 |

列映射：
- **A列**: 主播名字
- **B列**: 主播名字
- **C列**: 场次 — A1/A2（上/下半场）、B1/B2、C1/C2、D1/D2、E
- **E列**: 每小时数据
- **F列**: 该主播今天该直播间总业绩
- **G列**: 日期

### 步骤
1. 解析 Excel → 提取每行 { roomId, shift, anchor, sales }
2. 生成 DAILY_RECORDS 条目插入 `主播业绩/业绩demo.html`
3. 提交并推送

---

## 三、自动提交

数据更新后自动 `git add -A && git commit && git push`，无需确认。
