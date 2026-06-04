import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
import os

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')

OUR_ROOMS = {
    '小米数码旗舰店', '小米官方手表', '小米官方手环直播间',
    '小米官方耳机直播间', '小米手环10Pro直播间',
}

COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
          '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
ROOM_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']


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
    elif '耳机' in name or 'Buds' in name:
        return '耳机配件'
    elif 'AI眼镜' in name or 'AI 眼镜' in name:
        return '小米AI眼镜'
    elif '手环8' in name or 'Band 8' in name:
        return '小米手环8'
    elif '头戴' in name:
        return '头戴式耳机'
    elif '插线板' in name or '插座' in name:
        return '插线板/配件'
    else:
        return name[:25]


def analyze_data(filepath):
    df = pd.read_excel(filepath)
    ncols = len(df.columns)
    if ncols >= 5:
        df = df.iloc[:, :5]
        df.columns = ['product', 'price', 'time', 'room', 'type']
    elif ncols == 4:
        df = df.iloc[:, :4]
        df.columns = ['product', 'price', 'time', 'room']
        df['type'] = '竞对'
    else:
        df.columns = ['product', 'price', 'time']
        df['room'] = '未知直播间'
        df['type'] = '竞对'

    df['product'] = df['product'].astype(str).str.replace('\t', '', regex=False)
    df['time'] = df['time'].astype(str).str.replace('\t', '', regex=False)
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['time'] = pd.to_datetime(df['time'])
    df['date'] = df['time'].dt.date
    df['hour'] = df['time'].dt.hour
    df['product_short'] = df['product'].apply(shorten_product)
    df['room'] = df['room'].astype(str).str.strip()
    df['type'] = df['room'].apply(lambda r: '我方' if r in OUR_ROOMS else '竞对')
    return df


