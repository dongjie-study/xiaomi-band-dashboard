"""
竞对视频分析报告生成器
对比良米 vs 我司的视频广告投放数据，生成可视化HTML报告
自动发现 video_analysis/ 下所有 良米* / 我司* 目录并合并数据
"""
import pandas as pd
import numpy as np
import json
import base64
import os
import re
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent

def img_to_b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def sort_key(name):
    m = re.search(r'\((\d+)\)', name)
    if m:
        return (0, int(m.group(1)))
    return (1, 0)

def get_video_order(video_dir):
    videos = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
    return sorted(videos, key=sort_key)

def parse_number(val):
    if pd.isna(val):
        return 0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val = val.replace(',', '').replace('￥', '').replace('¥', '').replace('%', '')
        try:
            return float(val)
        except:
            return 0
    return float(val)

def discover_dirs():
    """Find all 良米* and 我司* directories under video_analysis/."""
    lm_dirs = sorted(
        [d for d in os.listdir(BASE) if d.startswith('良米') and os.path.isdir(BASE / d)],
        key=lambda d: d
    )
    ws_dirs = sorted(
        [d for d in os.listdir(BASE) if d.startswith('我司') and os.path.isdir(BASE / d)],
        key=lambda d: d
    )
    return lm_dirs, ws_dirs

def load_brand_data(brand_dirs):
    """Load Excel data and collect video file info from multiple directories."""
    all_dfs = []
    all_videos = []  # list of (dir_name, filename)

    for dir_name in brand_dirs:
        dir_path = BASE / dir_name
        xlsx_files = [f for f in os.listdir(dir_path)
                      if f.endswith('.xlsx') and not f.startswith('~$')]
        if xlsx_files:
            df = pd.read_excel(dir_path / xlsx_files[0])
            df.columns = df.columns.str.strip()
            # Tag with source directory for reference
            df['_source_dir'] = dir_name
            all_dfs.append(df)

        mp4s = get_video_order(dir_path)
        for mp4 in mp4s:
            all_videos.append((dir_name, mp4))

    combined_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    return combined_df, all_videos

