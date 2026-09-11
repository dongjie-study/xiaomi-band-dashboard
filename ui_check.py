# -*- coding: utf-8 -*-
"""UI 改造前后一致性校验。

用法: python ui_check.py <标签>      # 标签如 before / after_index
产出: _ui_<标签>.json  (关键数值 + 表格行数)
      _ui_<标签>_<页名>.png (桌面截图)
      _ui_<标签>_<页名>_mobile.png (移动端截图)
"""
import asyncio, json, subprocess, sys, time
from playwright.async_api import async_playwright

ROOT = r"C:\Users\Administrator\Desktop\小米手环直播间销量分析"
PORT = 8793

PAGES = [
    ("index",    "index.html",                          True),
    ("perf",     "主播业绩/业绩demo.html",               True),
    ("sales",    "sales_analysis/index.html",            True),
    ("sept",     "月度总结/九月销量分析.html",            True),
    ("aug",      "月度总结/八月销量分析.html",            True),
    ("june",     "月度总结/六月销量分析.html",            True),
    ("july",     "月度总结/七月销量分析.html",            True),
    ("violation","违规情况/report.html",                 True),
]

# 每页要钉住的关键数值/结构（选择器 -> 提取方式）
PROBES = {
    "index": {
        "statValues":  ("#statsRow .stat-value", "texts"),
        "statSubs":    ("#statsRow .stat-sub", "texts"),
        "sidebarItems":("#sidebarNav a", "count"),
        "cards":       ("#moduleGrid .module-card", "count"),
        "cardTitles":  ("#moduleGrid .module-card h3", "texts"),
        "breadcrumb":  ("#breadcrumb", "text"),
    },
    "perf": {
        "totalSales":  ("#totalSales", "text"),
        "activeAnchors":("#activeAnchors", "text"),
        "rows":        ("table tbody tr", "count"),
        "badgeRooms":  (".badge-room", "count"),
        "monthlyRows": ("#monthlySummaryBody tr", "count"),
        "detailRows":  ("#detailTableBody tr", "count"),
        "anchorStats": ("#anchorStatsBody tr", "count"),
        "championRows":("#dailyChampionsBody tr", "count"),
    },
    "sales": {
        "kpiCount":    (".kpi-card", "count"),
        "roomCards":   (".room-card", "count"),
        "rows":        ("table tbody tr", "count"),
        "provRows":    (".prow", "count"),
    },
    "sept": {
        "rows":        ("table tbody tr", "count"),
        "kpiCount":    (".kpi-card", "count"),
        "summary":     ("#summaryBox", "text"),
        "sections":    (".section", "count"),
    },
    "aug": {
        "rows":        ("table tbody tr", "count"),
        "kpiCount":    (".kpi-card", "count"),
        "sections":    (".section", "count"),
    },
    "june":   {"rows": ("table tbody tr", "count"), "kpiCount": (".kpi-card", "count"), "sections": (".section", "count")},
    "july":   {"rows": ("table tbody tr", "count"), "kpiCount": (".kpi-card", "count"), "sections": (".section", "count")},
    "violation": {
        "rows":        ("#detail-table tbody tr", "count"),
        "cards":       (".card", "count"),
        "charts":      (".chart", "count"),
    },
}

# 页面 JS 里引用的 id / selector —— 渲染后必须仍能解析（抓误改名）
async def collect_js_refs(pg, path):
    src = open(path, encoding="utf-8", errors="ignore").read()
    import re
    ids = sorted(set(re.findall(r"getElementById\(\s*['\"]([^'\"]+)['\"]", src)))
    sels = sorted(set(re.findall(r"querySelector(?:All)?\(\s*['\"]([^'\"]+)['\"]", src)))
    out = {}
    for i in ids:
        ok = await pg.evaluate("(id)=>!!document.getElementById(id)", i)
        out["#"+i] = ok
    for s in sels:
        if "${" in s or "+" in s:
            continue
        try:
            n = await pg.evaluate("(s)=>document.querySelectorAll(s).length", s)
            out[s] = n >= 0
        except Exception:
            out[s] = False
    return out


async def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    result = {}
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            # 这些页面有 localStorage 鉴权回跳，否则会被弹回首页
            ctx = await b.new_context(viewport={"width": 1500, "height": 1000})
            await ctx.add_init_script(
                "try{localStorage.setItem('mi_band_auth_v1','1')}catch(e){}")
            for name, rel, _ in PAGES:
                if not __import__("os").path.exists(__import__("os").path.join(ROOT, rel)):
                    result[name] = {"MISSING": True}
                    continue
                pg = await ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append("PAGEERROR: " + str(e)))
                pg.on("console", lambda m: errs.append("CONSOLE: " + m.text) if m.type == "error" else None)
                await pg.goto(f"http://localhost:{PORT}/{rel}", wait_until="domcontentloaded", timeout=90000)
                # 违规报告页依赖 CDN 的 echarts，沙箱里要等更久
                await pg.wait_for_timeout(12000 if name == "violation" else 6000)
                entry = {}
                for key, (sel, mode) in PROBES.get(name, {}).items():
                    try:
                        if mode == "texts":
                            v = await pg.eval_on_selector_all(sel, "e=>e.map(x=>x.innerText.trim())")
                        elif mode == "count":
                            v = await pg.eval_on_selector_all(sel, "e=>e.length")
                        else:
                            v = await pg.inner_text(sel)
                            v = v.strip()
                        entry[key] = v
                    except Exception as ex:
                        entry[key] = "ERR:" + type(ex).__name__
                entry["jsRefs"] = await collect_js_refs(
                    pg, __import__("os").path.join(ROOT, rel))
                entry["errors"] = errs
                result[name] = entry
                await pg.screenshot(path=f"_ui_{tag}_{name}.png")
                # 移动端
                await pg.set_viewport_size({"width": 700, "height": 1000})
                await pg.wait_for_timeout(900)
                await pg.screenshot(path=f"_ui_{tag}_{name}_mobile.png")
                # 移动端侧边栏是否溢出（对比侧边栏宽度与内容宽度）
                if name == "index":
                    entry["mobileSidebar"] = await pg.evaluate("""()=>{
                        const sb=document.querySelector('.sidebar');
                        const nav=document.getElementById('sidebarNav');
                        if(!sb||!nav) return null;
                        return { sbW: Math.round(sb.getBoundingClientRect().width),
                                 navScrollW: nav.scrollWidth };
                    }""")
                await pg.close()
            await b.close()
    finally:
        srv.terminate()
    json.dump(result, open(f"_ui_{tag}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # 简报
    for name, e in result.items():
        bad = [k for k, v in e.get("jsRefs", {}).items() if not v]
        print(f"[{name}] 错误:{len(e.get('errors',[]))} 取不到的选择器:{bad if bad else '无'}")
        if e.get("errors"):
            for x in e["errors"][:3]:
                print("    ", x[:160])


asyncio.run(main())
