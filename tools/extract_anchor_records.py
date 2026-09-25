# -*- coding: utf-8 -*-
"""
主播业绩数据抽取器 —— 从 主播业绩/业绩demo.html 的 DAILY_RECORDS 抽出独立 JSON。

为什么：数据小管家（assistant-server/）需要按日期查询主播 GSV，
但数据嵌在 236KB 的 HTML 里，运行时解析又慢又脆。这里抽成轻量 JSON，
Worker 直接从 GitHub raw 拉这个 JSON。

铁律遵守：**只读** 业绩demo.html，一个字节都不改它。
业绩流程入库后（业绩demo.html 有新日期时）跑一次本脚本刷新 JSON 并提交。

用法：
    PYTHONUTF8=1 python tools/extract_anchor_records.py
    PYTHONUTF8=1 python tools/extract_anchor_records.py --check   # 只校验 JSON 与 HTML 同步
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(ROOT, '主播业绩', '业绩demo.html')
OUT_FILE = os.path.join(ROOT, '主播业绩', 'anchor_records.json')

# 业绩demo.html 里直播间名 → roomId（与 docs/03 一致）
ROOM_MAP = {
    '小米数码旗舰店': 'room_xiaomi_digital',
    '小米官方手环直播间': 'room_xiaomi_band',
    '小米官方手表': 'room_xiaomi_watch',
    '小米官旗手表直播间': 'room_xiaomi_watch_flagship',
    '小米官方耳机直播间': 'room_xiaomi_earphone',
    '小米AI眼镜直播间': 'room_xiaomi_glasses',
    '小米智能设备旗舰店直播间': 'room_xiaomi_smart_device',
    '小米手环官旗直播间': 'room_xiaomi_band_flagship',
    '手环预约期业绩': 'room_xiaomi_band_preorder',
}

RE_RECORDS = re.compile(r'const DAILY_RECORDS = (\{[\s\S]*?\n\s*\});')
RE_TRAILING_SEMI = re.compile(r';\s*$')


def extract():
    """从 HTML 抽出 DAILY_RECORDS → {date: [records]}，失败抛异常不落盘。"""
    with open(HTML_FILE, encoding='utf-8') as f:
        html = f.read()
    m = RE_RECORDS.search(html)
    if not m:
        raise SystemExit('✗ 在 业绩demo.html 里找不到 DAILY_RECORDS 区块')
    block = RE_TRAILING_SEMI.sub('', m.group(1))
    # HTML 里是 JS 对象字面量（键带单引号），基本是合法 JSON 语法，
    # 但保险起见先试 json，失败再退回 node 解析
    try:
        data = json.loads(block)
    except json.JSONDecodeError:
        data = _parse_with_node(block)

    # 结构校验：键是 YYYY-MM-DD，值是 {roomId, shift, anchor, sales} 数组
    days = sorted(data)
    for d in days:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(d)):
            raise SystemExit(f'✗ 非法日期键 {d!r}，HTML 结构可能变了')
        for rec in data[d]:
            for k in ('roomId', 'shift', 'anchor', 'sales'):
                if k not in rec:
                    raise SystemExit(f'✗ {d} 的记录缺字段 {k}：{rec}')
    return data, days


def _parse_with_node(block):
    """json 解析失败时用 node eval（HTML 手工维护过可能有 JS 特有语法）。"""
    import subprocess
    import tempfile
    code = (
        'const fs=require("fs");'
        f'const o=eval({json.dumps("(" + block + ")")});'
        'process.stdout.write(JSON.stringify(o))'
    )
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as t:
        t.write(code)
        tmp = t.name
    try:
        out = subprocess.run(['node', tmp], capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            raise SystemExit(f'✗ node 解析失败：{out.stderr[:500]}')
        return json.loads(out.stdout)
    finally:
        os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只校验 JSON 已与 HTML 同步')
    args = ap.parse_args()

    data, days = extract()
    total = sum(len(v) for v in data.values())

    if args.check:
        if not os.path.exists(OUT_FILE):
            print(f'✗ {OUT_FILE} 不存在，需要先跑一次本脚本')
            return 1
        with open(OUT_FILE, encoding='utf-8') as f:
            old = json.load(f)
        if old.get('records') == data:
            print(f'✓ 已同步（{len(days)} 天 / {total} 条，最新 {days[-1]}）')
            return 0
        print(f'✗ JSON 落后于 HTML，请重跑：{os.path.relpath(OUT_FILE, ROOT)}')
        return 1

    out = {
        'schema_version': 1,
        'updated_at': days[-1],
        '_note': '由 tools/extract_anchor_records.py 从 业绩demo.html 的 DAILY_RECORDS 抽取（只读）。'
                 '业绩demo.html 更新后重跑该脚本刷新本文件。主播 GSV 口径未扣退款。',
        'room_names': {v: k for k, v in ROOM_MAP.items()},
        'records': data,
    }
    tmp = OUT_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False)
    os.replace(tmp, OUT_FILE)
    print(f'✓ 已生成 {os.path.relpath(OUT_FILE, ROOT)}：{len(days)} 天 / {total} 条记录，最新 {days[-1]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
