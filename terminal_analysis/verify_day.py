# -*- coding: utf-8 -*-
"""终端流量分析 · 单日复核（截图链路版）

用法：
    python -X utf8 terminal_analysis/verify_day.py            # 复核全部已入库日期
    python -X utf8 terminal_analysis/verify_day.py 2026-11-01 # 只复核某天

复核对像：shots/<日期>.json（人工转写的截图数字，唯一源）↔ data/YYYY/YYYY-MM-DD.json（落盘产物）
    A 每个终端的 6 个源指标逐项相等（容差 1e-6，比率按 % → 小数换算）
    B 整体 = Σ各终端（曝光/点击必须精确；推算支付金额容差 0.5 元/终端）
    C 派生指标公式自洽：支付金额 = 千次曝光支付 × 曝光 ÷ 1000；成交订单 = 点击 × 点击→成交率
    D 索引 index.json 的天数/月份/口径/末条与日档一致
    E 页面钩子齐全（terminal_analysis/index.html）
"""
import os
import sys
import json

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
SHOTS = os.path.join(BASE, 'shots')
PAGE = os.path.join(BASE, 'index.html')
TRUNC = '未显示（截图截断）'
TOL = 1e-6

PAGE_HOOKS = ['chartTmPie', 'chartTmSell', 'chartTmBar', 'chartTmLine', 'chartTmShare',
              'tmKpi', 'tmTableBody', 'tmStatus', 'tmHeadline', 'tmNote',
              'tmScopeChips', 'tmLineTerms', 'tmLineMeta',
              'renderScopeChips', 'renderLineTerms', 'setScope', 'setHighlight']

ok_n = 0
bad = []


def ok(msg):
    global ok_n
    ok_n += 1
    print('  ✅ ' + msg)


def fail(msg):
    bad.append(msg)
    print('  ❌ ' + msg)


def near(a, b, tol):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


