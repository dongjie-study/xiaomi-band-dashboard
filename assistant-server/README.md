# 数据小管家（xiaomi-data-assistant）

给同事用的项目数据问答入口：网页聊天 → DeepSeek（function calling）→ 实时查 GitHub 仓库数据 → 自然语言回答。

- **问销量**：某天/某区间、某直播间、某商品、某团队（订单口径）
- **问小时分布**：某天几点出单高峰
- **问主播业绩**：每主播每班次 GSV（未扣退款口径）
- **问每日总结**：官方 好/差/盯 三段式复盘
- **问首销月进度**：手环11 累计 vs 60000 目标、我司 vs 良米

数据源 = 本仓库 GitHub raw，**每天正常跑完订单/业绩流程并 push，小管家自动就是最新数据**，无需任何额外同步。

## 部署（只做一次）

```bash
cd assistant-server
npm install -g wrangler        # 或用 npx 代替
npx wrangler login            # 浏览器登录 Cloudflare 账号
npx wrangler secret put DEEPSEEK_API_KEY   # 粘贴 DeepSeek 的 sk-... key（不进代码不进 git）
npx wrangler deploy
```

部署完会得到 `https://xiaomi-data-assistant.<你的子域>.workers.dev`，微信里直接发这个链接就能用。

## 口令管理（随时开/关，不用重新部署）

配置在 Cloudflare 控制台：**Workers → xiaomi-data-assistant → Settings → Variables and Secrets**

| 变量 | 作用 | 改法 |
|---|---|---|
| `ACCESS_ENABLED` | `"true"`=要口令 / `"false"`=关掉口令 | 控制台改完点保存**立即生效** |
| `ACCESS_CODE` | 口令本体（当前 `xiaomi`） | 同上，随时换 |

也可改 `wrangler.toml` 的 `[vars]` 后重新 `deploy`，效果一样。

## 数据更新链路

| 数据 | 谁更新 | 小管家怎么拿到 |
|---|---|---|
| 每日销量 / 小时 / 总结 / 首销月 | 订单流程 push 后自动 | 直接拉 `sales_analysis/*.json` |
| **主播业绩** | 业绩流程更新 `业绩demo.html` 后，**要跑一次** `PYTHONUTF8=1 python tools/extract_anchor_records.py` 并提交 | 拉 `主播业绩/anchor_records.json` |

> ⚠️ 业绩流程的铁律不变：`业绩demo.html` 仍由业绩流程维护，抽取脚本**只读**它。

## 本地测试

```bash
cd assistant-server
node test.mjs        # 需要 .dev.vars 里有真实 DEEPSEEK_API_KEY，端到端真实调用
```

## 花费与额度

- Cloudflare Workers 免费版：每天 10 万次请求，内部用不完
- DeepSeek：每次问答约消耗几万 token（含工具查询结果），按官方价格一次问答约几厘钱
- GitHub raw 有带宽限额但对小流量无压力；Worker 内置 10 分钟缓存，同一问题高频重复也只拉一次
