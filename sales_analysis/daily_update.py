"""
Multi-room Xiaomi Band Live Stream Sales Analysis
Usage: python daily_update.py <path_to_excel>

Supports both 3-column (no room info) and 4-column (with room name) Excel files.
When room info is present, generates per-room comparison reports and charts.
"""
import pandas as pd
import json
import os
import sys
from datetime import datetime

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')

# Our rooms — everything else is competitor
OUR_ROOMS = {
    '小米数码旗舰店', '小米官方手表', '小米官方手环直播间',
    '小米官方耳机直播间', '小米手环10Pro直播间',
}


def shorten_product(name):
    name = str(name)
    if '10Pro' in name or '10 Pro' in name:
        return '小米手环10 Pro'
    elif '10系' in name or ('10 ' in name and 'Pro' not in name and '9' not in name):
        return '小米手环10'
    elif '10 标准' in name:
        return '小米手环10 标准'
    elif '10 陶瓷' in name or '10陶瓷' in name or '陶瓷白' in name:
        return '小米手环10 陶瓷版'
    elif '9 Pro' in name:
        return '小米手环9 Pro'
    elif 'REDMI Watch 6' in name:
        return 'REDMI Watch 6'
    elif 'REDMI 手' in name:
        return 'REDMI 手环 3'
    elif 'Type-C' in name or '充电' in name:
        return '充电配件'
    elif 'Xiaomi Buds 6' in name:
        return 'Xiaomi Buds 6'
    elif 'Xiaomi Buds 5' in name:
        return 'Xiaomi Buds 5 Pro'
    elif '骨传导耳机' in name:
        return '小米骨传导耳机2'
    elif '开放式耳机' in name or '耳夹式耳机' in name:
        return 'Xiaomi 开放式耳机'
    elif 'Buds 8 Pro' in name:
        return 'REDMI Buds 8 Pro'
    elif 'Buds 8 青春' in name:
        return 'REDMI Buds 8 青春版'
    elif 'Buds 8 活力' in name:
        return 'REDMI Buds 8 活力版'
    elif 'Buds 8' in name:
        return 'REDMI Buds 8'
    elif 'Buds 7S' in name:
        return 'REDMI Buds 7S'
    elif 'Buds 6 活力' in name:
        return 'REDMI Buds 6 活力版'
    elif 'Buds 6' in name:
        return 'REDMI Buds 6'
    elif '颈挂式耳机' in name:
        return 'Xiaomi 颈挂式耳机2'
    elif '头戴' in name:
        return '头戴式耳机'
    elif '耳机' in name or 'Buds' in name:
        return '耳机配件'
    elif 'AI眼镜' in name or 'AI 眼镜' in name:
        return '小米AI眼镜'
    elif '手环8' in name or 'Band 8' in name:
        return '小米手环8'
    elif '插线板' in name or '插座' in name:
        return '插线板/配件'
    else:
        return name[:25]


def load_and_clean(filepath):
    df = pd.read_excel(filepath)
    # Detect column roles by name patterns
    col_map = {}
    for i, col in enumerate(df.columns):
        name = str(col)
        if any(kw in name for kw in ['商品', '产品', 'product']):
            col_map['product'] = i
        elif any(kw in name for kw in ['金额', '价格', 'price', '应付']):
            col_map['price'] = i
        elif any(kw in name for kw in ['时间', '提交', 'time', 'date']):
            col_map['time'] = i
        elif any(kw in name for kw in ['直播', '房间', 'room', '达人']):
            col_map['room'] = i
        elif any(kw in name for kw in ['类型', '我方', '竞对', 'type']):
            col_map['type'] = i

    cols = []
    for key in ['product', 'price', 'time', 'room', 'type']:
        if key in col_map:
            cols.append(df.columns[col_map[key]])
        else:
            cols.append(None)

    df = df.iloc[:, :len(df.columns)]  # keep all
    new_names = {}
    for i, (key, col) in enumerate(zip(['product', 'price', 'time', 'room', 'type'], cols)):
        if col is not None:
            new_names[col] = key
    df = df.rename(columns=new_names)

    if 'time' not in df.columns:
        df['time'] = pd.NaT
    if 'room' not in df.columns:
        df['room'] = '未知直播间'
    if 'type' not in df.columns:
        df['type'] = '竞对'

    # Keep only our standard columns
    df = df[['product', 'price', 'time', 'room', 'type']]

    df['product'] = df['product'].astype(str).str.replace('\t', '', regex=False)
    df['time'] = df['time'].astype(str).str.replace('\t', '', regex=False)
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['time'] = pd.to_datetime(df['time'])
    df['date'] = df['time'].dt.date
    df['hour'] = df['time'].dt.hour
    df['product_short'] = df['product'].apply(shorten_product)
    df['room'] = df['room'].astype(str).str.strip()
    # Always classify by room name
    df['type'] = df['room'].apply(lambda r: '我方' if r in OUR_ROOMS else '竞对')
    return df


