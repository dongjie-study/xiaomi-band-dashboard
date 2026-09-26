#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建腾讯云 CloudBase 云函数所需的数据资产。

作用：把项目里已有的只读数据文件复制/合并进云函数目录，供云端小管家查询。
  1) 直接复制：history / band11_history / b10pro_history / daily_summary / anchor_records
  2) 合并压缩：sales_analysis/hourly/*.json  ->  hourly.json.gz（11MB 全量压到约 1.5MB）

设计原则：纯只读 + 只写 cloudbase-assistant/ 目录，绝不改动任何现有文件与流程。

用法：
  python tools/build_cloudbase_assets.py          # 生成数据资产
  python tools/build_cloudbase_assets.py --zip    # 生成数据资产 + 打包上传用 zip
"""
import gzip
import io
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FN_DIR = os.path.join(ROOT, 'cloudbase-assistant', 'cloudfunctions', 'chat')
ASSETS = os.path.join(FN_DIR, 'assets')

COPY_FILES = {
    'history.json': 'sales_analysis/history.json',
    'band11_history.json': 'sales_analysis/band11_history.json',
    'b10pro_history.json': 'sales_analysis/b10pro_history.json',
    'daily_summary.json': 'sales_analysis/daily_summary.json',
    'anchor_records.json': '主播业绩/anchor_records.json',
}
HOURLY_DIR = os.path.join(ROOT, 'sales_analysis', 'hourly')


def human(n):
    for unit in ('B', 'KB', 'MB'):
        if n < 1024:
            return f'{n:.0f}{unit}'
        n /= 1024
    return f'{n:.1f}GB'


def main():
    os.makedirs(ASSETS, exist_ok=True)
    total = 0

    # 1) 直接复制小文件
    for dst_name, rel in COPY_FILES.items():
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            print(f'[跳过] 源文件不存在：{rel}')
            continue
        dst = os.path.join(ASSETS, dst_name)
        shutil.copyfile(src, dst)
        size = os.path.getsize(dst)
        total += size
        print(f'[复制] {rel}  ->  assets/{dst_name}  ({human(size)})')

    # 2) 合并压缩 hourly
    if os.path.isdir(HOURLY_DIR):
        merged = {}
        for fn in sorted(os.listdir(HOURLY_DIR)):
            if not fn.endswith('.json'):
                continue
            date = fn[:-5]
            with open(os.path.join(HOURLY_DIR, fn), encoding='utf-8') as f:
                try:
                    merged[date] = json.load(f)
                except Exception as e:  # 单个文件坏了不影响整体
                    print(f'[警告] {fn} 解析失败，已跳过：{e}')
        raw = json.dumps(merged, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        gz_path = os.path.join(ASSETS, 'hourly.json.gz')
        with gzip.open(gz_path, 'wb', compresslevel=9) as f:
            f.write(raw)
        size = os.path.getsize(gz_path)
        total += size
        print(f'[压缩] sales_analysis/hourly/*.json  {len(merged)} 天  '
              f'{human(len(raw))} -> assets/hourly.json.gz  ({human(size)})')

    # 3) 可选：打包成控制台上传用的 zip
    if '--zip' in sys.argv:
        zip_path = os.path.join(ROOT, 'cloudbase-assistant', 'chat-function.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(os.path.join(FN_DIR, 'index.js'), 'index.js')
            z.write(os.path.join(FN_DIR, 'package.json'), 'package.json')
            for fn in sorted(os.listdir(ASSETS)):
                z.write(os.path.join(ASSETS, fn), f'assets/{fn}')
        print(f'[打包] {zip_path}  ({human(os.path.getsize(zip_path))})')

    print(f'\n完成：数据资产共 {human(total)}，位置 cloudbase-assistant/cloudfunctions/chat/assets/')
    print('提示：每次订单/业绩数据更新后，重新跑一次本脚本再部署，云端数据即最新。')


if __name__ == '__main__':
    main()
