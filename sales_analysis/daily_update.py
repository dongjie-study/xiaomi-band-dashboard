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
from pathlib import Path

# Ensure project root is in Python path for shared module imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from team_config import TEAM_MAP, classify_room, ALL_TEAMS, OUR_TEAM
from product_classifier import classify_product as shorten_product
from utils import detect_excel_columns

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')


def load_and_clean(filepath):
    """
    Load and clean an Excel file of live stream orders.

    Auto-detects column roles by keyword matching, standardizes column names,
    parses dates, classifies products and teams.

    Args:
        filepath: Path to Excel file.

    Returns:
        Cleaned DataFrame with columns: product, price, time, room, type,
        date, hour, product_short.
    """
    try:
        df = pd.read_excel(filepath)
    except FileNotFoundError:
        print(f"Error: File not found — {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read Excel file — {e}")
        sys.exit(1)
    col_map = detect_excel_columns(df)

    cols = []
    for key in ['product', 'price', 'time', 'room', 'type']:
        cols.append(col_map.get(key))

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
    # Classify by room name into teams
    df['type'] = df['room'].apply(classify_room)
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
        rsum['type'] = classify_room(room_name)
        rooms[room_name] = rsum

    # Identify rooms by team
    our_rooms = [r for r, info in rooms.items() if info['type'] == '我司']
    jixie_rooms = [r for r, info in rooms.items() if info['type'] == '机械空间']
    zongheng_rooms = [r for r, info in rooms.items() if info['type'] == '纵横']
    liangmi_rooms = [r for r, info in rooms.items() if info['type'] == '良米']
    comp_rooms = jixie_rooms + zongheng_rooms + liangmi_rooms

    # Type-level aggregates
    type_summary = {}
    for t in ALL_TEAMS:
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
        'jixie_rooms': jixie_rooms,
        'zongheng_rooms': zongheng_rooms,
        'liangmi_rooms': liangmi_rooms,
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
        json.dump(history, f, ensure_ascii=False, separators=(',', ':'))