def generate_dashboard(df, output_path=None):
    if output_path is None:
        output_path = os.path.join(DATA_DIR, 'dashboard.png')

    date_str = str(df['date'].iloc[0])
    total_orders = len(df)
    total_revenue = df['price'].sum()
    avg_price = df['price'].mean()
    rooms = df['room'].nunique()

    fig = plt.figure(figsize=(20, 14))
    title = f'小米手环直播间销量仪表盘 - {date_str}'
    if rooms > 1:
        title += f' ({rooms}个直播间)'
    fig.suptitle(title, fontsize=20, fontweight='bold', y=0.98)

    # 1. Product orders bar chart (top left)
    ax1 = fig.add_subplot(2, 3, 1)
    product_counts = df['product_short'].value_counts().head(8)
    bars = ax1.barh(range(len(product_counts)), product_counts.values, color=COLORS[:len(product_counts)])
    ax1.set_yticks(range(len(product_counts)))
    ax1.set_yticklabels(product_counts.index, fontsize=10)
    ax1.set_xlabel('订单数')
    ax1.set_title(f'各产品订单量 (Top 8)\n总订单: {total_orders} 单')
    ax1.invert_yaxis()
    for bar, val in zip(bars, product_counts.values):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                 str(val), va='center', fontsize=9)

    # 2. Revenue by product pie chart (top middle)
    ax2 = fig.add_subplot(2, 3, 2)
    rev_by_product = df.groupby('product_short')['price'].sum().sort_values(ascending=False)
    top_rev = rev_by_product.head(6)
    other_rev = rev_by_product[6:].sum()
    if other_rev > 0:
        top_rev['其他'] = other_rev
    wedges, texts, autotexts = ax2.pie(
        top_rev.values, labels=top_rev.index, autopct='%1.1f%%',
        colors=COLORS[:len(top_rev)], startangle=90, pctdistance=0.75
    )
    for t in autotexts:
        t.set_fontsize(8)
    ax2.set_title(f'产品收入占比\n总销售额: RMB {total_revenue:,.0f}')

    # 3. Hourly order trend (top right)
    ax3 = fig.add_subplot(2, 3, 3)
    hourly_orders = df.groupby('hour').size()
    hours = range(24)
    orders = [hourly_orders.get(h, 0) for h in hours]
    ax3.fill_between(hours, orders, alpha=0.3, color='#FF6B6B')
    ax3.plot(hours, orders, color='#FF6B6B', linewidth=2, marker='o', markersize=4)
    ax3.set_xlabel('小时')
    ax3.set_ylabel('订单数')
    ax3.set_title('24小时订单分布')
    ax3.set_xticks(range(0, 24, 2))
    ax3.grid(True, alpha=0.3)
    peak_hour = max(hours, key=lambda h: orders[h])
    ax3.annotate(f'高峰: {peak_hour}:00 ({orders[peak_hour]} 单)',
                 xy=(peak_hour, orders[peak_hour]),
                 xytext=(peak_hour + 2, orders[peak_hour] + 5),
                 arrowprops=dict(arrowstyle='->', color='black'), fontsize=9)

    # 4. Hourly revenue trend (bottom left)
    ax4 = fig.add_subplot(2, 3, 4)
    hourly_rev = df.groupby('hour')['price'].sum()
    rev_list = [hourly_rev.get(h, 0) for h in hours]
    ax4.fill_between(hours, [r/1000 for r in rev_list], alpha=0.3, color='#4ECDC4')
    ax4.plot(hours, [r/1000 for r in rev_list], color='#4ECDC4', linewidth=2, marker='o', markersize=4)
    ax4.set_xlabel('小时')
    ax4.set_ylabel('销售额（千元）')
    ax4.set_title('24小时销售额趋势')
    ax4.set_xticks(range(0, 24, 2))
    ax4.grid(True, alpha=0.3)

    # 5. Price distribution histogram (bottom middle)
    ax5 = fig.add_subplot(2, 3, 5)
    ax5.hist(df['price'], bins=30, color='#45B7D1', edgecolor='white', alpha=0.8)
    ax5.axvline(avg_price, color='red', linestyle='--', linewidth=2, label=f'均价: RMB {avg_price:.0f}')
    ax5.set_xlabel('价格 (RMB)')
    ax5.set_ylabel('订单数')
    ax5.set_title('价格分布')
    ax5.legend()

    # 6. KPI summary + room breakdown (bottom right)
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis('off')

    top_product = product_counts.index[0]
    top_product_orders = product_counts.values[0]
    top_product_pct = top_product_orders / total_orders * 100

    text = f"关键指标汇总\n{'='*40}\n\n"
    text += f"总订单数:        {total_orders} 单\n"
    text += f"总销售额:        RMB {total_revenue:,.0f}\n"
    text += f"平均单价:        RMB {avg_price:.0f}\n"
    text += f"直播间数:        {rooms}\n\n"
    text += f"{'-'*40}\n"
    text += f"销冠产品:        {top_product}\n"
    text += f"  销量:          {top_product_orders} 单 ({top_product_pct:.1f}%)\n\n"

    if rooms > 1:
        text += f"{'-'*40}\n各直播间订单占比:\n"
        for room_name, room_df in df.groupby('room'):
            pct = len(room_df) / total_orders * 100
            text += f"  {room_name}: {len(room_df)} ({pct:.1f}%)\n"

    ax6.text(0.05, 0.5, text, transform=ax6.transAxes,
             fontsize=11, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path


def generate_room_comparison(df, our_rooms=None, output_path=None):
    """Generate multi-room comparison chart with our-vs-competitor highlighting"""
    if output_path is None:
        output_path = os.path.join(DATA_DIR, 'room_comparison.png')

    if our_rooms is None:
        our_rooms = []
    if isinstance(our_rooms, str):
        our_rooms = [our_rooms]

    rooms = sorted(df['room'].unique())
    if len(rooms) < 2:
        print("Only one room found, skipping room comparison chart")
        return None

    date_str = str(df['date'].iloc[0])

    # Determine room type from data
    room_type = {}
    for room in rooms:
        rdf = df[df['room'] == room]
        rtype = rdf['type'].iloc[0] if 'type' in rdf.columns else '竞对'
        room_type[room] = rtype
        if rtype == '我方' and room not in our_rooms:
            our_rooms.append(room)

    is_ours = lambda r: room_type.get(r) == '我方'

    fig = plt.figure(figsize=(22, 16))
    title = f'直播间竞对分析 - {date_str}'
    our_count = sum(1 for r in rooms if is_ours(r))
    comp_count = len(rooms) - our_count
    if our_count > 0:
        title += f'  (我方 {our_count} 间 vs 竞对 {comp_count} 间)'
    fig.suptitle(title, fontsize=20, fontweight='bold', y=0.98)

    # Room data
    room_stats = {}
    for room in rooms:
        rdf = df[df['room'] == room]
        room_stats[room] = {
            'orders': len(rdf),
            'revenue': rdf['price'].sum(),
            'avg_price': rdf['price'].mean(),
            'sku': rdf['product_short'].nunique(),
            'top_product': rdf['product_short'].value_counts().index[0],
            'top_product_orders': rdf['product_short'].value_counts().values[0],
        }

    total_orders = df['room'].value_counts().sum()
    n_rooms = len(rooms)

    # 1. Orders by room (horizontal bar) - top left
    ax1 = fig.add_subplot(2, 3, 1)
    room_order = sorted(rooms, key=lambda r: room_stats[r]['orders'], reverse=True)
    order_vals = [room_stats[r]['orders'] for r in room_order]
    bar_colors = []
    for r in room_order:
        if is_ours(r):
            bar_colors.append('#FFD700')  # gold for our rooms
        else:
            bar_colors.append(ROOM_COLORS[room_order.index(r) % len(ROOM_COLORS)])

    bars = ax1.barh(range(len(room_order)), order_vals, color=bar_colors)
    ax1.set_yticks(range(len(room_order)))
    ax1.set_yticklabels(room_order, fontsize=11)
    ax1.set_xlabel('订单数')
    ax1.set_title(f'各直播间订单量对比\n(总计: {total_orders} 单)')
    ax1.invert_yaxis()
    for bar, val in zip(bars, order_vals):
        pct = val / total_orders * 100
        ax1.text(bar.get_width() + 3, bar.get_y() + bar.get_height()/2,
                 f'{val} ({pct:.1f}%)', va='center', fontsize=10)

    # 2. Revenue by room (horizontal bar) - top middle
    ax2 = fig.add_subplot(2, 3, 2)
    rev_order = sorted(rooms, key=lambda r: room_stats[r]['revenue'], reverse=True)
    rev_vals = [room_stats[r]['revenue'] for r in rev_order]
    rev_colors = []
    for r in rev_order:
        if is_ours(r):
            rev_colors.append('#FFD700')
        else:
            rev_colors.append(ROOM_COLORS[rev_order.index(r) % len(ROOM_COLORS)])

    bars = ax2.barh(range(len(rev_order)), rev_vals, color=rev_colors)
    ax2.set_yticks(range(len(rev_order)))
    ax2.set_yticklabels(rev_order, fontsize=11)
    ax2.set_xlabel('销售额 (RMB)')
    ax2.set_title('各直播间销售额对比')
    ax2.invert_yaxis()
    for bar, val in zip(bars, rev_vals):
        ax2.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
                 f'RMB {val:,.0f}', va='center', fontsize=10)

    # 3. Avg price + SKU count (dual metric) - top right
    ax3 = fig.add_subplot(2, 3, 3)
    x = np.arange(n_rooms)
    width = 0.35
    avg_prices = [room_stats[r]['avg_price'] for r in rooms]
    skus = [room_stats[r]['sku'] for r in rooms]

    bars1 = ax3.bar(x - width/2, avg_prices, width, label='平均单价 (RMB)', color='#FF6B6B', alpha=0.85)
    ax3.set_ylabel('平均单价 (RMB)', color='#FF6B6B')
    ax3.tick_params(axis='y', labelcolor='#FF6B6B')
    ax3_2 = ax3.twinx()
    bars2 = ax3_2.bar(x + width/2, skus, width, label='SKU数', color='#45B7D1', alpha=0.85)
    ax3_2.set_ylabel('SKU数', color='#45B7D1')
    ax3_2.tick_params(axis='y', labelcolor='#45B7D1')

    ax3.set_xticks(x)
    ax3.set_xticklabels(rooms, fontsize=9, rotation=15)
    ax3.set_title('均价 vs SKU数 对比')

    for bar, val in zip(bars1, avg_prices):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f'RMB {val:.0f}', ha='center', fontsize=9)
    for bar, val in zip(bars2, skus):
        ax3_2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 str(val), ha='center', fontsize=9)

    lines1, labels1 = ax3.get_legend_handles_labels()
    lines2, labels2 = ax3_2.get_legend_handles_labels()
    ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)

    # 4. Product mix comparison (grouped bar, top products) - bottom left
    ax4 = fig.add_subplot(2, 3, 4)

    # Find top products across all rooms
    all_prod_orders = {}
    for room in rooms:
        rdf = df[df['room'] == room]
        for prod, count in rdf['product_short'].value_counts().items():
            all_prod_orders[prod] = all_prod_orders.get(prod, 0) + count
    top_products = sorted(all_prod_orders, key=all_prod_orders.get, reverse=True)[:6]

    x = np.arange(len(top_products))
    width = 0.8 / n_rooms
    for i, room in enumerate(rooms):
        rdf = df[df['room'] == room]
        prod_counts = rdf['product_short'].value_counts()
        vals = [prod_counts.get(p, 0) for p in top_products]
        offset = (i - n_rooms/2 + 0.5) * width
        label = room
        if is_ours(room):
            label = f'★ {room} (我方)'
        ax4.bar(x + offset, vals, width, label=label, alpha=0.85,
                color='#FFD700' if is_ours(room) else ROOM_COLORS[i % len(ROOM_COLORS)])

    ax4.set_xticks(x)
    ax4.set_xticklabels(top_products, fontsize=9, rotation=20)
    ax4.set_title('各直播间产品结构对比 (Top 6产品)')
    ax4.set_ylabel('订单数')
    ax4.legend(fontsize=8, loc='upper right')

    # 5. Hourly orders overlay - bottom middle
    ax5 = fig.add_subplot(2, 3, 5)
    hours = range(24)
    for i, room in enumerate(rooms):
        rdf = df[df['room'] == room]
        hourly = rdf.groupby('hour').size()
        vals = [hourly.get(h, 0) for h in hours]
        label = room
        if is_ours(room):
            label = f'★ {room} (我方)'
            ax5.plot(hours, vals, color='#FFD700', linewidth=3, marker='o', markersize=5, label=label)
        else:
            ax5.plot(hours, vals, color=ROOM_COLORS[i % len(ROOM_COLORS)],
                     linewidth=1.8, marker='o', markersize=4, label=label, alpha=0.8)
    ax5.set_xlabel('小时')
    ax5.set_ylabel('订单数')
    ax5.set_title('各直播间24小时订单分布对比')
    ax5.set_xticks(range(0, 24, 2))
    ax5.legend(fontsize=8)
    ax5.grid(True, alpha=0.3)

    # 6. Summary stats table - bottom right
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis('off')

    # Determine rank for each room
    order_rank = {r: i+1 for i, r in enumerate(sorted(rooms, key=lambda r: room_stats[r]['orders'], reverse=True))}
    rev_rank = {r: i+1 for i, r in enumerate(sorted(rooms, key=lambda r: room_stats[r]['revenue'], reverse=True))}
    price_rank = {r: i+1 for i, r in enumerate(sorted(rooms, key=lambda r: room_stats[r]['avg_price'], reverse=True))}

    text = f"竞对分析汇总\n{'='*45}\n\n"
    for room in rooms:
        s = room_stats[room]
        marker = '★' if is_ours(room) else '  '
        text += f"{marker} {room}\n"
        text += f"  订单: {s['orders']:>4} 单 (第{order_rank[room]}名)  "
        text += f"销售额: RMB {s['revenue']:,.0f}\n"
        text += f"  均价: RMB {s['avg_price']:.0f} (第{price_rank[room]}名)  "
        text += f"SKU数: {s['sku']}\n"
        text += f"  销冠: {s['top_product']} ({s['top_product_orders']}单)\n\n"

    # Add insights
    if len(rooms) >= 2:
        top_r = max(rooms, key=lambda r: room_stats[r]['orders'])
        bottom_r = min(rooms, key=lambda r: room_stats[r]['orders'])
        gap = room_stats[top_r]['orders'] - room_stats[bottom_r]['orders']
        ratio = room_stats[bottom_r]['orders'] / room_stats[top_r]['orders'] * 100
        text += f"{'-'*45}\n"
        text += f"订单差距: {top_r} vs {bottom_r}\n"
        text += f"差距 {gap} 单, 末位是榜首的 {ratio:.1f}%\n"

        # Check if orders and revenue rank match
        if order_rank != rev_rank:
            text += f"\n注: 订单排名 ≠ 销售额排名 (均价差异导致)"

    ax6.text(0.02, 0.5, text, transform=ax6.transAxes,
             fontsize=9, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path


def generate_comparison_report(history, output_path=None):
    """Generate day-over-day comparison chart"""
    if len(history) < 2:
        print("Need at least 2 days of data for comparison")
        return None

    if output_path is None:
        output_path = os.path.join(DATA_DIR, 'comparison.png')

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('每日销售对比', fontsize=18, fontweight='bold')

    dates = [h['date'] for h in history]
    orders = [h['total_orders'] for h in history]
    revenue = [h['total_revenue'] for h in history]
    avg_price = [h['avg_price'] for h in history]

    # Orders trend
    axes[0, 0].bar(dates, orders, color='#FF6B6B', alpha=0.8)
    axes[0, 0].set_title('每日订单量')
    axes[0, 0].set_ylabel('订单数')
    for i, (d, o) in enumerate(zip(dates, orders)):
        axes[0, 0].text(i, o + max(orders)*0.02, str(o), ha='center', fontsize=10)
    if len(dates) >= 2:
        change = orders[-1] - orders[-2]
        pct = change / orders[-2] * 100
        axes[0, 0].set_xlabel(f'日环比: {change:+d} ({pct:+.1f}%)')

    # Revenue trend
    rev_k = [r/1000 for r in revenue]
    axes[0, 1].bar(dates, rev_k, color='#4ECDC4', alpha=0.8)
    axes[0, 1].set_title('每日销售额')
    axes[0, 1].set_ylabel('销售额（千元）')
    for i, (d, r) in enumerate(zip(dates, rev_k)):
        axes[0, 1].text(i, r + max(rev_k)*0.02, f'RMB {r:.1f}K', ha='center', fontsize=10)
    if len(dates) >= 2:
        change = rev_k[-1] - rev_k[-2]
        pct = change / rev_k[-2] * 100
        axes[0, 1].set_xlabel(f'日环比: {change:+.1f}K ({pct:+.1f}%)')

    # Avg price trend
    axes[1, 0].plot(dates, avg_price, color='#45B7D1', linewidth=2, marker='s', markersize=8)
    axes[1, 0].set_title('平均单价趋势')
    axes[1, 0].set_ylabel('单价 (RMB)')
    for d, p in zip(dates, avg_price):
        axes[1, 0].annotate(f'RMB {p:.0f}', (d, p), textcoords="offset points", xytext=(0, 10),
                            ha='center', fontsize=9)
    axes[1, 0].grid(True, alpha=0.3)

    # Product comparison across days
    ax = axes[1, 1]
    all_products = set()
    for h in history:
        all_products.update(h['products'].keys())
    total_orders_by_product = {}
    for p in all_products:
        total_orders_by_product[p] = sum(h['products'].get(p, {}).get('orders', 0) for h in history)
    top_products = sorted(total_orders_by_product, key=total_orders_by_product.get, reverse=True)[:6]

    x = np.arange(len(dates))
    width = 0.8 / len(top_products)
    for i, prod in enumerate(top_products):
        prod_orders = [h['products'].get(prod, {}).get('orders', 0) for h in history]
        offset = (i - len(top_products)/2 + 0.5) * width
        ax.bar(x + offset, prod_orders, width, label=prod, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(dates)
    ax.set_title('各产品每日订单量对比')
    ax.set_ylabel('订单数')
    ax.legend(fontsize=7, loc='upper right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = os.path.join(DATA_DIR, '小米手环分析.xlsx')

    print(f'Analyzing: {filepath}')
    df = analyze_data(filepath)

    dashboard_path = generate_dashboard(df)
    print(f'Dashboard saved to: {dashboard_path}')

    if df['room'].nunique() > 1:
        room_path = generate_room_comparison(df)
        print(f'Room comparison saved to: {room_path}')
