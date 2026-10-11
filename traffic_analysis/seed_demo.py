# -*- coding: utf-8 -*-
"""流量分析 · 示例数据生成器（真实数据到位前的占位）。

生成 2026-10-01 ~ 2026-10-07 的「抖音直播流量渠道明细」，**结构与真实导出完全一致**：
每份表 12 个渠道 + 「整体」行，8 个计数指标 + 直播时长 / 人均观看时长 / 千川消耗。

    python traffic_analysis/seed_demo.py            # 灌入示例数据（默认 7 天）
    python traffic_analysis/seed_demo.py --days 3   # 只灌 10-01~10-03
    python traffic_analysis/seed_demo.py --clear    # 清空示例数据

⚠️ 示例数据只用于把页面跑起来看效果。真实流量表入库时同一天会被 daily_update.py
   直接覆盖（upsert），不会残留；示例数据在页面上会显示金色「示例数据」提示条。
   默认只灌到 10-07，就是为了不跟 10.10 的真实数据撞车。
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

START = date(2026, 10, 1)

# 渠道基准占比（按观看次数），渠道名与真实导出逐字一致
CHANNELS = [
    ('推荐feed',                0.300),
    ('直播广场',                0.100),
    ('同城',                    0.020),
    ('直播推荐-其他推荐场景',   0.030),
    ('短视频引流',              0.140),
    ('关注',                    0.090),
    ('搜索',                    0.110),
    ('个人主页&店铺&橱窗',      0.085),
    ('抖音商城推荐',            0.060),
    ('活动页',                  0.025),
    ('头条西瓜',                0.020),
    ('其他',                    0.020),
]
# 每天总会有 1~2 个渠道的「互动次数」比「观看次数」还大（平台两列口径不一致），保留这个特征
SUSPECT_CHANNELS = ['直播广场', '关注', '搜索', '活动页']

# 5 个示例直播间（真实名单是 6 个，示例少一个也无所谓）：
#   base_views 日均观看、gpm 千次观看成交额、evr 曝光→观看率、ctr 商品点击率、cvr 点击→成交率
ROOMS = [
    {'name': '小米官方手环直播间', 'base_views': 38000, 'aov': 325, 'evr': 0.045, 'ctr': 0.120, 'cvr': 0.022, 'fans': 0.0057, 'roi': 40.0},
    {'name': '小米官方手表',       'base_views': 52000, 'aov': 566, 'evr': 0.065, 'ctr': 0.074, 'cvr': 0.010, 'fans': 0.0040, 'roi': 36.0},
    {'name': '小米官方耳机直播间', 'base_views': 3000,  'aov': 247, 'evr': 0.050, 'ctr': 0.067, 'cvr': 0.021, 'fans': 0.0030, 'roi': 14.0},
    {'name': '小米官旗手表直播间', 'base_views': 6800,  'aov': 694, 'evr': 0.058, 'ctr': 0.054, 'cvr': 0.011, 'fans': 0.0043, 'roi': 21.0},
    {'name': '小米数码旗舰店',     'base_views': 48000, 'aov': 322, 'evr': 0.052, 'ctr': 0.105, 'cvr': 0.024, 'fans': 0.0049, 'roi': 46.0},
]
# GPM 由「客单价 × 点击→成交率」反推（客单价 × 成交订单数 = 支付金额，两者必须自洽，
# 否则示例数据的「客单价」会离谱 —— 之前直接拍 GPM 就把官旗手表推到 823 元/单）。

# 每日大盘系数（国庆高，节后回落）
DAY_FACTOR = {'10-01': 1.14, '10-02': 1.18, '10-03': 1.12, '10-04': 1.04,
              '10-05': 0.97, '10-06': 0.92, '10-07': 1.00}


def gen_room_day(prof, d: date) -> dict:
    """造一个直播间一天的渠道明细（确定性伪随机，同一天同一直播间结果稳定）。"""
    rnd = random.Random(hash((prof['name'], d.isoformat())) & 0x7FFFFFFF)
    factor = DAY_FACTOR.get(d.isoformat()[5:], 1.0) * rnd.uniform(0.94, 1.06)
    base_views = prof['base_views'] * factor

    channels = {}
    for name, share in CHANNELS:
        v = max(0.0, base_views * share * rnd.uniform(0.82, 1.20))
        if v < 8:                      # 小渠道偶尔真的没人进来，保留这种稀疏特征
            v = float(rnd.choice([0, 0, 1, 2, 4, 7]))
        evr = prof['evr'] * rnd.uniform(0.88, 1.14)
        impressions = (v / evr) if evr else 0.0
        # 互动次数：正常渠道是观看的 8%~26%；「口径异常」渠道偶尔冲到 1.0~2.6 倍
        if name in SUSPECT_CHANNELS and rnd.random() < 0.12 and v >= 600:
            ir = rnd.uniform(1.0, 2.6)
        elif name in SUSPECT_CHANNELS:
            ir = rnd.uniform(0.08, 0.24)
        else:
            ir = rnd.uniform(0.08, 0.24)
        pimp = v * rnd.uniform(5.4, 7.8)
        ctr = prof['ctr'] * rnd.uniform(0.86, 1.16)
        pclk = pimp * ctr
        cvr = prof['cvr'] * rnd.uniform(0.82, 1.22)
        orders = pclk * cvr
        # 支付金额 = 成交订单数 × 该渠道客单价（客单价按渠道上下浮动 ±8%，这样
        # 「客单价 = 支付金额 ÷ 成交订单数」这个恒等式在渠道层也成立，全店客单价才贴近真实）
        channels[name] = {
            'impressions':         round(impressions, 4),
            'views':               round(v, 4),
            'interactions':        round(v * ir, 4),
            'new_followers':       round(v * prof['fans'] * rnd.uniform(0.80, 1.20), 4),
            'product_impressions': round(pimp, 4),
            'product_clicks':      round(pclk, 4),
            'paid_orders':         round(orders, 4),
            'paid_amount':         round(orders * prof['aov'] * rnd.uniform(0.92, 1.08), 4),
        }
    return channels


def build_room(prof, d: date) -> dict:
    """把渠道明细组装成 analyze_room 的同款结构（totals / ok_totals / metrics / extras）。"""
    channels = gen_room_day(prof, d)
    fields = [f for f, _l, _u, _k in du.COLS]
    totals = {f: round(sum(c.get(f, 0.0) for c in channels.values()), 4) for f in fields}
    order = [n for n, _s in CHANNELS]
    recs = [dict(channels[n], name=n) for n in order]
    anomalies, suspects = [], []
    for c in recs:
        v, it = c.get('views') or 0, c.get('interactions') or 0
        ratio = (it / v) if v else None
        c['interaction_ratio'] = round(ratio, 4) if ratio is not None else None
        c['anomaly'] = bool(v >= du.ANOM_MIN_VIEWS and ratio is not None and ratio >= du.ANOM_RATIO)
        c['suspect'] = bool(not c['anomaly'] and v >= du.ANOM_MIN_VIEWS and ratio is not None and ratio >= du.ANOM_WARN_RATIO)
        if c['anomaly']:
            anomalies.append(c['name'])
        elif c['suspect']:
            suspects.append(c['name'])
    ok_totals = {f: round(sum(c.get(f, 0.0) for c in recs if not c['anomaly']), 4) for f in fields}
    excluded = round((totals.get('interactions') or 0) - (ok_totals.get('interactions') or 0), 4)

    rnd = random.Random((hash((prof['name'], d.isoformat(), 'x')) & 0x7FFFFFFF))
    minutes = {'小米官方手环直播间': 1440.0, '小米数码旗舰店': 1440.0}.get(prof['name'], round(rnd.uniform(560, 1020), 2))
    qianchuan = round((totals['paid_amount'] / prof['roi']) * rnd.uniform(0.9, 1.1), 2)
    totals['live_duration'] = minutes
    totals['qianchuan'] = qianchuan
    totals['avg_watch_time'] = '%d秒' % int(rnd.uniform(38, 62))

    metrics = du.compute_metrics(totals, ok_totals)
    metrics['qianchuan_roi'] = du.div(totals['paid_amount'], qianchuan)
    metrics['orders_per_hour'] = du.div(totals['paid_orders'], minutes / 60.0)
    metrics['gmv_per_hour'] = du.div(totals['paid_amount'], minutes / 60.0)
    return {
        'sheet': '流量趋势', 'source_file': '（示例数据 · seed_demo.py）',
        'channels': {c['name']: {k: v for k, v in c.items() if k != 'name'} for c in recs},
        'channel_order': order,
        'totals': {k: (round(v, 6) if isinstance(v, float) else v) for k, v in totals.items()},
        'ok_totals': ok_totals,
        'metrics': {k: (round(v, 6) if isinstance(v, float) else v) for k, v in metrics.items()},
        'totals_source': '渠道加总（示例）',
        'row_sum_mismatch': {},
        'anomaly_channels': anomalies,
        'suspect_channels': suspects,
        'excluded_interactions': excluded,
        'excluded_share': round(du.div(excluded, totals.get('interactions')) or 0.0, 4),
        'skipped_rows': [],
        'extras': {'qianchuan': qianchuan, 'live_duration': minutes, 'avg_watch_time': totals['avg_watch_time']},
        'demo': True,
        'updated_at': du.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def build_payload(d: date) -> dict:
    rooms = {p['name']: build_room(p, d) for p in ROOMS}
    payload = {
        'date': d.isoformat(), 'demo': True,
        'source_files': {p['name']: '（示例数据 · seed_demo.py）' for p in ROOMS},
        'rooms': rooms,
        'created_at': du.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    payload.update(du.sum_rooms(rooms))
    payload['demo'] = True
    payload['updated_at'] = du.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return payload


def clear():
    n = 0
    for dd in du.all_dates():
        p = du.day_path(dd)
        try:
            rec = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        if du.day_is_demo(rec):
            os.remove(p)
            n += 1
    du.rebuild_reports(quiet=True)
    print('✔ 已清空 %d 天示例数据' % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7, help='生成天数（从 10-01 起，默认 7 天，避免撞真实数据）')
    ap.add_argument('--clear', action='store_true', help='清空示例数据（只删 demo 日文件）')
    a = ap.parse_args()

    if a.clear:
        clear()
        return 0

    for i in range(a.days):
        dd = START + timedelta(days=i)
        du.write_day(dd.isoformat(), build_payload(dd))
    dates, _ip, idx = du.rebuild_reports(quiet=True)
    print('✔ 示例数据已灌入：%d 天（%s ~ %s），每天 %d 个直播间' % (
        len(dates), dates[0], dates[-1], len(ROOMS)))
    for mm in idx['months']:
        print('   %s  %d 天：%s' % (mm['ym'], mm['count'], '、'.join(mm['dates'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
