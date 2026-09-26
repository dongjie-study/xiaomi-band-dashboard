# 数据小管家 · 腾讯云 CloudBase 版

> ⚠️ **当前状态：备用方案，暂未部署。**
> 小管家已通过 **Cloudflare Worker + 自定义域名 `data.xiaomi-exam.top`** 上线（国内可直连），无需腾讯云。
> 本目录作为备用：若将来 Cloudflare 域名方案出问题，或数据/调用量需要走国内节点，可按下方步骤部署，功能完全等价。

小米手环直播间销量数据问答小管家，跑在**腾讯云 CloudBase（云开发）**上，默认域名国内可直连（`*.app.tcloudbase.com`），同事不需要任何代理即可访问。

> 和 `assistant-server/`（Cloudflare 版）功能完全一致：同一套 DeepSeek function calling + 同样 5 个查询工具 + 同样的项目知识库（直播间归属表、口径定义）。
> 差别只在**数据来源**：Cloudflare 版从 GitHub raw 实时拉取；本版把数据打进函数包（因为国内云函数访问 GitHub raw 不通），所以**数据更新后需要重新部署一次**。

---

## 一、它是什么（结构）

```
cloudbase-assistant/
├── cloudbaserc.json                 # 部署配置（envId 从环境变量注入，密钥不落盘）
├── cloudfunctions/chat/
│   ├── index.js                     # 云函数主体（HTTP 入口 + 5 个查询工具 + 内嵌聊天页）
│   ├── package.json
│   └── assets/                      # ← 由 tools/build_cloudbase_assets.py 生成（不入 git）
└── test-local.cjs                   # 本地端到端测试（真实调 DeepSeek）
```

数据资产映射（由脚本从项目只读数据生成）：

| 函数内文件 | 来源 |
|---|---|
| `assets/history.json` | `sales_analysis/history.json` |
| `assets/band11_history.json` | `sales_analysis/band11_history.json` |
| `assets/daily_summary.json` | `sales_analysis/daily_summary.json` |
| `assets/anchor_records.json` | `主播业绩/anchor_records.json` |
| `assets/hourly.json.gz` | `sales_analysis/hourly/*.json`（117 天合并压缩，11MB → 1MB） |
| `assets/b10pro_history.json` | `sales_analysis/b10pro_history.json` |

---

## 二、部署（两条路，选一条）

### 前置：注册并登录腾讯云

1. 打开 https://cloud.tencent.com/ 注册（手机号即可），完成**实名认证**（个人认证，几分钟）
2. 开通 **云开发 CloudBase**：https://console.cloud.tencent.com/tcb → 新建环境
   - 环境名称：如 `xiaomi-data`
   - 计费方式：选**个人版 / 免费体验**（有免费额度：云函数调用次数、存储、CDN 流量足够内部使用）
   - 地域：就近（如上海）
   - 记下**环境 ID**（形如 `xiaomi-data-8g5xxxxxxxx`）

### 路线 A：命令行（推荐，快）

```powershell
# 1. 登录（会弹浏览器授权）
cd "C:\Users\Administrator\Desktop\小米手环直播间销量分析\cloudbase-assistant"
npx --yes -p @cloudbase/cli tcb login

# 2. 确认环境 ID
npx --yes -p @cloudbase/cli tcb env list

# 3. 生成数据资产（每次数据更新后都要跑一次）
cd ..
python tools/build_cloudbase_assets.py

# 4. 部署（设置 3 个环境变量后执行，密钥来自进程环境，不写进任何文件）
cd cloudbase-assistant
$env:TCB_ENV_ID="你的环境ID"; $env:ACCESS_ENABLED="true"; $env:ACCESS_CODE="xiaomi"; $env:DEEPSEEK_API_KEY="sk-xxxx"
npx --yes -p @cloudbase/cli tcb fn deploy chat

# 5. 建 HTTP 路由（把 /api 路径指到云函数；domain 填控制台里的默认域名）
npx --yes -p @cloudbase/cli tcb routes add -e "你的环境ID" -d '{\"domain\":\"你的环境ID.地域.app.tcloudbase.com\",\"routes\":[{\"path\":\"/api\",\"upstreamResourceType\":\"SCF\",\"upstreamResourceName\":\"chat\"}]}'
```

### 路线 B：控制台点击（不装命令行）

1. 云函数 → 新建云函数：名称 `chat`，运行时 **Node.js 18**，入口 `index.main`，超时 **60 秒**
2. 代码包上传：`cloudbase-assistant/chat-function.zip`（由 `python tools/build_cloudbase_assets.py --zip` 生成）
3. 环境变量（函数配置页）：
   | 变量名 | 值 |
   |---|---|
   | `ACCESS_ENABLED` | `true`（想关掉口令就改成 `false`） |
   | `ACCESS_CODE` | `xiaomi` |
   | `DEEPSEEK_API_KEY` | 你的 `sk-...` |
4. **HTTP 网关 → 路由管理 → 新建**：关联资源选「云函数 / chat」，触发路径填 `/api`，域名选默认域名
5. 得到访问地址：`https://<环境ID>.<地域>.app.tcloudbase.com/api`

---

## 三、验证

```bash
curl "https://<环境ID>.<地域>.app.tcloudbase.com/api/config"
# → {"enabled":true}

curl -X POST "https://<环境ID>.<地域>.app.tcloudbase.com/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"code":"xiaomi","messages":[{"role":"user","content":"9月24日小米官方手环直播间卖了多少台小米手环11？"}]}'
# → {"answer":"...1487 台..."}
```

浏览器直接打开 `https://<环境ID>.<地域>.app.tcloudbase.com/api` 也有一个**独立聊天页**（和 Cloudflare 版同款）。

本地自测（不需要部署）：

```bash
cd cloudbase-assistant
node test-local.cjs
# 会读取 ../assistant-server/.dev.vars 里的 key，真实调用 DeepSeek 跑 12 项检查
```

---

## 四、接入工作台

拿到域名后，打开工作台 → 「数据小管家」模块页 → 右上角**设置** → 粘贴

```
https://<环境ID>.<地域>.app.tcloudbase.com/api
```

（也可以直接把 `数据小管家/index.html` 里的 `API_BASE` 改成这个地址，然后 push）

---

## 五、日常维护

| 场景 | 动作 |
|---|---|
| 订单/业绩数据更新后 | `python tools/build_cloudbase_assets.py` 然后重新 `tcb fn deploy chat`（云端数据即最新） |
| 改口令 / 临时关口令 | 云函数 → 环境变量：改 `ACCESS_CODE` 或把 `ACCESS_ENABLED` 设为 `false`，保存即生效 |
| 换 DeepSeek key | 环境变量里改 `DEEPSEEK_API_KEY` |
| 看日志排错 | 控制台 → 云函数 chat → 日志，或 `npx -p @cloudbase/cli tcb fn log chat` |

**费用**：内部同事查询量下，云函数调用次数与 CDN 流量都在免费额度内；超出后按量计费（每万次调用几毛钱量级）。环境套餐若到期转付费，个人版约 ¥9.9/月。

**安全**：DeepSeek key 只放在云函数环境变量里（腾讯云侧加密存储），仓库和前端页面里都没有。
