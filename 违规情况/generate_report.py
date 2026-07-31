# -*- coding: utf-8 -*-
import json
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

base = r'C:\Users\Administrator\Desktop\违规情况'

# Try to find a Chinese font
font_paths = [
    'C:\\Windows\\Fonts\\msyh.ttc',
    'C:\\Windows\\Fonts\\simhei.ttf',
    'C:\\Windows\\Fonts\\simsun.ttc',
    'C:\\Windows\\Fonts\\STSONG.TTF',
]
zh_font = None
for fp in font_paths:
    if os.path.exists(fp):
        zh_font = fm.FontProperties(fname=fp)
        break
if zh_font is None:
    # Fallback: use any available CJK font
    for f in fm.fontManager.ttflist:
        if any(kw in f.name.lower() for kw in ['hei', 'song', 'ming', 'cjk', 'chinese', 'yahei', 'micro']):
            zh_font = fm.FontProperties(fname=f.fname)
            break

# ========================
# Manually parsed data from OCR
# ========================
data = {
    "小米官方手环直播间": [
        {"time": "2026-05-02", "reason": "赠品活动信息与宣传不符", "location": "直播口播", "product": "小米手环9 Pro", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "76466358056411958309", "violation_phrase": "赠品六选一"},
        {"time": "2026-05-24", "reason": "售后服务不符", "location": "直播画面", "product": "-", "action": "已撤销", "penalty": "警告(已撤销)", "ticket": "7643349423544205583", "violation_phrase": "一年质保"},
        {"time": "2026-06-06", "reason": "售后服务不符", "location": "直播画面", "product": "小米手环10Pro", "action": "预警", "penalty": "警告", "ticket": "7648165811143688500", "violation_phrase": "全国联保"},
    ],
    "小米官方手表": [
        {"time": "2026-05-13", "reason": "赠品活动信息与宣传不符", "location": "直播画面", "product": "REDMI Watch", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "7539301178585292806", "violation_phrase": "-"},
        {"time": "2026-06-07", "reason": "赠品活动信息与宣传不符", "location": "管理员评论", "product": "REDMI Watch", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "7648496881592516883", "violation_phrase": "凑单到手403起+教育优惠返20+额外腕带"},
        {"time": "2026-05-21", "reason": "售后服务不符", "location": "直播画面", "product": "-", "action": "预警", "penalty": "警告", "ticket": "76422923203391491190", "violation_phrase": "一年质保"},
        {"time": "2026-05-06", "reason": "效果虚假", "location": "直播口播", "product": "REDMI Watch", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播+关闭商品分享1天", "ticket": "7536494293812658473", "violation_phrase": "五十米深度防水(夸大宣传)"},
        {"time": "2026-06-10", "reason": "未使用平台福袋工具", "location": "直播口播", "product": "REDMI Watch", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "76530149197860", "violation_phrase": "引导观众扣订单号到评论区进行抽奖，未使用平台官方福袋工具"},
    ],
    "小米官方耳机直播间": [
        {"time": "2026-05-02", "reason": "赠品活动信息与宣传不符", "location": "直播口播", "product": "REDMI Buds Pro", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "76352147209546632040", "violation_phrase": "赠送耳机包"},
        {"time": "2026-05-16", "reason": "赠品活动信息与宣传不符", "location": "直播口播", "product": "REDMI Buds 8 Pro", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "75404001323196910625", "violation_phrase": "-"},
        {"time": "2026-05-18", "reason": "售后服务不符", "location": "直播画面", "product": "-", "action": "预警", "penalty": "警告", "ticket": "75411094941515287305", "violation_phrase": "无忧质保"},
        {"time": "2026-05-23", "reason": "售后服务不符", "location": "直播口播", "product": "Xiaomi夹式耳机", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "7642750111487148331", "violation_phrase": "一年官方质保以及全国联保"},
        {"time": "2026-05-23", "reason": "赠品活动信息与宣传不符", "location": "直播口播", "product": "Xiaomi Buds", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "7642974458155474226", "violation_phrase": "-"},
        {"time": "2026-05-23", "reason": "售后服务不符", "location": "直播口播", "product": "Xiaomi夹式耳机", "action": "违规", "penalty": "冻结佣金14650.79元30天", "ticket": "7642986916338123062", "violation_phrase": "一年质保和全国联保保质保证"},
        {"time": "2026-05-25", "reason": "售后服务不符", "location": "直播口播", "product": "Xiaomi夹式耳机", "action": "违规", "penalty": "冻结佣金4192.5元30天+关闭商品分享3天", "ticket": "7543509078755770086", "violation_phrase": "线上线下都可以维修"},
        {"time": "2026-05-26", "reason": "综合判定高风险(账号)", "location": "达人账号", "product": "-", "action": "违规", "penalty": "提升风险保证金至3000元90天", "ticket": "76440321333458865140", "violation_phrase": "-"},
        {"time": "2026-05-29", "reason": "售后服务不符", "location": "直播画面", "product": "-", "action": "已撤销", "penalty": "警告(已撤销)", "ticket": "7645066775767286054", "violation_phrase": "品质质保"},
    ],
    "小米手环10pro直播间": [
        {"time": "2026-06-07", "reason": "售后服务不符", "location": "直播画面", "product": "小米手环10Pro", "action": "预警", "penalty": "警告", "ticket": "7548406803645267658", "violation_phrase": "全国联保"},
        {"time": "2026-06-07", "reason": "售后服务不符", "location": "直播文案", "product": "-", "action": "预警", "penalty": "警告", "ticket": "7648621291297407270", "violation_phrase": "-"},
        {"time": "2026-05-27", "reason": "售后服务不符", "location": "直播画面", "product": "便携式折叠衣架", "action": "预警", "penalty": "警告", "ticket": "7542513087310921218", "violation_phrase": "-"},
    ],
    "小米数码旗舰店": [
        {"time": "2026-05-02", "reason": "赠品活动信息与宣传不符", "location": "直播口播", "product": "小米手环9 Pro", "action": "预警", "penalty": "下架商品+冻结佣金5%+中断直播", "ticket": "7635206695983235370", "violation_phrase": "-"},
    ],
}

# ========================
# Compute summary stats
# ========================
all_records = []
for room, violations in data.items():
    for v in violations:
        v['room'] = room
        all_records.append(v)

total = len(all_records)

# Count by reason
from collections import Counter
reason_counter = Counter(v['reason'] for v in all_records)

# Count by action
action_counter = Counter(v['action'] for v in all_records)

# Count by location
loc_counter = Counter(v['location'] for v in all_records)

# Count by month
month_counter = Counter()
for v in all_records:
    try:
        m = v['time'][:7]
    except (ValueError, IndexError, TypeError, KeyError):
        m = '未知'
    month_counter[m] += 1

# Room-level aggregation
room_stats = {}
for room, violations in data.items():
    reasons = Counter(v['reason'] for v in violations)
    actions = Counter(v['action'] for v in violations)
    room_stats[room] = {
        'count': len(violations),
        'top_reason': reasons.most_common(1)[0][0] if reasons else '-',
        'reasons': dict(reasons),
        'actions': dict(actions),
    }

# ========================
# Print text report
# ========================
print("=" * 70)
print("  小米系直播间违规情况分析报告（2026年5月 - 6月7日）")
print("=" * 70)

print(f"\n【总览】共涉及 5 个直播间，累计违规 {total} 次\n")

print("-" * 70)
for room, violations in data.items():
    real_count = sum(1 for v in violations if v['action'] != '已撤销')
    print(f"\n▶ {room}")
    print(f"  违规次数: {len(violations)}（其中已撤销 {len(violations)-real_count} 次，有效 {real_count} 次）")
    stats = room_stats[room]
    print(f"  处置类型: {stats['actions']}")
    print(f"  违规原因分布: {stats['reasons']}")
    print(f"  主要问题: {stats['top_reason']}")
    for i, v in enumerate(violations, 1):
        print(f"  {i}. [{v['action']}] {v['time']} | {v['reason']} | 位置:{v['location']} | 商品:{v['product']} | 处罚:{v['penalty']}")
        if v['violation_phrase'] != '-':
            print(f"     违规表述: \"{v['violation_phrase']}\"")

print("\n" + "=" * 70)
print("  总体统计")
print("=" * 70)

print(f"\n  处置类型分布:")
for k, v in action_counter.most_common():
    print(f"    {k}: {v}次 ({v/total*100:.1f}%)")

print(f"\n  违规原因分布:")
for k, v in reason_counter.most_common():
    print(f"    {k}: {v}次 ({v/total*100:.1f}%)")

print(f"\n  违规位置分布:")
for k, v in loc_counter.most_common():
    print(f"    {k}: {v}次 ({v/total*100:.1f}%)")

print(f"\n  月度趋势:")
for month in sorted(month_counter.keys()):
    bar = '█' * month_counter[month]
    print(f"    {month}: {bar} {month_counter[month]}次")

# Peak day analysis
print(f"\n  高峰日分析:")
day_counter = Counter(v['time'] for v in all_records)
for day, cnt in day_counter.most_common():
    if cnt >= 2:
        rooms_on_day = [v['room'] for v in all_records if v['time'] == day]
        print(f"    {day}: {cnt}次违规 ({', '.join(rooms_on_day)})")

print(f"\n  处罚升级趋势:")
print(f"    预警 → 警告: 大部分首次违规")
print(f"    预警 → 冻结佣金+下架: 涉及赠品/功效虚假类")
print(f"    账号违规 → 提升保证金: 累计违规导致账号风险评级升高")

# ========================
# VISUALIZATION
# ========================

# Use a style
plt.style.use('ggplot')
plt.rcParams['figure.dpi'] = 150
if zh_font:
    plt.rcParams['font.family'] = zh_font.get_name()

# Color palette
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#FF9FF3', '#54A0FF']

# ============
# Figure 1: Comprehensive dashboard (2x2)
# ============
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('小米系直播间违规情况综合分析', fontsize=18, fontweight='bold', y=0.98)

# 1.1 Room violation count
ax = axes[0, 0]
rooms_sorted = sorted(data.items(), key=lambda x: len(x[1]), reverse=True)
room_names = [r[0] for r in rooms_sorted]
counts = [len(r[1]) for r in rooms_sorted]
effective = [sum(1 for v in r[1] if v['action'] != '已撤销') for r in rooms_sorted]

bars = ax.bar(range(len(room_names)), counts, color=colors[:len(room_names)], alpha=0.85, label='总违规次数')
ax.bar(range(len(room_names)), effective, color='white', alpha=0.4, hatch='///', label='有效违规(扣除已撤销)')
ax.set_xticks(range(len(room_names)))
ax.set_xticklabels(room_names, fontsize=9, rotation=30, ha='right')
ax.set_ylabel('次数', fontsize=12)
ax.set_title('各直播间违规次数对比', fontsize=14, fontweight='bold')
ax.legend(fontsize=9)
for i, (c, e) in enumerate(zip(counts, effective)):
    ax.text(i, c + 0.2, str(c), ha='center', fontweight='bold', fontsize=11)

# 1.2 Reason distribution - overall
ax = axes[0, 1]
reasons_labels = list(reason_counter.keys())
reason_vals = list(reason_counter.values())
wedges, texts, autotexts = ax.pie(reason_vals, labels=reasons_labels, autopct='%1.1f%%',
                                   colors=colors[:len(reasons_labels)], startangle=90,
                                   textprops={'fontsize': 10})
ax.set_title('违规原因分布（全部直播间）', fontsize=14, fontweight='bold')

# 1.3 Monthly trend
ax = axes[1, 0]
months_sorted = sorted(month_counter.keys())
if '未知' in months_sorted:
    months_sorted.remove('未知')
month_vals = [month_counter[m] for m in months_sorted]
ax.bar(months_sorted, month_vals, color='#FF6B6B', alpha=0.8, width=0.5)
ax.plot(months_sorted, month_vals, 'o-', color='#2D3436', linewidth=2, markersize=8)
ax.set_xlabel('月份', fontsize=11)
ax.set_ylabel('违规次数', fontsize=11)
ax.set_title('月度违规趋势', fontsize=14, fontweight='bold')
for i, v in enumerate(month_vals):
    ax.text(i, v + 0.3, str(v), ha='center', fontweight='bold', fontsize=11)

# 1.4 Location distribution
ax = axes[1, 1]
locs = list(loc_counter.keys())
loc_vals = list(loc_counter.values())
bars = ax.barh(range(len(locs)), loc_vals, color=colors[:len(locs)], alpha=0.85)
ax.set_yticks(range(len(locs)))
ax.set_yticklabels(locs, fontsize=10)
ax.set_xlabel('次数', fontsize=11)
ax.set_title('违规位置分布', fontsize=14, fontweight='bold')
for i, v in enumerate(loc_vals):
    ax.text(v + 0.2, i, str(v), va='center', fontweight='bold', fontsize=11)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(base, 'report_dashboard.png'), bbox_inches='tight', dpi=150)