def print_comparison(today, yesterday=None):
    print()
    print("=" * 70)
    print(f"  小米手环直播间竞对分析 - {today['date']}")
    print("=" * 70)

    type_summary = today.get('type_summary', {})
    our_rooms = today.get('our_rooms', [])
    comp_rooms = today.get('comp_rooms', [])
    rooms = today.get('rooms', {})

    # ===== 团队总览 =====
    team_colors = {'我司': '★', '机械空间': '◆', '纵横': '▲', '凝云': '●', '良米': '·'}
    print(f"\n  【四队总览】")
    print(f"    {'':<15s} {'订单':>8s} {'占比':>8s} {'销售额':>14s} {'均价':>10s} {'直播间':>8s}")
    print(f"    {'-'*65}")
    total = today['total_orders']
    for t in ALL_TEAMS:
        if t in type_summary:
            ts = type_summary[t]
            pct = ts['orders'] / total * 100
            marker = team_colors.get(t, ' ')
            print(f"    {marker} {t:<13s} {ts['orders']:>8} {pct:>7.1f}%  "
                  f"RMB {ts['revenue']:>10,.0f}  RMB {ts['avg_price']:>6.0f}  {ts['rooms']:>6}")

    # ===== 房间明细 =====
    if len(rooms) > 1:
        print(f"\n  【各直播间明细】")
        header = f"    {'直播间':<22s} {'团队':>6s} {'订单':>6s} {'占比':>7s} {'销售额':>12s} {'均价':>8s} {'SKU':>5s}"
        print(header)
        print(f"    {'-'*70}")
        total_orders = today['total_orders']
        sorted_rooms = sorted(rooms.items(), key=lambda x: x[1]['orders'], reverse=True)
        for name, info in sorted_rooms:
            pct = info['orders'] / total_orders * 100
            rtype = info.get('type', '良米')
            marker = team_colors.get(rtype, ' ')
            sku_count = len(info['products'])
            print(f"  {marker} {name:<22s} {rtype:>6s} {info['orders']:>6} {pct:>6.1f}% "
                  f"RMB {info['revenue']:>10,.0f} RMB {info['avg_price']:>6.0f} {sku_count:>5}")

    # ===== 我司 vs 其他团队对比 =====
    if our_rooms and comp_rooms:
        print(f"\n  【我司房间 vs 对标房间】")
        counterpart_keywords = [
            ('手环', '手环'), ('手表', '手表'), ('旗舰店', '旗舰店'),
        ]
        matched_comps = set()
        for our_name in our_rooms:
            our_info = rooms[our_name]
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
                ratio = our_info['orders'] / comp_info['orders'] * 100 if comp_info['orders'] else 0
                status = '领先' if o_gap > 0 else '落后'
                print(f"    {our_name} vs {best_match}:")
                print(f"      订单: {our_info['orders']} vs {comp_info['orders']} → {status} {abs(o_gap)}单 ({ratio:.1f}%)")
                print(f"      均价: RMB {our_info['avg_price']:.0f} vs RMB {comp_info['avg_price']:.0f}")
            else:
                print(f"    {our_name}: 无对标房间")

    # ===== 热销产品 =====
    print(f"\n  【热销产品 TOP8】")
    sorted_prods = sorted(today['products'].items(), key=lambda x: x[1]['revenue'], reverse=True)
    for i, (name, info) in enumerate(sorted_prods[:8]):
        pct = info['orders'] / today['total_orders'] * 100
        print(f"    {i+1}. {name:<25s}  订单: {info['orders']:>4} ({pct:>5.1f}%)  "
              f"销售额: RMB {info['revenue']:>10,.0f}  均价: RMB {info['avg_price']:.0f}")

    # ===== 高峰时段 =====
    print(f"\n  【出单高峰时段】")
    if '_hourly_stats' in today:
        sorted_hours = sorted(today['_hourly_stats'].items(),
                              key=lambda x: x[1]['orders'], reverse=True)
        for hour, stats in sorted_hours[:5]:
            print(f"    {hour:>2}:00 - 订单: {stats['orders']:>4} 单  "
                  f"销售额: RMB {stats['revenue']:>10,.2f}")

    # ===== 总结 =====
    if '我司' in type_summary:
        o = type_summary['我司']
        other_orders = sum(type_summary[t]['orders'] for t in ['机械空间','纵横','良米'] if t in type_summary)
        print(f"\n  【总结】")
        print(f"    我司 {o['orders']} 单 ({o['orders']/today['total_orders']*100:.1f}%), "
              f"均价 RMB {o['avg_price']:.0f}, 销售额 RMB {o['revenue']:,.0f}")
        our_sorted = sorted([(r, rooms[r]) for r in our_rooms], key=lambda x: x[1]['revenue'], reverse=True)
        if our_sorted:
            print(f"    最佳(销售额): {our_sorted[0][0]} (RMB {our_sorted[0][1]['revenue']:,.0f})")
            print(f"    最弱(销售额): {our_sorted[-1][0]} (RMB {our_sorted[-1][1]['revenue']:,.0f})")
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
        n_our_rooms = len([r for r in df['room'].unique() if classify_room(r) == '我司'])
        n_jixie = len([r for r in df['room'].unique() if classify_room(r) == '机械空间'])
        n_zongheng = len([r for r in df['room'].unique() if classify_room(r) == '纵横'])
        n_liangmi = len([r for r in df['room'].unique() if classify_room(r) == '良米'])
        n_our_orders = len(df[df['type'] == '我司'])
        n_jixie_orders = len(df[df['type'] == '机械空间'])
        n_zongheng_orders = len(df[df['type'] == '纵横'])
        n_liangmi_orders = len(df[df['type'] == '良米'])
        print(f"Combined: {len(df)} orders, {df['room'].nunique()} rooms")
        print(f"  我司: {n_our_orders}单/{n_our_rooms}室 | 机械空间: {n_jixie_orders}单/{n_jixie}室 | 纵横: {n_zongheng_orders}单/{n_zongheng}室 | 良米: {n_liangmi_orders}单/{n_liangmi}室")
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

    # Generate charts (import at function level to avoid circular dependency with build_html)
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

    # Build HTML dashboard (sales_analysis/build_html.py)
    from sales_analysis.build_html import main as build_html
    build_html()

    # Generate stats_data.js for root index.html overview
    _write_stats_js(history)

    return today, history


def _write_stats_js(history):
    """Write stats_data.js so root index.html can load overview stats via <script> tag."""
    latest = history[-1]
    rooms = latest.get('rooms', {})
    our_rooms = sum(1 for r in rooms.values() if r.get('type') == '我司')
    team_counts = {}
    for r in rooms.values():
        t = r.get('type', '良米')
        team_counts[t] = team_counts.get(t, 0) + 1
    stats = {
        'date': latest['date'],
        'orders': latest['total_orders'],
        'revenue': round(latest['total_revenue'] / 10000, 1),
        'avg_price': round(latest['avg_price']),
        'rooms': len(rooms),
        'our_rooms': our_rooms,
        'comp_rooms': len(rooms) - our_rooms,
        'team_counts': team_counts,
        'days': len(history),
        'first_date': history[0]['date'],
        'dates': [d['date'] for d in history],
    }
    js = 'window.__STATS__ = ' + json.dumps(stats, ensure_ascii=False) + ';'
    path = os.path.join(DATA_DIR, 'stats_data.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(js)
    print(f"Stats data: {path}")


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        # Two files: competitor data + our data
        update(sys.argv[1], our_filepath=sys.argv[2])
    elif len(sys.argv) > 1:
        # One combined file
        update(sys.argv[1])
    else:
        update(os.path.join(DATA_DIR, '小米手环分析.xlsx'))