def summarize_room(grp):
    hourly_stats = {}
    for hour, hgrp in grp.groupby('hour'):
        products = {}
        for pname, pgrp in hgrp.groupby('product_short'):
            products[pname] = {
                'orders': int(len(pgrp)),
                'revenue': float(round(pgrp['price'].sum(), 2)),
                'room_pct': round(len(pgrp) / len(hgrp) * 100, 1)
            }
        hourly_stats[str(hour)] = {
            'orders': int(len(hgrp)),
            'revenue': float(round(hgrp['price'].sum(), 2)),
            'products': products
        }

    return {
        'orders': int(len(grp)),
        'revenue': float(round(grp['price'].sum(), 2)),
        'avg_price': float(round(grp['price'].mean(), 2)),
        'products': {
            name: {
                'orders': int(len(pgrp)),
                'revenue': float(round(pgrp['price'].sum(), 2)),
                'avg_price': float(round(pgrp['price'].mean(), 2))
            }
            for name, pgrp in grp.groupby('product_short')
        },
        '_hourly_stats': hourly_stats
    }


def summarize_day(df):
    rooms = {}
    for room_name, room_df in df.groupby('room'):
        rsum = summarize_room(room_df)
        types = room_df['type'].value_counts()
        rsum['type'] = '我方' if '我方' in types.index else types.index[0]
        rooms[room_name] = rsum

    # Identify our rooms
    our_rooms = [r for r, info in rooms.items() if info['type'] == '我方']
    comp_rooms = [r for r, info in rooms.items() if info['type'] == '竞对']

    # Type-level aggregates
    type_summary = {}
    for t in ['我方', '竞对']:
        tdf = df[df['type'] == t]
        if len(tdf) > 0:
            type_summary[t] = {
                'orders': int(len(tdf)),
                'revenue': float(round(tdf['price'].sum(), 2)),
                'avg_price': float(round(tdf['price'].mean(), 2)),
                'rooms': tdf['room'].nunique()
            }

    all_products = {}
    for name, grp in df.groupby('product_short'):
        all_products[name] = {
            'orders': int(len(grp)),
            'revenue': float(round(grp['price'].sum(), 2)),
            'avg_price': float(round(grp['price'].mean(), 2))
        }

    hourly_stats = {}
    for hour, grp in df.groupby('hour'):
        products = {}
        for pname, pgrp in grp.groupby('product_short'):
            products[pname] = {
                'orders': int(len(pgrp)),
                'revenue': float(round(pgrp['price'].sum(), 2)),
                'room_pct': round(len(pgrp) / len(grp) * 100, 1)
            }
        hourly_stats[str(hour)] = {
            'orders': int(len(grp)),
            'revenue': float(round(grp['price'].sum(), 2)),
            'products': products
        }

    # Compute cross-room market share for each room-hour-product
    # Build (product, hour) -> total orders across all rooms
    product_hour_totals = {}
    for room_name, room_info in rooms.items():
        for hour_str, hdata in room_info['_hourly_stats'].items():
            for pname, pinfo in hdata['products'].items():
                key = (pname, hour_str)
                product_hour_totals[key] = product_hour_totals.get(key, 0) + pinfo['orders']
    # Apply market_pct to each room's product-hour
    for room_info in rooms.values():
        for hour_str, hdata in room_info['_hourly_stats'].items():
            for pname, pinfo in hdata['products'].items():
                total = product_hour_totals.get((pname, hour_str), 0)
                pinfo['market_pct'] = round(pinfo['orders'] / total * 100, 1) if total > 0 else 0

    return {
        'date': str(df['date'].iloc[0]),
        'total_orders': int(len(df)),
        'total_revenue': float(round(df['price'].sum(), 2)),
        'avg_price': float(round(df['price'].mean(), 2)),
        'products': all_products,
        'rooms': rooms,
        'our_rooms': our_rooms,
        'comp_rooms': comp_rooms,
        'type_summary': type_summary,
        '_hourly_stats': hourly_stats
    }


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def print_comparison(today, yesterday=None):
    print()
    print("=" * 70)
    print(f"  小米手环直播间竞对分析 - {today['date']}")
    print("=" * 70)

    type_summary = today.get('type_summary', {})
    our_rooms = today.get('our_rooms', [])
    comp_rooms = today.get('comp_rooms', [])
    rooms = today.get('rooms', {})

    # ===== 我方 vs 竞对 总览 =====
    if '我方' in type_summary and '竞对' in type_summary:
        o = type_summary['我方']
        c = type_summary['竞对']
        total = today['total_orders']
        o_pct = o['orders'] / total * 100
        c_pct = c['orders'] / total * 100
        order_gap = c['orders'] - o['orders']
        rev_gap = c['revenue'] - o['revenue']
        price_gap = c['avg_price'] - o['avg_price']

        print(f"\n  【我方 vs 竞对 总览】")
        print(f"    {'':<15s} {'订单':>8s} {'占比':>8s} {'销售额':>14s} {'均价':>10s} {'直播间':>8s}")
        print(f"    {'-'*65}")
        print(f"    {'★ 我方':<15s} {o['orders']:>8} {o_pct:>7.1f}%  "
              f"RMB {o['revenue']:>10,.0f}  RMB {o['avg_price']:>6.0f}  {o['rooms']:>6}")
        print(f"    {'竞对合计':<15s} {c['orders']:>8} {c_pct:>7.1f}%  "
              f"RMB {c['revenue']:>10,.0f}  RMB {c['avg_price']:>6.0f}  {c['rooms']:>6}")
        print(f"    {'-'*65}")
        gap_word = '落后' if order_gap > 0 else '领先'
        print(f"    {'差距':<15s} {abs(order_gap):>8} 单    "
              f"RMB {abs(rev_gap):>10,.0f}     "
              f"RMB {abs(price_gap):>6.0f}")
        print(f"    我方订单量为竞对的 {o['orders']/c['orders']*100:.1f}%")
        if price_gap > 0:
            print(f"    我方均价低于竞对 RMB {price_gap:.0f}，需关注定价策略")

    # ===== 逐房间对比 =====
    if len(rooms) > 1:
        print(f"\n  【各直播间明细对比】")
        header = f"    {'直播间':<22s} {'类型':>4s} {'订单':>6s} {'占比':>7s} {'销售额':>12s} {'均价':>8s} {'SKU':>5s}"
        print(header)
        print(f"    {'-'*70}")
        total_orders = today['total_orders']
        sorted_rooms = sorted(rooms.items(), key=lambda x: x[1]['orders'], reverse=True)
        for name, info in sorted_rooms:
            pct = info['orders'] / total_orders * 100
            rtype = info.get('type', '竞对')
            marker = '★' if rtype == '我方' else ' '
            sku_count = len(info['products'])
            print(f"  {marker} {name:<22s} {rtype:>4s} {info['orders']:>6} {pct:>6.1f}% "
                  f"RMB {info['revenue']:>10,.0f} RMB {info['avg_price']:>6.0f} {sku_count:>5}")

        # ===== 我方 vs 竞对 逐个对比 =====
        print(f"\n  【我方各房间 vs 竞对同类型房间 差距分析】")

        # Find counterpart comparisons: our rooms vs similar competitor rooms
        # Match by category: 手环 vs 手环, 手表 vs 手表, 旗舰店 vs 旗舰店
        counterpart_keywords = [
            ('手环', '手环'),
            ('手表', '手表'),
            ('旗舰店', '旗舰店'),
        ]

        matched_comps = set()
        for our_name in our_rooms:
            our_info = rooms[our_name]
            # Find best competitor match
            best_match = None
            for kw_our, kw_comp in counterpart_keywords:
                if kw_our in our_name:
                    for comp_name in comp_rooms:
                        if kw_comp in comp_name and comp_name not in matched_comps:
                            best_match = comp_name
                            break
                    if best_match:
                        break

            if best_match:
                matched_comps.add(best_match)
                comp_info = rooms[best_match]
                o_gap = our_info['orders'] - comp_info['orders']
                r_gap = our_info['revenue'] - comp_info['revenue']
                p_gap = our_info['avg_price'] - comp_info['avg_price']
                ratio = our_info['orders'] / comp_info['orders'] * 100 if comp_info['orders'] else 0

                status = '领先' if o_gap > 0 else '落后'
                print(f"    {our_name} vs {best_match}:")
                print(f"      订单: {our_info['orders']} vs {comp_info['orders']} → "
                      f"{status} {abs(o_gap)} 单 (我方为对手的 {ratio:.1f}%)")
                print(f"      均价: RMB {our_info['avg_price']:.0f} vs RMB {comp_info['avg_price']:.0f} → "
                      f"差距 RMB {p_gap:+.0f}")
                print(f"      销售额: RMB {our_info['revenue']:,.0f} vs RMB {comp_info['revenue']:,.0f} → "
                      f"差距 RMB {r_gap:+,.0f}")
            else:
                print(f"    {our_name}: 未找到直接对标的竞对直播间")

        # Unmatched competitor rooms
        for comp_name in comp_rooms:
            if comp_name not in matched_comps:
                comp_info = rooms[comp_name]
                print(f"    {comp_name} (竞对): {comp_info['orders']} 单, "
                      f"无直接对应的我方直播间")

    # ===== 产品重叠分析 =====
    our_prod_sets = [set(rooms[r]['products'].keys()) for r in our_rooms]
    comp_prod_sets = [set(rooms[r]['products'].keys()) for r in comp_rooms]
    if our_prod_sets and comp_prod_sets:
        all_ours = set().union(*our_prod_sets) if our_prod_sets else set()
        all_comps = set().union(*comp_prod_sets) if comp_prod_sets else set()
        shared = all_ours & all_comps
        only_ours = all_ours - all_comps
        only_comps = all_comps - all_ours

        print(f"\n  【产品线重叠分析】")
        print(f"    共同产品 ({len(shared)}): {', '.join(sorted(shared)) if shared else '无'}")
        if only_ours:
            print(f"    我方独有 ({len(only_ours)}): {', '.join(sorted(only_ours))}")
        if only_comps:
            print(f"    竞对独有 ({len(only_comps)}): {', '.join(sorted(only_comps))}")

    # ===== 热销产品 =====
    print(f"\n  【热销产品 (全部汇总)】")
    sorted_prods = sorted(today['products'].items(), key=lambda x: x[1]['orders'], reverse=True)
    for i, (name, info) in enumerate(sorted_prods[:8]):
        pct = info['orders'] / today['total_orders'] * 100
        print(f"    {i+1}. {name:<25s}  订单: {info['orders']:>4} ({pct:>5.1f}%)  "
              f"销售额: RMB {info['revenue']:>10,.2f}  均价: RMB {info['avg_price']:.0f}")

    # ===== 高峰时段 =====
    print(f"\n  【出单高峰时段】")
    if '_hourly_stats' in today:
        sorted_hours = sorted(today['_hourly_stats'].items(),
                              key=lambda x: x[1]['orders'], reverse=True)
        for hour, stats in sorted_hours[:5]:
            print(f"    {hour:>2}:00 - 订单: {stats['orders']:>4} 单  "
                  f"销售额: RMB {stats['revenue']:>10,.2f}")

    # ===== 总结 =====
    if '我方' in type_summary and '竞对' in type_summary:
        o = type_summary['我方']
        c = type_summary['竞对']
        print(f"\n  【总结】")
        if o['orders'] < c['orders']:
            print(f"    我方在订单量上落后竞对 {c['orders'] - o['orders']} 单，"
                  f"我方仅占整体 {o['orders']/today['total_orders']*100:.1f}% 份额")
        if o['avg_price'] < c['avg_price']:
            print(f"    我方均价 (RMB {o['avg_price']:.0f}) 低于竞对 (RMB {c['avg_price']:.0f})，"
                  f"需评估是否提价或优化产品结构")
        else:
            print(f"    我方均价 (RMB {o['avg_price']:.0f}) 高于竞对 (RMB {c['avg_price']:.0f})，"
                  f"定价端有优势")

        # Best/worst performing our room
        our_sorted = sorted([(r, rooms[r]) for r in our_rooms], key=lambda x: x[1]['orders'], reverse=True)
        print(f"    我方表现最好: {our_sorted[0][0]} ({our_sorted[0][1]['orders']} 单)")
        print(f"    我方表现最弱: {our_sorted[-1][0]} ({our_sorted[-1][1]['orders']} 单)")

    print()
    print("=" * 70)