plt.close()
print("\n [图1] 综合仪表盘已保存: report_dashboard.png")

# ============
# Figure 2: Room-by-room breakdown
# ============
fig, axes = plt.subplots(len(data), 1, figsize=(14, 3.5 * len(data)))
fig.suptitle('各直播间违规详情一览', fontsize=16, fontweight='bold', y=0.995)

for idx, (room, violations) in enumerate(rooms_sorted):
    ax = axes[idx] if len(data) > 1 else axes

    # Collect reasons
    reason_labels_local = []
    for v in violations:
        reason_labels_local.append(v['reason'])

    # Timeline view
    times = [v['time'] for v in violations]
    y_positions = list(range(len(violations)))
    reason_set = list(set(reason_labels_local))
    color_map = {r: colors[i % len(colors)] for i, r in enumerate(reason_set)}
    bar_colors = [color_map[r] for r in reason_labels_local]

    ax.barh(y_positions, [1]*len(violations), color=bar_colors, alpha=0.8, height=0.6)

    for i, v in enumerate(violations):
        action_marker = '⚠' if v['action'] == '预警' else ('✘' if v['action'] == '违规' else '✓')
        label = f"{action_marker} {v['time']} | {v['reason']} | {v['location']} | {v['penalty'][:30]}"
        ax.text(0.5, i, label, va='center', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

    ax.set_yticks([])
    ax.set_xlim(0, 1.5)
    ax.set_title(f'{room} ({len(violations)}次违规)', fontsize=13, fontweight='bold', loc='left')

    # Legend
    legend_patches = [plt.Rectangle((0,0),1,1, color=color_map[r], alpha=0.8) for r in reason_set]
    ax.legend(legend_patches, reason_set, loc='lower right', fontsize=8, ncol=len(reason_set))

plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.savefig(os.path.join(base, 'report_room_detail.png'), bbox_inches='tight', dpi=150)
plt.close()
print(" [图2] 各直播间详情图已保存: report_room_detail.png")

# ============
# Figure 3: Heatmap - Rooms vs Violation Types
# ============
fig, ax = plt.subplots(figsize=(10, 6))

reasons_all = sorted(set(v['reason'] for v in all_records))
rooms_all = [r[0] for r in rooms_sorted]

heatmap_data = np.zeros((len(rooms_all), len(reasons_all)))
for i, room in enumerate(rooms_all):
    for v in data[room]:
        j = reasons_all.index(v['reason'])
        heatmap_data[i][j] += 1

im = ax.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')

ax.set_xticks(range(len(reasons_all)))
ax.set_xticklabels(reasons_all, fontsize=10, rotation=30, ha='right')
ax.set_yticks(range(len(rooms_all)))
ax.set_yticklabels(rooms_all, fontsize=10)

for i in range(len(rooms_all)):
    for j in range(len(reasons_all)):
        val = int(heatmap_data[i, j])
        text_color = 'white' if val >= 3 else 'black'
        if val > 0:
            ax.text(j, i, str(val), ha='center', va='center', fontweight='bold',
                    color=text_color, fontsize=12)

ax.set_title('直播间 vs 违规原因 热力图', fontsize=14, fontweight='bold')
plt.colorbar(im, ax=ax, shrink=0.8, label='次数')
plt.tight_layout()
plt.savefig(os.path.join(base, 'report_heatmap.png'), bbox_inches='tight', dpi=150)
plt.close()
print(" [图3] 热力图已保存: report_heatmap.png")

# ============
# Figure 4: Action severity distribution by room (stacked bar)
# ============
fig, ax = plt.subplots(figsize=(10, 6))

action_types = ['预警', '违规', '已撤销']
room_action_data = {}
for room in rooms_all:
    room_action_data[room] = {a: 0 for a in action_types}
    for v in data[room]:
        room_action_data[room][v['action']] += 1

bottom = np.zeros(len(rooms_all))
action_colors = {'预警': '#4ECDC4', '违规': '#FF6B6B', '已撤销': '#DFE6E9'}

for action in action_types:
    vals = [room_action_data[r][action] for r in rooms_all]
    bars = ax.bar(range(len(rooms_all)), vals, bottom=bottom, color=action_colors[action],
                  alpha=0.85, label=action)
    for i, (b, v) in enumerate(zip(bottom, vals)):
        if v > 0:
            ax.text(i, b + v/2, str(v), ha='center', va='center', fontweight='bold', color='white' if action == '违规' else 'black')
    bottom += np.array(vals)

ax.set_xticks(range(len(rooms_all)))
ax.set_xticklabels(rooms_all, fontsize=9, rotation=30, ha='right')
ax.set_ylabel('次数', fontsize=12)
ax.set_title('各直播间处置严重程度分布', fontsize=14, fontweight='bold')
ax.legend(fontsize=10)

plt.tight_layout()
plt.savefig(os.path.join(base, 'report_severity.png'), bbox_inches='tight', dpi=150)
plt.close()
print(" [图4] 严重度分布图已保存: report_severity.png")

# ============
# Save structured JSON
# ============
output = {
    'report_time': '2026-06-10',
    'period': '2026年5月 - 2026年6月10日',
    'total_violations': total,
    'total_rooms': len(data),
    'summary': {
        'actions': dict(action_counter),
        'reasons': dict(reason_counter),
        'locations': dict(loc_counter),
        'monthly': dict(month_counter),
    },
    'rooms': room_stats,
    'key_findings': [
        '小米官方耳机直播间违规最多(9次)，占比45%，是重点整改对象',
        '售后服务不符是最突出的问题(12次，占60%)，主要表现为过度承诺质保、全国联保、线上线下均可维修等',
        '赠品活动信息与宣传不符次之(6次，占30%)，赠品未在商品详情页体现',
        '效果虚假出现1次(REDMI Watch防水夸大宣传)',
        '存在处罚升级趋势：从警告 → 冻结佣金5% → 冻结佣金15% → 关闭分享 → 提升保证金',
        '小米官方耳机直播间出现账号级别处罚(提升保证金至3000元)，表明累计违规导致账号风险评级升高',
        '截止6月10日，6月已有5次违规，新增「未使用平台福袋工具」违规类型，需高度关注',
    ],
    'recommendations': [
        '1. 立即规范直播间话术，不得在未确权的情况下承诺"全国联保""终生售后""一年质保"等',
        '2. 赠品信息需在商品详情页明确体现，直播间口播与详情页保持严格一致',
        '3. 建立直播话术审核机制，对每场直播的宣传文案进行提前审核',
        '4. 对小米官方耳机直播间进行专项整改，该直播间面临冻结佣金和保证金双重压力',
        '5. 关注6月违规趋势，避免触发平台更严厉处罚(如店铺冻结)',
    ]
}

with open(os.path.join(base, 'final_report.json'), 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(" [JSON] 完整报告已保存: final_report.json")
print("\n" + "=" * 70)
print("  报告生成完毕！共生成 4 张图表 + 1 个 JSON 数据文件")
print("=" * 70)