def build_report():
    lm_dirs, ws_dirs = discover_dirs()
    lm_df, lm_videos = load_brand_data(lm_dirs)
    ws_df, ws_videos = load_brand_data(ws_dirs)

    if lm_df.empty and ws_df.empty:
        raise FileNotFoundError("No video data found. Place Excel files in 良米*/ or 我司*/ directories.")

    def build_cards(df, videos, prefix):
        """Build card list. videos is list of (dir_name, filename). frames/ lives inside each dir."""
        cards = []
        for idx, (dir_name, vname) in enumerate(videos):
            if idx >= len(df):
                break
            row = df.iloc[idx]
            frame_imgs = []
            poster_b64 = ''
            for pct in [0.25, 0.50, 0.75]:
                fpath = BASE / dir_name / "frames" / f"{idx}_{pct:.2f}.jpg"
                # Fall back to legacy frame location if not found in batch dir
                if not fpath.exists():
                    fpath = BASE / "frames" / prefix / f"{idx}_{pct:.2f}.jpg"
                if fpath.exists():
                    b64 = img_to_b64(fpath)
                    frame_imgs.append(b64)
                    if pct == 0.50:
                        poster_b64 = b64

            video_rel = f"video_analysis/{dir_name}/{vname}"

            cards.append({
                'index': idx,
                'filename': vname,
                'dir_name': dir_name,
                'name': str(row.iloc[0])[:80],
                'duration': str(row.iloc[3]) if len(row) > 3 else '',
                'frames': frame_imgs,
                'poster': poster_b64,
                'video_path': video_rel,
                'data': {str(df.columns[j]): parse_number(row.iloc[j]) for j in range(len(row))}
            })
        return cards

    lm_cards = build_cards(lm_df, lm_videos, 'liangmi')
    ws_cards = build_cards(ws_df, ws_videos, 'wosi')

    # ===== Compute summaries =====
    lm_s = {}
    ws_s = {}

    metric_defs = [
        ('总消耗', '整体消耗', 'sum'),
        ('平均支付ROI', '整体支付ROI', 'avg'),
        ('总成交金额', '整体成交金额', 'sum'),
        ('总成交订单数', '整体成交订单数', 'sum'),
        ('平均订单成本', '整体成交订单成本', 'avg'),
        ('总展现次数', '整体展现次数', 'sum'),
        ('总点击次数', '整体点击次数', 'sum'),
        ('平均点击率', '整体点击率', 'avg'),
        ('平均转化率', '整体转化率', 'avg'),
        ('平均千次展现费用', '整体千次展现费用', 'avg'),
        ('平均点击单价', '整体点击单价', 'avg'),
        ('总用户实际支付', '用户实际支付金额', 'sum'),
        ('总智能优惠券', '智能优惠券金额', 'sum'),
        ('总平台补贴', '电商平台补贴金额', 'sum'),
    ]

    for disp, col, agg in metric_defs:
        if col in lm_df.columns:
            vals = [parse_number(v) for v in lm_df[col]]
            lm_s[disp] = sum(vals) if agg == 'sum' else np.mean(vals)
        if col in ws_df.columns:
            vals = [parse_number(v) for v in ws_df[col]]
            ws_s[disp] = sum(vals) if agg == 'sum' else np.mean(vals)

    # ===== Chart data =====
    n = max(len(lm_cards), len(ws_cards))
    labels = [f'视频{i+1}' for i in range(n)]

    chart_metrics = [
        ('总消耗', '整体消耗'),
        ('平均支付ROI', '整体支付ROI'),
        ('总成交金额', '整体成交金额'),
        ('总成交订单数', '整体成交订单数'),
        ('平均订单成本', '整体成交订单成本'),
    ]

    charts = {}
    for disp, col in chart_metrics:
        charts[disp] = {
            'labels': labels,
            'lm': [parse_number(lm_df.iloc[i][col]) if i < len(lm_df) and col in lm_df.columns else 0 for i in range(n)],
            'ws': [parse_number(ws_df.iloc[i][col]) if i < len(ws_df) and col in ws_df.columns else 0 for i in range(n)],
        }

    for col in ['整体展现次数', '整体点击率', '整体转化率']:
        if col in lm_df.columns:
            charts[col] = {
                'labels': labels,
                'lm': [parse_number(lm_df.iloc[i][col]) if i < len(lm_df) else 0 for i in range(n)],
                'ws': None,
            }

    return render_html(lm_cards, ws_cards, lm_s, ws_s, charts, lm_df, ws_df)


