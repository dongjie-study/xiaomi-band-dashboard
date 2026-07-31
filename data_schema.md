# history.json Data Schema

## Top-level structure

```json
[
  {
    "date": "2026-06-01",          // YYYY-MM-DD
    "total_orders": 1234,           // int — total orders for the day
    "total_revenue": 456789.12,     // float — total revenue (RMB)
    "avg_price": 370.12,            // float — average order price
    "products": {                   // dict — product_short_name → stats
      "小米手环10": {
        "orders": 500,
        "revenue": 144000.0,
        "avg_price": 288.0
      }
    },
    "rooms": {                      // dict — room_name → room_summary
      "小米官方手环直播间": {
        "orders": 300,
        "revenue": 87000.0,
        "avg_price": 290.0,
        "products": {               // same structure as top-level products
          "小米手环10": { "orders": 200, "revenue": 57600.0, "avg_price": 288.0 }
        },
        "type": "我司",             // team classification
        "_hourly_stats": {          // optional — hour-indexed breakdown
          "9": {
            "orders": 25,
            "revenue": 7200.0,
            "products": {
              "小米手环10": { "orders": 15, "revenue": 4320.0, "room_pct": 60.0, "market_pct": 13.2 }
            }
          }
        }
      }
    },
    "our_rooms": ["小米官方手环直播间", ...],     // list of room names for our team
    "jixie_rooms": [...],                          // 机械空间 rooms
    "zongheng_rooms": [...],                       // 纵横 rooms
    "liangmi_rooms": [...],                        // 良米 rooms
    "comp_rooms": [...],                           // all competitor rooms
    "type_summary": {                              // per-team aggregates
      "我司": { "orders": 500, "revenue": 144000.0, "avg_price": 288.0, "rooms": 6 }
    },
    "_hourly_stats": {                 // optional — day-level hourly breakdown
      "9": { "orders": 100, "revenue": 28800.0, "products": {...} }
    }
  }
]
```

## Team Classification

Rooms are classified using `team_config.py` → `TEAM_MAP`:
- **我司**: 小米官方手环直播间, 小米数码旗舰店, 小米官方手表, 小米官方耳机直播间, 小米手环10Pro直播间, 小米官旗手表直播间
- **机械空间**: 小米智能穿戴国补号, 小米智能穿戴授权号
- **纵横**: 小米官方手表直播号
- **凝云**: 小米手环官方直播间, 小米手环新品直播间, 小米手环直播间
- **良米**: default for anything not in the above

## Product Classification

Products are classified by `product_classifier.py` → `classify_product()`.
Key categories: 小米手环10, 小米手环10 Pro, 小米手环9 Pro, REDMI Watch 6, Xiaomi 开放式耳机, etc.

## Key Files

| Script | Input | Output |
|--------|-------|--------|
| `daily_update.py` | Excel (.xlsx) | `history.json` |
| `generate_dashboard.py` | history.json | dashboard.png, comparison.png |
| `build_html.py` (root) | 618_analysis_data.json | 618复盘总结.html |
| `generate_june_summary.py` | history.json | 六月销量分析.html |
