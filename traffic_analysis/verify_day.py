#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""流量单日复核（纯 Python：不启动浏览器、不联网，正常 < 3 秒）。

每天入库后跑这一条就够：
    python -X utf8 traffic_analysis/verify_day.py                    # 复核索引里最新的一天
    python -X utf8 traffic_analysis/verify_day.py 2026-10-15
    python -X utf8 traffic_analysis/verify_day.py 2026-10-15 --src "C:\Users\Administrator\Downloads"
    python -X utf8 traffic_analysis/verify_day.py --all              # 全部日期（索引一致性）

六段检查（编号沿用历史复核脚本）：
  A 源表「整体」行 ↔ 入库日档        —— 源表按日档里 source_files 记录的文件名去桌面/下载/--src 找
  B 全店 = 各直播间相加（9 个字段）
  C 日报 7 份齐全 + 漏斗首段 == 全店曝光 + 渠道数与日档一致
  D data/index.json 天数 / 末条 / 升序 / 该日视图
  E 页面静态契约（index.html 的 id 与交互钩子没被改坏）
  F 环比交叉校验：源表「较上周期」行（平台自己算的 %）↔ 我方前一日存档
退出码 0 = 全 OK；1 = 有 BAD。逐条打印，BAD 会写清「得到 vs 期望」。
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import daily_update as du                                   # noqa: E402  复用同一套解析器，避免两份口径

DATA = os.path.join(HERE, 'data')
REPD = os.path.join(HERE, 'reports')
PAGE = os.path.join(HERE, 'index.html')
HOME = os.path.expanduser('~')
SEARCH_DIRS = [os.path.join(HOME, 'Downloads'), os.path.join(HOME, 'Desktop')]

# 要跟日档逐一比对的字段（源表 A 段 / 全店加总 B 段）
FIELDS = ['impressions', 'views', 'interactions', 'new_followers', 'product_impressions',
          'product_clicks', 'paid_orders', 'paid_amount']
FLABEL = {'impressions': '曝光', 'views': '观看', 'interactions': '互动', 'new_followers': '涨粉',
          'product_impressions': '商品曝光', 'product_clicks': '商品点击', 'paid_orders': '订单',
          'paid_amount': '支付', 'live_duration': '直播时长'}
# 页面静态契约：这些 id / 钩子被改名会静默失效（docs/04-页面与模块.md 有说明）
HOOKS = ['tfStatus', 'tfHeadline', 'tfGridA', 'tfGridB', 'tfGridC', 'tfExtra', 'tfCompareBody',
         'tfPeerBody', 'tfChannelBody', 'tfRuleRows', 'tfReportPills', 'tfHeadlineList',
         'tfDataList', 'tfRuleList', 'tfActionList', 'chartFunnel', 'chartChannel', 'chartTrend',
         'chartRate', 'monthSelect', 'daySelect', 'scopeSelect',
         'toggleMetricHighlight', 'scrollToBlock', 'highlightChannelRow', 'tf-flash', 'tfTop',
         'dataZoom', "focus: 'series'"]

OK_N = 0
BAD = []


def ok(msg):
    global OK_N
    OK_N += 1
    print('  ✅ %s' % msg)


def bad(msg):
    BAD.append(msg)
    print('  ❌ %s' % msg)


def head(t):
    print('\n[%s]' % t)