def update(filepath, our_filepath=None):
    if our_filepath:
        print(f"Loading data source 1: {filepath}")
        df1 = load_and_clean(filepath)
        print(f"Loading data source 2: {our_filepath}")
        df2 = load_and_clean(our_filepath)
        df = pd.concat([df1, df2], ignore_index=True)
        # Fill missing dates from available time data
        valid_dates = df['date'].dropna()
        if len(valid_dates) > 0:
            df['date'] = df['date'].fillna(valid_dates.mode().iloc[0])
        dup = set(df1['room'].unique()) & set(df2['room'].unique())
        if dup:
            print(f"Rooms in both sources (summed): {', '.join(sorted(dup))}")
        n_our_rooms = len([r for r in df['room'].unique() if r in OUR_ROOMS])
        n_comp_rooms = df['room'].nunique() - n_our_rooms
        n_our_orders = len(df[df['type'] == '我方'])
        n_comp_orders = len(df[df['type'] == '竞对'])
        print(f"Combined: {len(df)} orders ({n_our_orders} ours + {n_comp_orders} comp), "
              f"{df['room'].nunique()} rooms ({n_our_rooms} ours + {n_comp_rooms} comp)")
    else:
        print(f"Loading: {filepath}")
        df = load_and_clean(filepath)
    today = summarize_day(df)

    # Load history and compare
    history = load_history()

    yesterday = None
    if history:
        yesterday = history[-1]
        if yesterday['date'] == today['date']:
            # Same date — replace (upsert)
            history.pop(-1)
            yesterday = history[-1] if history else None

    # Print comparison
    print_comparison(today, yesterday)

    # Save
    history.append(today)
    history.sort(key=lambda x: x['date'])
    save_history(history)
    print(f"History updated: {len(history)} days saved to {HISTORY_FILE}")

    # Generate charts
    from generate_dashboard import generate_dashboard, generate_room_comparison, generate_comparison_report
    dashboard_path = generate_dashboard(df)
    print(f"Overall dashboard: {dashboard_path}")

    rooms = today.get('rooms', {})
    if len(rooms) > 1:
        our_rooms = today.get('our_rooms', [])
        room_comparison_path = generate_room_comparison(df, our_rooms=our_rooms)
        print(f"Room comparison chart: {room_comparison_path}")

    if len(history) >= 2:
        comparison_path = generate_comparison_report(history)
        print(f"Day-over-day comparison: {comparison_path}")

    # Build HTML
    from build_html import main as build_html
    build_html()

    return today, history


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        # Two files: competitor data + our data
        update(sys.argv[1], our_filepath=sys.argv[2])
    elif len(sys.argv) > 1:
        # One combined file
        update(sys.argv[1])
    else:
        update(os.path.join(DATA_DIR, '小米手环分析.xlsx'))