def render_html(lm_cards, ws_cards, lm_s, ws_s, charts, lm_df, ws_df):
    now = datetime.now()

    def build_summary_table():
        rows = []
        for disp in lm_s:
            lm_v = lm_s.get(disp)
            ws_v = ws_s.get(disp)

            if any(kw in disp for kw in ['ROI', '率', '成本', '单价', '费用', '平均']):
                if '率' in disp:
                    lm_f = f'{lm_v:.2f}%' if lm_v else '-'
                    ws_f = f'{ws_v:.2f}%' if ws_v else '-'
                else:
                    lm_f = f'{lm_v:,.2f}' if lm_v else '-'
                    ws_f = f'{ws_v:,.2f}' if ws_v else '-'
            else:
                lm_f = f'{lm_v:,.0f}' if lm_v else '-'
                ws_f = f'{ws_v:,.0f}' if ws_v else '-'

            if ws_v and lm_v and ws_v != 0:
                diff_pct = (lm_v - ws_v) / abs(ws_v) * 100
                if '成本' in disp or '费用' in disp:
                    better = 'lm' if lm_v < ws_v else 'ws'
                else:
                    better = 'lm' if lm_v > ws_v else 'ws'
                arrow = '▲' if better == 'lm' else ''
                arrow_ws = '▲' if better == 'ws' else ''
                diff_text = f'{diff_pct:+.1f}%'
                diff_cls = 'good' if better == 'lm' else 'bad'
            else:
                diff_text = '-'
                diff_cls = ''
                arrow = ''
                arrow_ws = ''

            rows.append(f'''
            <tr>
                <td class="mname">{disp}</td>
                <td class="v-lm">{lm_f} {arrow}</td>
                <td class="v-ws">{ws_f} {arrow_ws}</td>
                <td class="diff {diff_cls}">{diff_text}</td>
            </tr>''')
        return '\n'.join(rows)

    vid_counter = [0]

    def video_card(card, side, label, color):
        if not card:
            return '<div class="vcard empty">无数据</div>'

        vid_id = f'v{vid_counter[0]}'
        vid_counter[0] += 1

        frames = ''.join(
            f'<div class="frm"><img src="data:image/jpeg;base64,{b64}" loading="lazy" onclick="document.getElementById(\'{vid_id}\').style.display=\'block\';this.closest(\'.frames\').style.display=\'none\';document.getElementById(\'{vid_id}\').play()"/></div>'
            for b64 in card['frames']
        )

        poster = f'poster="data:image/jpeg;base64,{card["poster"]}"' if card['poster'] else ''

        metrics = card['data']
        key_cols = ['整体消耗', '整体支付ROI', '整体成交金额', '整体成交订单数', '整体成交订单成本']
        mrows = ''
        for k in key_cols:
            if k in metrics:
                v = metrics[k]
                if 'ROI' in k:
                    mrows += f'<tr><td class="mk">{k}</td><td class="mv">{v:.2f}</td></tr>'
                elif '金额' in k or '消耗' in k:
                    mrows += f'<tr><td class="mk">{k}</td><td class="mv">{v:,.0f}</td></tr>'
                elif '成本' in k:
                    mrows += f'<tr><td class="mk">{k}</td><td class="mv">{v:,.2f}</td></tr>'
                else:
                    mrows += f'<tr><td class="mk">{k}</td><td class="mv">{v:,.0f}</td></tr>'

        batch_tag = f'<span style="font-size:.7em;color:#888;margin-left:4px">[{card.get("dir_name","")}]</span>' if card.get('dir_name') else ''

        return f'''
        <div class="vcard" style="border-left:3px solid {color}">
            <div class="vhead">
                <span class="vbadge" style="background:{color}">{label}#{card['index']+1}</span>
                <span class="vname" title="{card['name']}">{card['name'][:50]}{batch_tag}</span>
                <span class="vdur">{card['duration']}</span>
            </div>
            <div class="vbody">
                <div class="frames">{frames}</div>
                <video id="{vid_id}" class="vplayer" src="{card['video_path']}" {poster} controls preload="none" style="display:none">
                    您的浏览器不支持视频播放
                </video>
                <table class="mtab">{mrows}</table>
            </div>
        </div>'''

    paired = ''
    for i in range(max(len(lm_cards), len(ws_cards))):
        lm = lm_cards[i] if i < len(lm_cards) else None
        ws = ws_cards[i] if i < len(ws_cards) else None
        paired += f'''
        <div class="pair">
            <h3 class="ptitle">视频 #{i+1} 对比</h3>
            <div class="prow">
                {video_card(lm, 'lm', '良米', '#ff6b6b')}
                {video_card(ws, 'ws', '我司', '#4ecdc4')}
            </div>
        </div>'''

    chart_divs = ''
    chart_json = {}
    for i, (title, data) in enumerate(charts.items()):
        cid = f'c{i}'
        datasets = [{
            'label': '良米', 'data': data['lm'],
            'backgroundColor': 'rgba(255,107,107,0.7)', 'borderColor': '#ff6b6b', 'borderWidth': 1
        }]
        if data['ws'] is not None:
            datasets.append({
                'label': '我司', 'data': data['ws'],
                'backgroundColor': 'rgba(78,205,196,0.7)', 'borderColor': '#4ecdc4', 'borderWidth': 1
            })
        chart_json[cid] = {'labels': data['labels'], 'datasets': datasets}
        chart_divs += f'<div class="cbox"><h4>{title}</h4><canvas id="{cid}"></canvas></div>'

    def insight():
        lines = []
        lm_spend = lm_s.get('总消耗', 0)
        ws_spend = ws_s.get('总消耗', 0)
        lm_roi = lm_s.get('平均支付ROI', 0)
        ws_roi = ws_s.get('平均支付ROI', 0)
        lm_amt = lm_s.get('总成交金额', 0)
        ws_amt = ws_s.get('总成交金额', 0)
        lm_orders = lm_s.get('总成交订单数', 0)
        ws_orders = ws_s.get('总成交订单数', 0)
        lm_cpa = lm_s.get('平均订单成本', 0)
        ws_cpa = ws_s.get('平均订单成本', 0)
        lm_ctr = lm_s.get('平均点击率', 0)
        lm_cvr = lm_s.get('平均转化率', 0)

        if ws_spend > 0:
            spend_ratio = lm_spend / ws_spend
            lines.append(f'良米投放总消耗是<span class="hl">{lm_spend:,.0f}元</span>，我司为<span class="hl">{ws_spend:,.0f}元</span>，良米投放规模约为我司的<span class="hl">{spend_ratio:.1f}倍</span>。')

        if ws_roi > 0:
            roi_diff = (lm_roi - ws_roi) / ws_roi * 100
            lines.append(f'良米平均支付ROI为<span class="hl">{lm_roi:.2f}</span>，我司为<span class="hl">{ws_roi:.2f}</span>，良米ROI高出<span class="hl">{roi_diff:+.1f}%</span>。')

        if ws_amt > 0:
            amt_ratio = lm_amt / ws_amt
            lines.append(f'良米总成交金额<span class="hl">{lm_amt:,.0f}元</span>（{lm_orders:,.0f}单），我司<span class="hl">{ws_amt:,.0f}元</span>（{ws_orders:,.0f}单），成交规模倍数约<span class="hl">{amt_ratio:.1f}倍</span>。')

        if ws_cpa > 0 and lm_cpa > 0:
            lines.append(f'平均订单成本：良米<span class="hl">{lm_cpa:,.2f}元</span> vs 我司<span class="hl">{ws_cpa:,.2f}元</span>，{"良米" if lm_cpa < ws_cpa else "我司"}成本更低。')

        if lm_ctr > 0:
            lines.append(f'良米平均点击率<span class="hl">{lm_ctr:.2f}%</span>，平均转化率<span class="hl">{lm_cvr:.2f}%</span>。')

        if len(lm_cards) > 0:
            lm_best = max(lm_cards, key=lambda c: c['data'].get('整体支付ROI', 0))
            lm_worst = min(lm_cards, key=lambda c: c['data'].get('整体支付ROI', 0))
            lines.append(f'良米ROI最高视频：<span class="hl">#{lm_best["index"]+1} {lm_best["name"][:30]}</span>（ROI={lm_best["data"].get("整体支付ROI",0):.2f}），最低：#{lm_worst["index"]+1}（ROI={lm_worst["data"].get("整体支付ROI",0):.2f}）。')

        if len(ws_cards) > 0:
            ws_best = max(ws_cards, key=lambda c: c['data'].get('整体支付ROI', 0))
            ws_worst = min(ws_cards, key=lambda c: c['data'].get('整体支付ROI', 0))
            lines.append(f'我司ROI最高视频：<span class="hl">#{ws_best["index"]+1} {ws_best["name"][:30]}</span>（ROI={ws_best["data"].get("整体支付ROI",0):.2f}），最低：#{ws_worst["index"]+1}（ROI={ws_worst["data"].get("整体支付ROI",0):.2f}）。')

        return '\n'.join(f'<li>{l}</li>' for l in lines)

    # Source dirs summary
    lm_dir_list = sorted(set(c.get('dir_name', '') for c in lm_cards if c.get('dir_name')))
    ws_dir_list = sorted(set(c.get('dir_name', '') for c in ws_cards if c.get('dir_name')))
    dir_info = ''
    if len(lm_dir_list) > 1 or len(ws_dir_list) > 1:
        dir_info = f'<div class="sub" style="margin-top:4px">数据批次: 良米 [{", ".join(lm_dir_list)}] | 我司 [{", ".join(ws_dir_list)}]</div>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>竞对视频分析 — 良米 vs 我司</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Microsoft YaHei',sans-serif;background:#f0f2f5;color:#333;line-height:1.6}}