def rj(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def find_source(basename, extra_dirs):
    """按文件名在 桌面 / 下载 / --src 里找源表（含一层子目录）。"""
    want = du.norm(basename)
    for d in extra_dirs + SEARCH_DIRS:
        if os.path.isfile(d):
            if du.norm(os.path.basename(d)) == want:
                return d
            continue
        if not os.path.isdir(d):
            continue
        for p in glob.glob(os.path.join(d, '*')):
            if os.path.isfile(p) and du.norm(os.path.basename(p)) == want:
                return p
        for sub in glob.glob(os.path.join(d, '*')):
            if os.path.isdir(sub):
                for p in glob.glob(os.path.join(sub, '*')):
                    if os.path.isfile(p) and du.norm(os.path.basename(p)) == want:
                        return p
    return None


def pct_of_cell(v):
    """源表「较上周期」单元格 → 百分数（'+1236.1%' / '-77.0%' / 空）。"""
    s = str(v or '').strip().replace('%', '').replace(',', '')
    if not s or s in ('—', '-', '--'):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main():
    argv = [a for a in sys.argv[1:]]
    src_dirs = []
    while '--src' in argv:
        i = argv.index('--src')
        src_dirs.append(os.path.abspath(argv[i + 1]))
        del argv[i:i + 2]
    all_days = '--all' in argv
    argv = [a for a in argv if not a.startswith('--')]

    print('=' * 68)
    print('  流量单日复核 · %s' % ROOT)
    print('=' * 68)

    # ---------------- D. 索引 ----------------
    head('D 索引 data/index.json')
    ip = os.path.join(DATA, 'index.json')
    if not os.path.exists(ip):
        bad('缺 %s' % os.path.relpath(ip, ROOT))
        return 1
    idx = rj(ip)
    days = [d['date'] for d in idx['days']]
    if not days:
        bad('索引里没有任何日期')
        return 1
    if days != sorted(days):
        bad('索引日期不是升序：%s' % days[:5])
    else:
        ok('%d 天，升序，%s ~ %s' % (len(days), days[0], days[-1]))
    target = days[-1] if (all_days or not argv) else argv[0]
    if target not in days:
        bad('索引里没有 %s（最近是 %s）' % (target, days[-1]))
        return 1
    meta = [d for d in idx['days'] if d['date'] == target][0]
    day = rj(os.path.join(DATA, target[:4], '%s.json' % target))
    rooms = day.get('rooms') or {}
    if meta['n_rooms'] != len(rooms):
        bad('%s 索引 n_rooms=%s，日档 %d 间' % (target, meta['n_rooms'], len(rooms)))
    elif meta['views'] != day['totals']['views']:
        bad('%s 索引 views=%s，日档 %s' % (target, meta['views'], day['totals']['views']))
    else:
        ok('%s 索引 ↔ 日档一致（%d 间，观看 %s）' % (target, len(rooms), format(int(day['totals']['views']), ',')))
    prev = days[days.index(target) - 1] if days.index(target) > 0 else None

    # ---------------- B. 全店加总 ----------------
    head('B 全店 = 各直播间相加')
    if len(rooms) <= 1:
        ok('单直播间天，跳过加总比对')
    else:
        diffs = []
        for f in FIELDS + ['live_duration']:
            s = sum((r['totals'].get(f) or 0) for r in rooms.values())
            v = day['totals'].get(f) or 0
            if abs(s - v) > 0.5:
                diffs.append('%s 加总 %s ≠ 全店 %s' % (FLABEL.get(f, f), round(s, 2), round(v, 2)))
        if diffs:
            bad('；'.join(diffs))
        else:
            ok('%d 间 × 9 字段相加精确等于全店（totals_source=%s）' % (len(rooms), day.get('totals_source')))

    # ---------------- C. 日报 ----------------
    head('C 日报 reports/%s/%s/' % (target[:4], target))
    rdir = os.path.join(REPD, target[:4], target)
    want = ['全店'] + list(rooms)
    miss = [s for s in want if not os.path.exists(os.path.join(rdir, '%s.json' % s))]
    if miss:
        bad('缺日报：%s' % '、'.join(miss))
    else:
        ok('%d 份日报齐全（全店 + %d 间）' % (len(want), len(rooms)))
    cb = []
    for s in want:
        p = os.path.join(rdir, '%s.json' % s)
        if not os.path.exists(p):
            continue
        r = rj(p)
        funnel = (r.get('metrics') or {}).get('funnel') or []
        exp_imp = day['totals']['impressions'] if s == '全店' else (rooms.get(s, {}).get('totals') or {}).get('impressions')
        if not funnel or abs((funnel[0].get('value') or 0) - (exp_imp or 0)) > 0.5:
            cb.append('%s 漏斗首段 %s ≠ 曝光 %s' % (s, (funnel[0].get('value') if funnel else None), exp_imp))
        n_day = len(rooms.get(s, {}).get('channels') or [])
        n_rep = len(r.get('channels') or [])
        if n_day and n_rep != n_day:
            cb.append('%s 渠道数 日报 %d ≠ 日档 %d' % (s, n_rep, n_day))
    if cb:
        bad('；'.join(cb[:6]))
    else:
        ok('每份日报漏斗首段 == 当日曝光，渠道数与日档一致')

    # ---------------- E. 页面静态契约 ----------------
    head('E 页面静态契约 traffic_analysis/index.html')
    html = io.open(PAGE, encoding='utf-8').read() if os.path.exists(PAGE) else ''
    gone = [h for h in HOOKS if h not in html]
    if gone:
        bad('缺 id / 交互钩子：%s' % '、'.join(gone))
    else:
        ok('%d 个 id 与交互钩子齐全（%d 字节）' % (len(HOOKS), len(html)))

    # ---------------- A. 源表 ↔ 日档 ----------------
    head('A 源表「整体」行 ↔ 日档（源表：桌面/下载/%s）' % ('、'.join(os.path.basename(d) for d in src_dirs) or '无 --src'))
    srcs = day.get('source_files') or {}
    found, missing = {}, []
    for room, base in srcs.items():
        p = find_source(base, src_dirs)
        (found.__setitem__(room, p) if p else missing.append(base))
    if missing:
        print('  ⚠️ 找不到源表（跳过 A/F，不算 BAD）：%s' % '、'.join(missing))
    a_bad = []
    for room, p in found.items():
        try:
            book = du.parse_xlsx(p)
            picked = du.pick_sheet(book)
            if not picked:
                a_bad.append('%s：源表里找不到表头（渠道列 + 指标列）' % room)
                continue
            sn, rows, hi, hidx, ch, how = picked
            a = du.analyze_room(rows, hi, hidx, ch, sn, os.path.basename(p))
        except Exception as e:                              # noqa: BLE001
            a_bad.append('%s：源表解析失败 %s' % (room, e))
            continue
        for f in FIELDS + ['live_duration']:
            got = a['totals'].get(f) or 0
            exp = (rooms.get(room, {}).get('totals') or {}).get(f) or 0
            if abs(got - exp) > 0.5:
                a_bad.append('%s %s：源表 %s ≠ 日档 %s' % (room, FLABEL.get(f, f), round(got, 2), round(exp, 2)))
    if a_bad:
        bad('；'.join(a_bad[:8]))
    elif found:
        ok('%d/%d 间源表「整体」行 9 字段与日档逐项相等' % (len(found), len(srcs)))
    else:
        print('  ⚠️ 本次没有可比对的源表')

    # ---------------- F. 环比交叉校验 ----------------
    if found and prev:
        head('F 环比交叉校验（源表「较上周期」↔ 我方 %s 存档）' % prev)
        try:
            prev_rooms = (rj(os.path.join(DATA, prev[:4], '%s.json' % prev)).get('rooms') or {})
        except Exception:                                   # noqa: BLE001
            prev_rooms = {}
        f_bad, f_n = [], 0
        for room, p in found.items():
            old = prev_rooms.get(room)
            if not old:
                continue
            try:
                sn, rows, hi, hidx, ch, how = du.pick_sheet(du.parse_xlsx(p))
            except Exception:                               # noqa: BLE001
                continue
            dod_row = None
            for i in sorted(rows.keys()):
                if i <= hi or len(rows[i]) <= ch:
                    continue
                if '较上周期' in str(rows[i][ch] or ''):
                    dod_row = rows[i]
                    break
            if dod_row is None:
                continue
            for f in FIELDS:
                j = hidx.get(f)
                if j is None or len(dod_row) <= j:
                    continue
                claimed = pct_of_cell(dod_row[j])
                base = (old.get('totals') or {}).get(f) or 0
                if claimed is None or not base:
                    continue
                mine = ((rooms[room]['totals'].get(f) or 0) / base - 1) * 100
                f_n += 1
                if abs(claimed - mine) > 0.2:
                    f_bad.append('%s %s：平台 %+.1f%% vs 我方存档算得 %+.1f%%' % (room, FLABEL.get(f, f), claimed, mine))
        if f_bad:
            bad('；'.join(f_bad[:8]))
        elif f_n:
            ok('%d 个字段的环比%%：平台自算 ↔ 我方前一日存档 全吻合（文件确为 %s 单日数据）' % (f_n, target))
        else:
            print('  ⚠️ 源表里没有「较上周期」行，跳过')

    # ---------------- 人眼摘要 ----------------
    hd = day['totals']
    line = '%s 全店：曝光 %s / 观看 %s / 订单 %s / 支付 %s' % (
        target, format(int(hd['impressions']), ','), format(int(hd['views']), ','),
        format(int(hd['paid_orders']), ','), format(int(hd.get('paid_amount') or 0), ','))
    if prev and prev_rooms is not None:
        try:
            pv = rj(os.path.join(DATA, prev[:4], '%s.json' % prev))['totals']
            if pv.get('views'):
                line += '（观看环比 %+.1f%%）' % ((hd['views'] / pv['views'] - 1) * 100)
        except Exception:                                   # noqa: BLE001
            pass
    print('\n' + line)

    print('\n' + '=' * 68)
    if BAD:
        print('  ❌ BAD %d 条 / OK %d 条' % (len(BAD), OK_N))
        for b in BAD:
            print('     - %s' % b)
        return 1
    print('  ✅ 全部通过（OK %d 条，无 BAD）' % OK_N)
    return 0


if __name__ == '__main__':
    sys.exit(main())