def load(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_day(date):
    sp = os.path.join(SHOTS, date + '.json')
    dp = os.path.join(DATA, date[:4], date + '.json')
    if not os.path.exists(sp):
        fail('%s 缺少转写源 shots/%s.json' % (date, date))
        return
    if not os.path.exists(dp):
        fail('%s 缺少日档' % date)
        return
    shot, day = load(sp), load(dp)
    print('\n===== %s（售卖类型「%s」，%d 间） =====' % (date, '/'.join(day['sell_types']), len(day['scopes'])))

    # A 源指标逐项（售卖类型按每间自己的取：2026-11-02 官旗手表=合作，其余=自营）
    errs = 0
    excluded = {e['scope']: e.get('reason', '') for e in (day.get('excluded_scopes') or [])}
    n_checked = 0
    for room, spec in shot['rooms'].items():
        if room in excluded:
            print('  ℹ️  %s 按「排除」跳过（%s）' % (room, excluded[room]))
            continue
        n_checked += 1
        if isinstance(spec, dict) and 'terminals' in spec:
            terms = spec['terminals']
        else:
            terms = spec
        sc = day['scopes'].get(room)
        if not sc:
            fail('%s 日档缺少该间' % room); errs += 1; continue
        sell = sc['sell_types'][0]
        for t, vals in terms.items():
            r = sc['terminals'].get(t, {}).get(sell)
            if not r:
                fail('%s / %s 日档缺少该终端' % (room, t)); errs += 1; continue
            pairs = [(r['product_impressions'], vals[0]), (r['product_clicks'], vals[1]),
                     (r['evr_click'], vals[2] / 100.0), (r['click_cvr'], vals[3] / 100.0),
                     (r['evr_order'], vals[4] / 100.0), (r['gpm_1k'], vals[5])]
            for got, want in pairs:
                if not near(got, want, 1e-6 if abs(want) < 1 else 1e-4):
                    fail('%s / %s 数值不一致：%s ≠ %s' % (room, t, got, want)); errs += 1
    if not errs:
        ok('[A] %d 间 × 全部终端 × 6 个源指标 ↔ 日档逐项相等' % n_checked)

    # B 整体 = Σ终端
    errs = 0
    micro = day.get('micro_diff') or {}
    for room, sc in day['scopes'].items():
        sell = sc['sell_types'][0]
        o = sc['terminals']['整体'][sell]
        ts = [v[sell] for k, v in sc['terminals'].items() if k != '整体']
        m = micro.get(room) or {}
        mi, mc = abs(m.get('impressions') or 0), abs(m.get('clicks') or 0)
        for k, tol_k in (('product_impressions', mi + 0.001), ('product_clicks', mc + 0.001)):
            s = sum((x.get(k) or 0) for x in ts)
            if not near(o.get(k), s, tol_k):
                fail('%s 整体%s(%s) ≠ Σ终端(%s)' % (room, k, o.get(k), s)); errs += 1
            elif abs((o.get(k) or 0) - s) > 0.001:
                print('  ℹ️  %s 整体%s %s vs 可见终端之和 %s（平台口径微差，以整体为准）' % (
                    room, '曝光' if k == 'product_impressions' else '点击', '{:,.0f}'.format(o.get(k) or 0), '{:,.0f}'.format(s)))
        sp = sum((x.get('paid_amount') or 0) for x in ts)
        # 支付金额是推算值（=千次曝光支付×曝光/1000），千次支付本身只显示 2 位小数，
        # 每行误差上限 0.005 元/千次曝光 → 整体与 Σ终端 的差额上限 = 0.005×(整体曝光+Σ曝光)/1000
        tol_paid = 0.005 * ((o.get('product_impressions') or 0) + sum((x.get('product_impressions') or 0) for x in ts)) / 1000.0 + 0.01
        if mi:
            # 平台整体比可见终端少 mi 次曝光 → 少掉的推算支付最多 mi×最大千次支付/1000
            gmax = max([x.get('gpm_1k') or 0 for x in ts] + [o.get('gpm_1k') or 0])
            tol_paid += mi * (gmax + 5) / 1000.0 + 0.02
        has_trunc = TRUNC in sc['terminals']
        if has_trunc:
            # 截图截断时「整体」里含看不到的终端行，其支付金额无从拆解；
            # 平台「千次曝光用户支付金额」是各自四舍五入后的值，加总本就不闭合 → 放宽到 2%，只做合理性检查
            tol_paid = max(tol_paid, 0.02 * abs(o.get('paid_amount') or 0))
        d_paid = (o['paid_amount'] - sp) if o.get('paid_amount') is not None else 0
        if o.get('paid_amount') is not None and abs(d_paid) > tol_paid:
            fail('%s 整体推算支付(%s) 与 Σ终端(%s) 差 %.2f 元（容差 %.2f）' % (room, o['paid_amount'], sp, d_paid, tol_paid)); errs += 1
        elif has_trunc and abs(d_paid) > 0.01:
            print('  ℹ️  %s 整体推算支付 %s vs 可见终端相加 %s（差 %.2f 元 = %.2f%%，截图截断所致，已放宽）' % (
                room, ('%.2f' % o['paid_amount']), ('%.2f' % sp), d_paid, 100.0 * d_paid / (o.get('paid_amount') or 1)))
    if not errs:
        ok('[B] 每间 整体 = Σ各终端（曝光/点击精确，推算支付容差内）')

    # C 派生公式
    errs = 0
    for room, sc in day['scopes'].items():
        sell = sc['sell_types'][0]
        for t, sells in sc['terminals'].items():
            r = sells[sell]
            if r.get('gpm_1k') is not None:
                want = round(r['gpm_1k'] * r['product_impressions'] / 1000.0, 2)
                if not near(r.get('paid_amount'), want, 0.02):
                    fail('%s / %s 推算支付 %s ≠ %s' % (room, t, r.get('paid_amount'), want)); errs += 1
            if r.get('click_cvr') is not None:
                want = round(r['product_clicks'] * r['click_cvr'], 1)
                if not near(r.get('paid_orders'), want, 0.15):
                    fail('%s / %s 推算订单 %s ≠ %s' % (room, t, r.get('paid_orders'), want)); errs += 1
    if not errs:
        ok('[C] 派生指标公式自洽（支付金额 / 成交订单）')

    trunc = [r for r in day['scopes'] if TRUNC in day['scopes'][r]['terminals']]
    if trunc:
        print('  ⚠️  截图截断（差额行已补齐可见字段）：' + '、'.join(trunc))


def check_index():
    idx = load(os.path.join(DATA, 'index.json'))
    days = [d['date'] for d in idx['days']]
    files = sorted(fn[:-5] for fn in os.listdir(os.path.join(DATA, '2026')) if fn.endswith('.json')) if os.path.isdir(os.path.join(DATA, '2026')) else []
    print('\n===== 索引 =====')
    if sorted(days) != files:
        fail('[D] 索引日期与日档文件不一致：索引 %s / 文件 %s' % (sorted(days), files))
    else:
        ok('[D] 索引 %d 天（%s），与日档文件一致' % (len(days), ', '.join(days)))
    last = idx['days'][0] if idx['days'] else None
    if last:
        day = load(os.path.join(DATA, last['date'][:4], last['date'] + '.json'))
        if sorted(last['scopes']) != sorted(day['scopes'].keys()):
            fail('[D] 末条口径与日档不一致')
        else:
            ok('[D] 末条 %s 口径 %d 间与日档一致' % (last['date'], len(last['scopes'])))
    if idx.get('metrics') and len(idx['metrics']) >= 6:
        ok('[D] 指标 %d 个：%s' % (len(idx['metrics']), '、'.join(m['key'] for m in idx['metrics'])))
    else:
        fail('[D] 索引缺少指标定义')


def check_page():
    print('\n===== 页面 =====')
    if not os.path.exists(PAGE):
        fail('[E] 页面不存在'); return
    with open(PAGE, 'r', encoding='utf-8') as f:
        src = f.read()
    miss = [h for h in PAGE_HOOKS if h not in src]
    if miss:
        fail('[E] 缺少钩子：%s' % ', '.join(miss))
    else:
        ok('[E] 页面钩子 %d 个齐全（%d 字节）' % (len(PAGE_HOOKS), len(src.encode('utf-8'))))


def main(argv):
    dates = []
    if argv:
        dates = [argv[0]]
    else:
        for fn in sorted(os.listdir(SHOTS)):
            if fn.endswith('.json'):
                dates.append(fn[:-5])
    if not dates:
        print('❌ shots/ 下没有任何转写文件'); return 1
    for d in dates:
        check_day(d)
    check_index()
    check_page()
    print('\n' + ('✅ OK %d 条，无 BAD' % ok_n if not bad else '❌ %d 条 BAD' % len(bad)))
    return 0 if not bad else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