.container{{max-width:1500px;margin:0 auto;padding:20px}}

.header{{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);color:#fff;padding:36px 40px;border-radius:16px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center}}
.header h1{{font-size:1.8em;font-weight:700}}
.header .sub{{opacity:.7;font-size:.9em}}
.header .kpis{{display:flex;gap:28px;text-align:center}}
.header .kpi .kv{{font-size:1.6em;font-weight:700}}
.header .kpi .kl{{font-size:.75em;opacity:.7}}
.header .kpi.lm .kv{{color:#ff6b6b}}
.header .kpi.ws .kv{{color:#4ecdc4}}

.section-title{{font-size:1.2em;color:#555;margin:24px 0 16px;padding-left:12px;border-left:4px solid #667eea}}

.stable{{width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:24px}}
.stable table{{width:100%;border-collapse:collapse}}
.stable th{{background:#f8f9fa;padding:12px 16px;text-align:left;font-weight:600;color:#666;font-size:.85em}}
.stable th:nth-child(2),.stable th:nth-child(3){{text-align:right}}
.stable th:nth-child(4){{text-align:center}}
.stable td{{padding:10px 16px;border-bottom:1px solid #f0f0f0}}
.stable .mname{{font-weight:600;color:#444}}
.stable .v-lm{{text-align:right;font-weight:600;color:#ff6b6b;font-family:'SF Mono',Consolas,monospace}}
.stable .v-ws{{text-align:right;font-weight:600;color:#4ecdc4;font-family:'SF Mono',Consolas,monospace}}
.stable .diff{{text-align:center;font-size:.85em}}
.stable .diff.good{{color:#27ae60}}
.stable .diff.bad{{color:#e74c3c}}

.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:16px;margin-bottom:24px}}
.cbox{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.cbox h4{{margin-bottom:12px;color:#555;font-size:.95em}}
.cbox canvas{{max-height:280px}}

.insights{{background:#fff;border-radius:12px;padding:24px 28px;margin-bottom:24px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.insights h2{{margin-bottom:16px;font-size:1.1em}}
.insights ul{{list-style:none;padding:0}}
.insights li{{padding:8px 0;border-bottom:1px solid #f5f5f5;line-height:1.7}}
.insights .hl{{color:#667eea;font-weight:600}}

.pair{{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.ptitle{{font-size:1em;color:#666;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #eee}}
.prow{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}

.vcard{{border-radius:8px;overflow:hidden;border:1px solid #eee}}
.vcard.empty{{padding:60px 20px;text-align:center;color:#bbb}}
.vhead{{padding:8px 14px;background:#fafafa;display:flex;align-items:center;gap:10px;border-bottom:1px solid #eee}}
.vbadge{{padding:2px 10px;border-radius:10px;font-size:.75em;color:#fff;font-weight:600;white-space:nowrap}}
.vname{{flex:1;font-size:.85em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.vdur{{font-size:.75em;color:#aaa}}
.vbody{{padding:10px 14px}}
.frames{{display:flex;gap:6px;margin-bottom:10px;overflow-x:auto}}
.frm{{flex-shrink:0;width:180px;border-radius:4px;overflow:hidden;border:1px solid #eee;cursor:pointer;position:relative}}
.frm:hover{{border-color:#667eea;box-shadow:0 2px 8px rgba(102,126,234,.3)}}
.frm:hover::after{{content:'▶ 播放';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,.7);color:#fff;padding:4px 12px;border-radius:4px;font-size:12px;pointer-events:none}}
.frm img{{width:100%;display:block}}
.vplayer{{width:100%;max-height:360px;border-radius:4px;margin-bottom:10px;background:#000}}
.mtab{{width:100%;border-collapse:collapse;font-size:.8em}}
.mtab td{{padding:3px 8px;border-bottom:1px solid #f8f8f8}}
.mtab .mk{{color:#999}}
.mtab .mv{{text-align:right;font-weight:600;font-family:'SF Mono',Consolas,monospace}}

.footer{{text-align:center;padding:30px;color:#bbb;font-size:.8em}}
</style>
</head>
<body style="display:none">
<script>
(function(){{
var K='mi_band_auth_v1';
if(localStorage.getItem(K)){{
document.body.style.display='';
return;
}}
document.body.innerHTML='<div style="display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:-apple-system,BlinkMacSystemFont,\'Microsoft YaHei\',sans-serif;background:#f0f2f5"><div style="background:#fff;border-radius:16px;padding:48px 40px;box-shadow:0 4px 24px rgba(0,0,0,.08);width:380px;max-width:90vw"><div style="text-align:center;font-size:2.4em;margin-bottom:8px">🔐</div><h1 style="font-size:1.4em;color:#1a1a2e;margin-bottom:8px;text-align:center">小米手环竞对分析平台</h1><p style="color:#888;font-size:.85em;text-align:center;margin-bottom:32px">请登录后查看数据</p><label style="display:block;font-size:.85em;color:#555;margin-bottom:6px">用户名</label><input type="text" id="lu" style="width:100%;padding:12px 16px;border:1px solid #ddd;border-radius:8px;font-size:.95em;margin-bottom:20px;outline:none" placeholder="请输入用户名" autofocus><label style="display:block;font-size:.85em;color:#555;margin-bottom:6px">密码</label><input type="password" id="lp" style="width:100%;padding:12px 16px;border:1px solid #ddd;border-radius:8px;font-size:.95em;margin-bottom:20px;outline:none" placeholder="请输入密码" onkeydown="if(event.key===\'Enter\')document.getElementById(\'lb\').click()"><p id="le" style="color:#e74c3c;font-size:.8em;text-align:center;margin-bottom:12px;display:none">用户名或密码错误</p><button id="lb" style="width:100%;padding:12px;background:#4ECDC4;color:#fff;border:none;border-radius:8px;font-size:1em;font-weight:600;cursor:pointer" onclick="var u=document.getElementById(\'lu\').value;var p=document.getElementById(\'lp\').value;if(u===\'zhangdongjie\'&&p===\'zdjzdj\'){{localStorage.setItem(\'mi_band_auth_v1\',\'1\');location.reload()}}else{{document.getElementById(\'le\').style.display=\'block\'}}">登 录</button></div></div>';
document.body.style.display='';
}})();
</script>
<div class="container">

<div class="header">
    <div>
        <h1>竞对视频广告分析报告</h1>
        <div class="sub">良米 vs 我司 · 巨量广告投放数据 · {now.strftime('%Y年%m月%d日')}{dir_info}</div>
    </div>
    <div class="kpis">
        <div class="kpi lm">
            <div class="kv">{lm_s.get('平均支付ROI', 0):.2f}</div>
            <div class="kl">良米平均ROI</div>
        </div>
        <div class="kpi ws">
            <div class="kv">{ws_s.get('平均支付ROI', 0):.2f}</div>
            <div class="kl">我司平均ROI</div>
        </div>
        <div class="kpi">
            <div class="kv">{lm_s.get('总消耗', 0) + ws_s.get('总消耗', 0):,.0f}</div>
            <div class="kl">双方总消耗(元)</div>
        </div>
    </div>
</div>

<h2 class="section-title">投放数据总览</h2>
<div class="stable">
    <table>
        <thead>
            <tr><th>指标</th><th style="text-align:right">良米</th><th style="text-align:right">我司</th><th style="text-align:center">差异</th></tr>
        </thead>
        <tbody>
            {build_summary_table()}
        </tbody>
    </table>
</div>

<div class="insights">
    <h2>分析洞察</h2>
    <ul>{insight()}</ul>
</div>

<h2 class="section-title">分视频指标对比</h2>
<div class="charts">{chart_divs}</div>

<h2 class="section-title">逐视频详细对比</h2>
{paired}

<div class="footer">报告由系统自动生成 · 数据来源：巨量广告投放平台 · {now.strftime('%Y-%m-%d %H:%M')}</div>

</div>

<script>
const chartData = {json.dumps(chart_json, ensure_ascii=False)};
Object.entries(chartData).forEach(function(e) {{
    var id = e[0], data = e[1];
    var ctx = document.getElementById(id);
    if (!ctx) return;
    new Chart(ctx, {{
        type: 'bar',
        data: data,
        options: {{
            responsive: true,
            plugins: {{ legend: {{ position: 'top' }} }},
            scales: {{ y: {{ beginAtZero: true }} }}
        }}
    }});
}});
</script>
</body>
</html>'''

    return html


if __name__ == '__main__':
    html = build_report()
    out_path = BASE.parent / '竞对视频分析报告.html'
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Report saved: {out_path}")
    print(f"Size: {len(html):,} bytes")
