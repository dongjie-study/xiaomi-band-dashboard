# history.json 字段速查（旧文档）

> **字段权威定义以 [`docs/02-数据字典.md`](docs/02-数据字典.md) 为准**，本文只保留「一眼看懂结构」的速查。
> 本文写于 2026-07，**2026-09-30 修正两处过期内容**：
> ① 补上 `zhumeng` / `feina` / `ningyun` / `lepan` / `chimu` / `mile_rooms` 六个团队数组；
> ② `_hourly_stats` 早已不内嵌在 `rooms` 里 —— 小时数据独立成 `sales_analysis/hourly/<日期>.json`。

## 顶层结构

```json
[
  {
    "date": "2026-06-01",          // YYYY-MM-DD（⚠️ 可能是 "NaT"，见 docs/06-踩坑#1）
    "total_orders": 1234,          // int — 当天总订单条数（下单口径，不扣退款）
    "total_revenue": 456789.12,    // float — 当天总实付金额（元）
    "avg_price": 370.12,           // float — 客单价 = revenue / orders
    "products": {                  // dict — 商品短名 → {orders, revenue, avg_price}
      "小米手环10": { "orders": 500, "revenue": 144000.0, "avg_price": 288.0 }
    },
    "rooms": {                     // dict — 直播间名 → room_summary
      "小米官方手环直播间": {
        "orders": 300,
        "revenue": 87000.0,
        "avg_price": 290.0,
        "products": { "小米手环10": { "orders": 200, "revenue": 57600.0, "avg_price": 288.0 } },
        "type": "我司"             // 团队名，取值见下
      }
    },
    "our_rooms": [...],            // 我司（当天实际出现的直播间，不是全量名单）
    "jixie_rooms": [...],          // 机械空间
    "zongheng_rooms": [...],       // 纵横
    "zhumeng_rooms": [...],        // 逐梦
    "feina_rooms": [...],          // 斐纳
    "ningyun_rooms": [...],        // 凝云
    "lepan_rooms": [...],          // 乐畔
    "chimu_rooms": [...],          // 炽木电商
    "mile_rooms": [...],           // 米乐
    "liangmi_rooms": [...],        // 良米
    "comp_rooms": [...],           // 全部竞对直播间
    "type_summary": {              // 团队名 → {orders, revenue, avg_price, rooms}
      "我司": { "orders": 500, "revenue": 144000.0, "avg_price": 288.0, "rooms": 6 }
    }
  }
]
```

> 一天一条，按日期升序；只有 `sales_analysis/daily_update.py`（由 `run_all.py sales` 调用）会写它。
> 各团队数组由 `daily_update.py` 按 `info["type"]` 过滤生成（`type` 取值：我司 / 机械空间 / 纵横 /
> 逐梦 / 斐纳 / 凝云 / 乐畔 / 炽木电商 / 米乐 / 良米）。

## 小时数据：已不在 rooms 里

小时明细独立成 `sales_analysis/hourly/<日期>.json`：
`{date, rooms: <同 history.json 的 rooms 结构>, _hourly_stats: {小时序号: {orders, revenue, products}}}`，
由 `sales_analysis/index.html` 按日期 `fetch`。详见 [`docs/02-数据字典.md`](docs/02-数据字典.md) 第二节。

## 团队归属（Team Classification）

以 `team_config.py` → `TEAM_MAP` 为准；**名单随时会新增，本文不再抄名单**（抄了就会过期）。
查归属看 [`直播间分类.md`](直播间分类.md) 与 [`docs/03-直播间与团队.md`](docs/03-直播间与团队.md)。
遇到两边都没出现过的新直播间名 → **先问用户**再入库，不要静默兜底归「良米」。

## 商品分类（Product Classification）

走 `product_classifier.py` → `classify_product()`；品类名与页面归类见 [`docs/03-直播间与团队.md`](docs/03-直播间与团队.md)。

## 脚本产出对照（易过期，完整清单见 docs/05）

| 脚本 | 产出 |
|------|------|
| `sales_analysis/daily_update.py` | `history.json`、`stats_data.js`（由 `run_all.py sales` 调用） |
| `sales_analysis/generate_dashboard.py` | 仪表盘 PNG ×3（被 `daily_update.py` 函数级 import，无 `__main__` 守卫） |
| `tools/generate_<月份>_summary.py` | `月度总结/<月>销量分析.html` |
| `archive/build_html.py`（已归档） | `节点总结/618复盘总结.html` |

## 想看别的

| 想了解 | 去哪 |
|--------|------|
| 各数据文件完整字段（`hourly/`、`daily_summary.json`、`stats_data.js`、`DAILY_RECORDS`、`modules.json`） | [`docs/02-数据字典.md`](docs/02-数据字典.md) |
| 数据怎么流动、谁写谁读 | [`docs/01-数据流.md`](docs/01-数据流.md) |
| 脚本清单（谁生成什么、谁已停用） | [`docs/05-脚本清单.md`](docs/05-脚本清单.md) |
| 每日流程 | [`WORKFLOW.md`](WORKFLOW.md) 顶部「⚡ 每日执行清单」 |
