# -*- coding: utf-8 -*-
"""流量分析 · 示例数据生成器（真实数据到位前的占位）。

生成 2026-10-01 ~ 2026-10-11 的「抖音直播流量渠道明细」，渠道口径与真实导出
（直播间曝光次数 / 直播间观看次数 / 直播间互动次数 / 新增粉丝数 /
  商品曝光次数 / 商品点击次数 / 成交订单数 / 用户支付金额）完全一致。

    python traffic_analysis/seed_demo.py            # 灌入示例数据
    python traffic_analysis/seed_demo.py --days 3   # 只灌 10-01~10-03
    python traffic_analysis/seed_demo.py --clear    # 清空示例数据

⚠️ 示例数据仅用于把页面跑起来看效果。用户上传真实流量表后，
   同一天会被 daily_update.py 直接覆盖（upsert），不会残留。
"""
import argparse
import json
import os
import random
import sys
from datetime import date, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import daily_update as du  # noqa: E402

ROOM = '全店（全渠道汇总）'
START = date(2026, 10, 1)

# 渠道基准占比（按观看次数），覆盖抖音直播常见的 7 个流量入口
CHANNELS = [
    ('直播推荐',              0.330),
    ('粉丝关注',              0.180),
    ('直播广场',              0.140),
    ('个人主页&店铺&橱窗',    0.120),   # 口径异常渠道：互动 > 观看
    ('活动页',                0.085),   # 口径异常渠道
    ('同城',                  0.075),
    ('搜索',                  0.070),
]
ANOM = {'个人主页&店铺&橱窗', '活动页'}

# 每日大盘基准观看人数（国庆假期高，节后回落再爬升）
DAILY_VIEWS = {
    '10-01': 1_240_000, '10-02': 1_305_000, '10-03': 1_258_000, '10-04': 1_182_000,
    '10-05': 1_096_000, '10-06': 1_020_000, '10-07': 1_112_000, '10-08': 986_000,
    '10-09': 1_064_000, '10-10': 1_158_000, '10-11': 872_000,   # 11 号是当天未跑满
}


def gen_day(d: date) -> dict:
    """造一天的渠道明细（确定性伪随机，同一天结果稳定）。"""
    key = d.isoformat()[5:]
    base_views = DAILY_VIEWS.get(key, 1_050_000)
    rnd = random.Random(20261000 + d.day)

    channels = {}
    for name, share in CHANNELS:
        w = share * rnd.uniform(0.86, 1.16)
        v = base_views * w
        # 异常渠道：互动次数比观看次数还大（口径不一致），保留特征
        ir_ratio = rnd.uniform(1.05, 1.35) if name in ANOM else rnd.uniform(0.048, 0.078)
        evr = rnd.uniform(0.100, 0.128)
        ctr = rnd.uniform(0.062, 0.088)
        cvr = rnd.uniform(0.046, 0.064)
        # GPM 定在 150~200 元区间：太大会把「客单价」推到 200 元+/单，
        # 与单品 100~160 元的实际售价不符（客单价 = 支付金额/成交订单数）。
        gpm = rnd.uniform(150, 200)
        rec = {
            'impressions':         v / evr,
            'views':               v,
            'interactions':        v * ir_ratio,
            'new_followers':       v * rnd.uniform(0.0075, 0.0125),
            'product_impressions': 250_000 / 7.0 * rnd.uniform(0.85, 1.18),
            'product_clicks':      (250_000 / 7.0 * rnd.uniform(0.85, 1.18)) * ctr,
            'paid_orders':         (250_000 / 7.0 * rnd.uniform(0.85, 1.18)) * ctr * cvr,
            'paid_amount':         v * gpm / 1000.0,
        }
        channels[name] = {k: round(x, 4) for k, x in rec.items()}
    return channels


def build_payload(d: date) -> dict:
    channels = gen_day(d)
    tot = {f: 0.0 for f, _l, _u, _k in du.COLS}
    for rec in channels.values():
        for k, v in rec.items():
            tot[k] += v
    ok = {k: v for k, v in channels.items() if k not in du.ANOMALY_CHANNELS}
    ok_tot = {f: sum(c.get(f, 0.0) for c in ok.values()) for f, _l, _u, _k in du.COLS}
    payload = {
        'date': d.isoformat(), 'room': ROOM, 'demo': True,
        'source_file': '（示例数据 · seed_demo.py）', 'source_sheet': '示例',
        'matched_fields': [f for f, _l, _u, _k in du.COLS],
        'channels': channels,
        'totals': {k: round(v, 4) for k, v in tot.items()},
        'ok_totals': {k: round(v, 4) for k, v in ok_tot.items()},
        'updated_at': du.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    payload['metrics'] = {k: (round(v, 6) if isinstance(v, float) else v)
                          for k, v in du.compute_metrics(tot, ok_tot).items()}
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=11, help='生成天数（从 10-01 起，默认 11 天）')
    ap.add_argument('--clear', action='store_true', help='清空示例数据')
    a = ap.parse_args()

    if a.clear:
        n = 0
        for dd in du.all_dates():
            p = du.day_path(dd)
            rec = json.load(open(p, encoding='utf-8'))
            if rec.get('demo'):
                os.remove(p)
                rp = os.path.join(du.REPORT_DIR, dd + '.json')
                if os.path.exists(rp):
                    os.remove(rp)
                n += 1
        du.rebuild_reports()
        print(f'✔ 已清空 {n} 天示例数据')
        return 0

    for i in range(a.days):
        d = START + timedelta(days=i)
        payload = build_payload(d)
        du.write_day(d.isoformat(), payload)
    dates, ip, idx = du.rebuild_reports()
    print(f'✔ 示例数据已灌入：{len(dates)} 天（{dates[0]} ~ {dates[-1]}）')
    for mm in idx['months']:
        print(f"   {mm['ym']}  {mm['count']} 天")
    print(f"   索引 {os.path.relpath(ip, os.path.dirname(du.ROOT))}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
