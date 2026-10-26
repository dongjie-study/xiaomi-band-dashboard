#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""流量页浏览器校验（一次启动 chromium：布局契约 + 全口径冒烟 + 多宽度；默认不截图）。

    python -X utf8 traffic_analysis/page_check.py           # 快速档（≈30 秒）——日常数据日可选跑
    python -X utf8 traffic_analysis/page_check.py --deep    # 深度档：全部日期 × 全部口径逐图核数（改过页面/脚本后跑）
    python -X utf8 traffic_analysis/page_check.py --shots   # 额外把截图存到 _artifacts/

为什么快：以前 _artifacts/ 里三份脚本（check_traffic_layout / _verify_chart_scope / audit_traffic_page）
各起一次浏览器、各自固定 wait_for_timeout，一轮 5~10 分钟；这里合并成
「一次 chromium + 一个本地 http 服务 + 事件驱动等待（wait_for_function）」，默认档 ≈30 秒。

echarts：优先用本地缓存 _artifacts/_echarts.min.js（首次自动下载，之后离线且更快），
没有就退回页面自己的 CDN。窗口尺寸/断言沿用历史三份脚本，标准是「改页面后必须全绿」。
"""
import functools
import http.server
import io
import json
import math
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ECH_CACHE = os.path.join(ROOT, '_artifacts', '_echarts.min.js')
ECH_URL = 'https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js'

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OK_N = 0
BAD = []
T0 = time.time()


def ok(msg):
    global OK_N
    OK_N += 1
    print('  ✅ %s' % msg, flush=True)


def bad(msg):
    BAD.append(msg)
    print('  ❌ %s' % msg, flush=True)


def head(t):
    print('\n[%s]  (+%.1fs)' % (t, time.time() - T0), flush=True)


def rj(p):
    with io.open(p, encoding='utf-8') as f:
        return json.load(f)


def jround(v):
    return math.floor(float(v) + 0.5) if v >= 0 else -math.floor(-float(v) + 0.5)


def jsq(v, nd):
    return Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def ensure_echarts():
    """本地 echarts 缓存；没有就下载一次（失败返回 None，退回页面 CDN）。"""
    if os.path.exists(ECH_CACHE) and os.path.getsize(ECH_CACHE) > 500000:
        return ECH_CACHE
    try:
        os.makedirs(os.path.dirname(ECH_CACHE), exist_ok=True)
        subprocess.run(['curl.exe', '-4', '-sL', '--max-time', '90', '-o', ECH_CACHE, ECH_URL], timeout=150)
    except Exception:                                       # noqa: BLE001
        pass
    return ECH_CACHE if (os.path.exists(ECH_CACHE) and os.path.getsize(ECH_CACHE) > 500000) else None


INIT = ("try{ localStorage.setItem('mi_band_auth_v1','1'); localStorage.setItem('dg_code','xiaomi');"
        " window.__errs=[]; window.addEventListener('error', function(e){ window.__errs.push(String(e.message)); }, true);"
        " }catch(e){}")
HIDE_WIDGET = "() => { var s=document.createElement('style'); s.textContent='#assistantWidget,.assistant-widget,#dg-widget-host{display:none!important}'; document.head.appendChild(s); }"

LAYOUT = r"""
() => {
  function n(sel){ return document.querySelectorAll(sel).length; }
  function cols(sel){ var g=document.querySelector(sel); return g? getComputedStyle(g).gridTemplateColumns : null; }
  var C = document.getElementById('tfContent');
  var all = C ? C.innerText : '';
  var sus = [];
  ['NaN','undefined','Infinity','[object'].forEach(function(t){
    var m = all.split(t).length - 1; if (m) sus.push(t + '×' + m);
  });
  var cardR = C ? C.getBoundingClientRect() : null;
  var overflow = [];
  Array.prototype.forEach.call(C ? C.querySelectorAll('*') : [], function(e){
    if (e.classList.contains('tf-table-wrap') || e.tagName === 'CANVAS') return;
    var r = e.getBoundingClientRect();
    var escapes = cardR ? (r.right - cardR.right > 1) : true;
    if (escapes && e.scrollWidth > e.clientWidth + 2 && e.clientWidth > 0 &&
        getComputedStyle(e).overflowX !== 'auto' && getComputedStyle(e).overflowX !== 'scroll')
      overflow.push(e.tagName + '.' + (e.className||'').toString().split(' ')[0]);
  });
  return {
    grids: { A: n('#tfGridA .tf-metric'), B: n('#tfGridB .tf-metric'), C: n('#tfGridC .tf-metric') },
    colsC: cols('#tfGridC'),
    metricLinked: n('.tf-metric.linked'),
    channelRows: n('#tfChannelBody tr'),
    ruleRows: n('#tfRuleRows tr'),
    compareRows: n('#tfCompareBody tr'),
    peerRows: n('#tfPeerBody tr'),
    meRow: n('#tfCompareBody tr.me'),
    canvasN: n('#tfContent canvas'),
    chartHeights: Array.prototype.map.call(document.querySelectorAll('.tf-chart'), function(e){ return Math.round(e.getBoundingClientRect().height); }),
    chChips: n('#tfChSwitch .tf-chip'),
    mChips: n('#tfChMetrics .tf-chip'),
    chCanvas: n('#chartChTrend canvas'),
    chSub: (document.getElementById('tfChTrendSub')||{}).textContent || '',
    scrollX: document.documentElement.scrollWidth > window.innerWidth + 2,
    statusText: (document.getElementById('tfStatus')||{}).innerText || '',
    headline: (document.getElementById('tfHeadline')||{}).innerText || '',
    pills: (document.getElementById('tfReportPills')||{}).innerText || '',
    extra: (document.getElementById('tfExtra')||{}).innerText || '',
    sus: sus, overflowN: overflow.length, overflow: overflow.slice(0, 4), errors: (window.__errs||[]).slice()
  };
}
"""

SNAP = r"""
() => {
  const o = id => { const c = CHARTS[id]; return c ? c.getOption() : null; };
  const f = o('chartFunnel'), p = o('chartChannel'), t = o('chartTrend'), rt = o('chartRate');
  const ct5 = o('chartChTrend');
  const last = s => (s && s.data && s.data.length) ? s.data[s.data.length - 1] : null;
  return {
    scope: document.getElementById('scopeSelect').value,
    funnel: f ? (f.series[0].data || []).map(v => Math.round(v)) : null,
    pie: p ? (p.series[0].data || []).map(x => x.name + '=' + x.value) : null,
    trendLast: t ? (t.series || []).map(last) : null,
    trendAll: t ? (t.series || []).map(s => s.data) : null,
    trendXLast: t ? (t.xAxis[0].data || []).slice(-1)[0] : null,
    rateLast: rt ? (rt.series || []).map(last) : null,
    chName: ct5 && ct5.series && ct5.series[0] ? ct5.series[0].name : null,
    chData: ct5 && ct5.series && ct5.series[0] ? ct5.series[0].data : [],
    chMetric: (typeof CH_TREND !== 'undefined') ? CH_TREND.metric : null,
    sub: (document.getElementById('tfTrendSub') || {}).textContent || '',
    fsub: (document.getElementById('tfFunnelSub') || {}).textContent || '',
    psub: (document.getElementById('tfPieSub') || {}).textContent || ''
  };
}
"""


def main():
    deep = '--deep' in sys.argv
    shots = '--shots' in sys.argv
    ech = ensure_echarts()

    idx = rj(os.path.join(HERE, 'data', 'index.json'))
    days = [d['date'] for d in idx['days']]
    rooms_by_day = {d['date']: (d.get('rooms') or []) for d in idx['days']}
    last_day = days[-1]

    print('=' * 68)
    print('  流量页校验 · %s档 · %d 天数据（末条 %s）' % ('深度' if deep else '快速', len(days), last_day))
    print('  echarts：%s' % ('本地缓存 ' + os.path.relpath(ech, ROOT) if ech else '页面 CDN'))
    print('=' * 68)

    class Srv(socketserver.ThreadingTCPServer):     # 必须多线程：单线程 backlog 一满，浏览器就报 ERR_CONNECTION_REFUSED
        allow_reuse_address = True
        daemon_threads = True
        request_queue_size = 128

    srv = Srv(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    URL = 'http://127.0.0.1:%d/traffic_analysis/index.html' % port

    from playwright.sync_api import sync_playwright

    LOCAL = '127.0.0.1:%d' % port

    def on_console(m):
        """只把「本页 / 本地资源」的报错算失败：小管家的外部后端（data.xiaomi-exam.top）失败不算页面缺陷。"""
        if m.type != 'error':
            return
        loc = (m.location or {}).get('url') or ''
        if loc and LOCAL not in loc:
            return
        BAD.append('console.error: %s（%s）' % (m.text[:90], loc or '无 URL'))

    def new_page(b, w, h):
        pg = b.new_page(viewport={'width': w, 'height': h})
        pg.add_init_script(INIT)
        pg.on('pageerror', lambda e: BAD.append('pageerror: %s' % e))
        pg.on('console', on_console)
        pg.on('requestfailed', lambda r: BAD.append('请求失败: %s' % r.url) if LOCAL in r.url else None)
        if ech:
            pg.route('**/echarts*.js', lambda route: route.fulfill(path=ech, content_type='application/javascript'))
        return pg

    def ready(pg, timeout=30000):
        pg.goto(URL, wait_until='domcontentloaded', timeout=60000)
        pg.wait_for_function("() => window.INDEX && document.querySelectorAll('#tfCompareBody tr').length > 0", timeout=timeout)
        pg.wait_for_function("() => document.querySelectorAll('#tfContent canvas').length >= 5", timeout=timeout)
        pg.evaluate(HIDE_WIDGET)

    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()

            # ---------- 1. 布局契约（最新一天 · 全店 · 1500 宽） ----------
            head('1 布局契约（%s 全店 1500×1000）' % last_day)
            pg = new_page(b, 1500, 1000)
            ready(pg)
            mini = pg.evaluate(LAYOUT)
            exp_rows = len(rj(os.path.join(HERE, 'reports', last_day[:4], last_day, '全店.json')).get('channels') or [])
            if mini['grids'] != {'A': 4, 'B': 4, 'C': 8}:
                bad('指标卡张数不是 4/4/8：%s' % mini['grids'])
            if len((mini['colsC'] or '').split()) != 4:
                bad('效率指标网格不是 4 列：%s' % mini['colsC'])
            if mini['metricLinked'] != 6:
                bad('可联动指标卡 %d 张（期望 6）' % mini['metricLinked'])
            if mini['channelRows'] != exp_rows:
                bad('渠道明细 %d 行 ≠ 日报 %d 行' % (mini['channelRows'], exp_rows))
            if mini['ruleRows'] < 1 or mini['compareRows'] < 1 or mini['peerRows'] < 1:
                bad('规则/对比/同业表有空：rule=%s cmp=%s peer=%s' % (mini['ruleRows'], mini['compareRows'], mini['peerRows']))
            if mini['canvasN'] != 5:
                bad('图 %d 张（期望 5）' % mini['canvasN'])
            if any(h < 200 or h > 420 for h in mini['chartHeights']):
                bad('图高异常：%s' % mini['chartHeights'])
            if mini['scrollX']:
                bad('1500 宽出现横向滚动')
            if last_day not in mini['statusText'] or last_day not in mini['headline']:
                bad('状态条/一句话结论没写最新日期 %s' % last_day)
            if mini['sus']:
                bad('正文出现可疑文本 %s' % mini['sus'])
            if mini['overflowN']:
                bad('元素溢出 %d 处：%s' % (mini['overflowN'], mini['overflow']))
            if mini['errors']:
                bad('window.onerror: %s' % mini['errors'][:3])
            if not BAD:
                ok('指标卡 4/4/8（效率 4 列）、渠道 %d 行、规则 %d 行、对比 %d 行、图 5 张 %s、无横向滚动、无 JS 报错'
                   % (mini['channelRows'], mini['ruleRows'], mini['compareRows'], mini['chartHeights']))
            if shots:
                pg.screenshot(path=os.path.join(ROOT, '_artifacts', '_pc_%s_top.png' % last_day.replace('-', '')))

            # ---------- 1b. 渠道走势卡（chips 与表格同源 / 指标切换必须引自日报） ----------
            rep_all = rj(os.path.join(HERE, 'reports', last_day[:4], last_day, '全店.json'))
            chn = [c['name'] for c in (rep_all.get('channels') or [])]
            win1 = [d for d in days if d <= last_day][-14:]

            def ch_series(metric_key):
                """按日报逐日拼出「某渠道某指标」的期望序列（缺天 = None）"""
                out = []
                for d in win1:
                    p = os.path.join(HERE, 'reports', d[:4], d, '全店.json')
                    rows = (rj(p).get('channels') or []) if os.path.exists(p) else []
                    hit = [c for c in rows if c['name'] == chn[0]]
                    if not hit:
                        out.append(None); continue
                    v = hit[0].get(metric_key)
                    out.append(None if v is None else float(v))
                return out

            ct = pg.evaluate("""() => { const o = CHARTS.chartChTrend.getOption();
                return { chips: document.querySelectorAll('#tfChSwitch .tf-chip').length,
                         names: Array.prototype.map.call(document.querySelectorAll('#tfChSwitch .tf-chip'), b => b.getAttribute('data-ch')),
                         mchips: document.querySelectorAll('#tfChMetrics .tf-chip').length,
                         sub: (document.getElementById('tfChTrendSub')||{}).textContent || '',
                         meta: (document.getElementById('tfChTrendMeta')||{}).textContent || '',
                         yname: o.yAxis[0].name,
                         series: o.series.map(s => ({ name: s.name, data: s.data })) }; }""")
            if ct['chips'] != len(chn) or ct['names'] != chn:
                bad('渠道走势渠道 chips %d 个 ≠ 表格 %d 个（或顺序不一致）' % (ct['chips'], len(chn)))
            if ct['mchips'] != 13:
                bad('渠道走势指标 chips %d 个（期望 13）' % ct['mchips'])
            if not ct['sub'].startswith('全店') or chn[0] not in ct['sub']:
                bad('渠道走势副标题不对：%s' % ct['sub'])
            if not ct['meta'] or '峰值' not in ct['meta']:
                bad('渠道走势概览行没渲染：%s' % ct['meta'])
            if ct['series'][0]['name'] != chn[0]:
                bad('渠道走势默认渠道不是表格第一名：%s' % ct['series'][0]['name'])
            # 默认只画渠道自己的曲线（叠加整体线会把渠道曲线压扁），勾选后才有第二条
            if len(ct['series']) != 1:
                bad('渠道走势默认应只有 1 条曲线，实际 %d 条：%s' % (len(ct['series']), [s['name'] for s in ct['series']]))
            cmp_n = pg.evaluate("() => document.querySelectorAll('#tfChCompare').length")
            if cmp_n != 1:
                bad('渠道走势缺少「叠加该口径整体」勾选框')
            else:
                pg.check('#tfChCompare')
                pg.wait_for_function("() => CHARTS.chartChTrend.getOption().series.length === 2", timeout=8000)
                two = pg.evaluate("() => CHARTS.chartChTrend.getOption().series.map(s => s.name)")
                if not two[1].startswith('全店'):
                    bad('勾选后第二条曲线不是「该口径整体」：%s' % two)
                pg.uncheck('#tfChCompare')
                pg.wait_for_function("() => CHARTS.chartChTrend.getOption().series.length === 1", timeout=8000)
            exp_v = ch_series('views')
            got_v = [None if v is None else float(v) for v in ct['series'][0]['data']]
            if got_v != exp_v:
                bad('渠道走势「观看次数」序列与日报不符：%s' % got_v[:4])
            # 指标 chips 切换：支付金额（保留 2 位小数）
            pg.click('#tfChMetrics .tf-chip[data-m="paid_amount"]')
            pg.wait_for_function("() => CHARTS.chartChTrend.getOption().yAxis[0].name === '元'", timeout=10000)
            exp_p = ch_series('paid_amount')
            got_p = pg.evaluate("() => CHARTS.chartChTrend.getOption().series[0].data")
            if [None if v is None else round(float(v), 2) for v in got_p] != [None if v is None else round(v, 2) for v in exp_p]:
                bad('渠道走势「支付金额」序列与日报不符')
            pg.click('#tfChMetrics .tf-chip[data-m="views"]')
            pg.wait_for_function("() => CHARTS.chartChTrend.getOption().yAxis[0].name === '次'", timeout=10000)
            # 渠道 chips 切换：点第 3 个渠道 → 表格该行高亮、副标题跟着变
            if len(chn) >= 3:
                pg.click('#tfChSwitch .tf-chip[data-ch="%s"]' % chn[2].replace('"', '\\"'))
                pg.wait_for_function("(n) => (document.getElementById('tfChTrendSub')||{}).textContent.indexOf(n) >= 0",
                                     arg=chn[2], timeout=10000)
                sel_n = pg.evaluate("() => document.querySelectorAll('#tfChannelBody tr.sel').length")
                if sel_n != 1:
                    bad('点渠道 chip 后表格高亮行 %d ≠ 1' % sel_n)
                pg.click('#tfChSwitch .tf-chip[data-ch="%s"]' % chn[0].replace('"', '\\"'))
                pg.wait_for_function("(n) => (document.getElementById('tfChTrendSub')||{}).textContent.indexOf(n) >= 0",
                                     arg=chn[0], timeout=10000)
            ok('渠道走势卡：%d 个渠道 chips（与表格同序）、13 个指标 chips、观看次数/支付金额序列与日报逐点一致、chip 切换联动表格' % len(chn))

            # ---------- 2. 全部口径冒烟（最新一天） ----------
            head('2 全口径冒烟（%s：全店 + %d 间）' % (last_day, len(rooms_by_day[last_day])))
            scope_bad = []
            src_files = rj(os.path.join(HERE, 'data', last_day[:4], '%s.json' % last_day)).get('source_files') or {}
            for scope in ['全店'] + rooms_by_day[last_day]:
                rep = rj(os.path.join(HERE, 'reports', last_day[:4], last_day, '%s.json' % scope))
                nrow = len(rep.get('channels') or [])
                first = int(round(rep['metrics']['funnel'][0]['value']))
                pg.evaluate("(s) => { if (window.SCOPE !== s) switchScope(s); }", scope)
                try:
                    # 渲染屏障：漏斗首段 == 该口径日报的曝光。比「等固定毫秒」可靠，也不会读到上一口径的旧 DOM
                    pg.wait_for_function(
                        "(v) => { var c = window.CHARTS && CHARTS.chartFunnel; var o = c && c.getOption();"
                        " return !!o && Math.round(o.series[0].data[0]) === v; }", arg=first, timeout=20000)
                    pg.wait_for_function("(n) => document.querySelectorAll('#tfChannelBody tr').length === n", arg=nrow, timeout=10000)
                except Exception:                           # noqa: BLE001
                    scope_bad.append('%s 没切过去（漏斗首段应为 %d）' % (scope, first))
                    continue
                m = pg.evaluate(LAYOUT)
                if m['canvasN'] != 5:
                    scope_bad.append('%s 图 %d 张' % (scope, m['canvasN']))
                if m['channelRows'] != nrow:
                    scope_bad.append('%s 渠道 %d ≠ %d' % (scope, m['channelRows'], nrow))
                if m['sus']:
                    scope_bad.append('%s 可疑文本 %s' % (scope, m['sus']))
                if m['scrollX']:
                    scope_bad.append('%s 横向滚动' % scope)
                exp_me = 0 if scope == '全店' else 1
                if m['meRow'] != exp_me:
                    scope_bad.append('%s 高亮行 %d ≠ %d' % (scope, m['meRow'], exp_me))
                if scope == '全店':
                    if ('%d 个源文件' % len(rooms_by_day[last_day])) not in m['statusText']:
                        scope_bad.append('全店 状态条没写「%d 个源文件」' % len(rooms_by_day[last_day]))
                elif (src_files.get(scope) or '') not in m['statusText']:
                    scope_bad.append('%s 状态条没写源表名 %s' % (scope, src_files.get(scope)))
            if scope_bad:
                bad('；'.join(scope_bad[:6]))
            else:
                ok('%d 个口径全部渲染正常（图 5 张、渠道行数与日报一致、无 JS 报错）' % (1 + len(rooms_by_day[last_day])))

            # ---------- 3. 多宽度 ----------
            head('3 多宽度（1100 / 760 / 420）')
            w_bad = []
            for w in (1100, 760, 420):
                pg2 = new_page(b, w, 1000)
                ready(pg2, timeout=30000)
                m2 = pg2.evaluate(LAYOUT)
                if m2['scrollX']:
                    w_bad.append('%d 宽横向滚动' % w)
                if m2['canvasN'] != 5:
                    w_bad.append('%d 宽图 %d 张' % (w, m2['canvasN']))
                if shots:
                    pg2.screenshot(path=os.path.join(ROOT, '_artifacts', '_pc_%d.png' % w), full_page=(w == 420))
                pg2.close()
            if w_bad:
                bad('；'.join(w_bad))
            else:
                ok('1100 / 760 / 420 三种宽度都没有横向滚动，图都渲染')

            # ---------- 4. 深度档：全部日期 × 全部口径逐图核数 ----------
            if deep:
                head('4 深度档：全部日期 × 全部口径（漏斗 / 占比 / 趋势 / 转化率曲线）')
                pg3 = new_page(b, 1400, 1000)
                ready(pg3, timeout=45000)
                combos = 0
                errs = []
                for day in days:
                    pg3.evaluate("(d) => showDay(d)", day)
                    pg3.wait_for_function("(d) => document.getElementById('tfStatus').innerText.indexOf(d) >= 0", arg=day, timeout=20000)
                    for scope in ['全店'] + rooms_by_day[day]:
                        rep = rj(os.path.join(HERE, 'reports', day[:4], day, '%s.json' % scope))
                        pg3.evaluate("(s) => { if (window.SCOPE !== s) switchScope(s); }", scope)
                        try:
                            pg3.wait_for_function(
                                "(v) => { var c = window.CHARTS && CHARTS.chartFunnel; var o = c && c.getOption();"
                                " return !!o && Math.round(o.series[0].data[0]) === v; }",
                                arg=int(round(rep['metrics']['funnel'][0]['value'])), timeout=20000)
                            # 再等趋势图副标题跟上这一天（趋势是异步 reloadCharts 画的）
                            pg3.wait_for_function("(d) => document.getElementById('tfTrendSub').textContent.indexOf(d) >= 0",
                                                  arg=day[5:], timeout=20000)
                        except Exception:                   # noqa: BLE001
                            errs.append('%s %s 没切过去' % (day, scope))
                            continue
                        got = pg3.evaluate(SNAP)
                        m, tot = rep['metrics'], rep['totals']
                        combos += 1
                        exp_f = [int(round(x['value'])) for x in m['funnel']]
                        if got['funnel'] != exp_f:
                            errs.append('%s %s 漏斗 %s != %s' % (day, scope, got['funnel'], exp_f))
                        exp_p = ['%s=%d' % (c['name'], int(round(c.get('views') or 0))) for c in (rep.get('channels') or [])[:8]]
                        if got['pie'] != exp_p:
                            errs.append('%s %s 占比 %s != %s' % (day, scope, got['pie'], exp_p))
                        exp_t = [jround(tot['impressions']), jround(tot['views']), float(jsq(m['exposure_view_rate'] * 100, 2))]
                        if got['trendLast'] != exp_t:
                            errs.append('%s %s 趋势末点 %s != %s' % (day, scope, got['trendLast'], exp_t))
                        if got['trendXLast'] != day[5:]:
                            errs.append('%s %s 趋势末标签 %s' % (day, scope, got['trendXLast']))
                        exp_r = [float(jsq(m[k] * 100, 2)) for k in ('exposure_view_rate', 'product_ctr', 'click_cvr', 'new_follower_rate')]
                        if got['rateLast'] != exp_r:
                            errs.append('%s %s 转化率末点 %s != %s' % (day, scope, got['rateLast'], exp_r))
                        win = [d for d in days if d <= day][-14:]
                        e_imp, e_views, e_evr = [], [], []
                        for d in win:
                            p = os.path.join(HERE, 'reports', d[:4], d, '%s.json' % scope)
                            if not os.path.exists(p):
                                e_imp.append(None); e_views.append(None); e_evr.append(None); continue
                            rr = rj(p)
                            e_imp.append(jround(rr['totals']['impressions']))
                            e_views.append(jround(rr['totals']['views']))
                            e_evr.append(float(jsq(rr['metrics']['exposure_view_rate'] * 100, 2)))
                        if got['trendAll'] != [e_imp, e_views, e_evr]:
                            errs.append('%s %s 趋势序列与日报不符' % (day, scope))
                        # 渠道走势：默认渠道的「观看次数」逐日序列也要与日报一致
                        if got['chMetric'] != 'views':
                            errs.append('%s %s 渠道走势指标不是默认 views' % (day, scope))
                        e_ch = []
                        for d in win:
                            p2 = os.path.join(HERE, 'reports', d[:4], d, '%s.json' % scope)
                            rows2 = (rj(p2).get('channels') or []) if os.path.exists(p2) else []
                            hit2 = [c for c in rows2 if c['name'] == got['chName']]
                            e_ch.append(None if not hit2 else (None if hit2[0].get('views') is None else float(hit2[0]['views'])))
                        g_ch = [None if v is None else float(v) for v in got['chData']]
                        if g_ch != e_ch:
                            errs.append('%s %s 渠道走势 %s 序列与日报不符' % (day, scope, got['chName']))
                if errs:
                    bad('深度档 %d 组合中 %d 处不一致：%s' % (combos, len(errs), errs[:5]))
                else:
                    ok('深度档 %d 个「日期 × 口径」组合，四张图与日报逐点一致' % combos)

            b.close()
    finally:
        srv.shutdown()

    print('\n' + '=' * 68)
    if BAD:
        print('  ❌ 失败 %d 条 / 通过 %d 条（用时 %.1fs）' % (len(BAD), OK_N, time.time() - T0))
        for x in BAD[:15]:
            print('     - %s' % x)
        return 1
    print('  ✅ 全部通过（%d 条，用时 %.1fs）' % (OK_N, time.time() - T0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
