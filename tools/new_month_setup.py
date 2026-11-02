# -*- coding: utf-8 -*-
"""新月一键准备（换月自动化）。

用法：
    python tools/new_month_setup.py 2026-12            # 真正执行
    python tools/new_month_setup.py 2026-12 --dry-run  # 只打印计划，不写文件

它会做（顺序执行，任何一步失败即中止）：
  1. 找到"当前最新月份"的生成器，复制成新月份的生成器，并做全部文案/日期替换
     （2026-MM、MM月、中文月名、English/english、周标签 W1..W5 日期区间）
  2. 给**所有** generate_<月份>_summary.py 的 nav-bar 补成"全部月份 + 当前月 active"（幂等）
  3. modules.json：sales / monthlySummary 各追加新月份条目，NEW 徽标挪到新月份
  4. workbench.html：modules.json 的缓存版本号 bump（否则浏览器还读旧配置）
  5. 运行新月份生成器 → 生成 月度总结/<中文月>销量分析.html
  6. 补注入右下角小管家（生成器整份重写会冲掉那行）
  7. 自检：JSON 合法、六个（及以上）月页 nav 含全部月份、小管家在、页面文件非空
  8. 打印需要人工补的文案（双11/节点类叙述）与提交命令

设计原则：能自动的自动化，**涉及时效性叙述的几句话只打印提示**，不硬编。
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
DOC_MONTH = os.path.join(ROOT, '月度总结')

EN = ['january', 'february', 'march', 'april', 'may', 'june',
      'july', 'august', 'september', 'october', 'november', 'december']
CN = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def month_days(year, m):
    if m == 2:
        leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
        return 29 if leap else 28
    return DAYS[m - 1]


def week_labels(year, m):
    """当月 W1..W5 日期区间标签：与生成器里的 week_labels 保持同一口径。"""
    n = month_days(year, m)
    out = []
    for idx, (start, end) in enumerate([(1, 7), (8, 14), (15, 21), (22, 28), (29, n)], start=1):
        if start > n:
            break
        end = min(end, n)
        out.append(f"'{year}-{m:02d}-{start:02d}'")  # 占位，实际标签在下面拼
    labels = {}
    for idx, (start, end) in enumerate([(1, 7), (8, 14), (15, 21), (22, 28), (29, n)], start=1):
        if start > n:
            break
        end = min(end, n)
        labels[f'W{idx}'] = f'W{idx} ({m}/{start}-{m}/{end})'
    return labels


def longest_month_generator():
    """返回 (month:int, path:str)，按文件名里的英文月份取最大的那个。"""
    best = None
    for name in os.listdir(TOOLS):
        m = re.fullmatch(r'generate_([a-z]+)_summary\.py', name)
        if not m or m.group(1) not in EN:
            continue
        month = EN.index(m.group(1)) + 1
        path = os.path.join(TOOLS, name)
        if best is None or month > best[0]:
            best = (month, path)
    return best


def gen_path(month):
    return os.path.join(TOOLS, f'generate_{EN[month - 1]}_summary.py')


def read_text(path):
    with io.open(path, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write_text(path, text):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


# ---------------------------------------------------------------- 1. 新生成器
def build_generator(year, new_month, dry):
    prev = longest_month_generator()
    if not prev:
        raise SystemExit('找不到任何 generate_<月份>_summary.py，无法复制模板')
    prev_month, prev_path = prev
    if prev_month >= new_month:
        # 已有更"新"或同月的生成器：说明该月已建过
        existing = [p for p in (gen_path(m) for m in range(new_month, 13)) if os.path.exists(p)]
        if os.path.exists(gen_path(new_month)):
            print(f'[跳过] {os.path.basename(gen_path(new_month))} 已存在，不覆盖')
            return None
        raise SystemExit(f'模板月 {prev_month} 不小于目标月 {new_month}，请检查')

    src = read_text(prev_path)
    text = src

    # (a) 周标签：整块替换成新月份的区间
    labels = week_labels(year, new_month)
    body = ', '.join(f"'{k}': '{v}'" for k, v in labels.items())
    new_block = ('week_labels = {\n        ' + body.replace("', '", "',\n        '") + '\n    }')
    text, n1 = re.subn(r'week_labels = \{[^}]*\}', new_block, text, count=1)

    # (b) 日期前缀 2026-MM → 2026-NN（先置换月前缀，避免再被月名替换波及）
    text = text.replace(f'{year}-{prev_month:02d}', f'{year}-{new_month:02d}')

    # (c) 月名：中文 / 阿拉伯数字 / 英文
    text = text.replace(f'{CN[prev_month - 1]}月', f'{CN[new_month - 1]}月')
    text = text.replace(f'{prev_month}月', f'{new_month}月')
    text = text.replace(EN[prev_month - 1].capitalize(), EN[new_month - 1].capitalize())
    text = text.replace(EN[prev_month - 1], EN[new_month - 1])
    # (d) 函数名/变量名（load_october_data → load_november_data 之类由上面英文替换覆盖）

    # 断言：不得残留上一月的日期前缀
    if f'{year}-{prev_month:02d}' in text:
        raise SystemExit('替换后仍残留上一月的日期前缀，请人工检查')

    target = gen_path(new_month)
    print(f'[1] 生成器：{os.path.basename(prev_path)} → {os.path.basename(target)}'
          + (f'（周标签 {n1} 块）' if n1 else ''))
    if not dry:
        write_text(target, text)
    return target


# ---------------------------------------------------------------- 2. nav 统一
MONTH_LINE = re.compile(
    r'^(\s*)<a href="(?:#|(?:[一二三四五六七八九十]+月)销量分析\.html)"'
    r' class="nav-btn(?: active)?">\d+月销量分析</a>\s*$'
)


def patch_nav(months, dry):
    """把每个生成器的 nav 月份块统一成 months 列表，当前页对应月份 active。"""
    changed = 0
    for m in months:
        path = gen_path(m)
        if not os.path.exists(path):
            continue
        text = read_text(path)
        lines = text.split('\n')
        out, i, blocks = [], 0, 0
        while i < len(lines):
            mm = MONTH_LINE.match(lines[i])
            if mm:
                indent = mm.group(1)
                j = i
                while j < len(lines) and MONTH_LINE.match(lines[j]):
                    j += 1
                for mm2 in months:
                    if mm2 == m:
                        out.append(f'{indent}<a href="#" class="nav-btn active">{mm2}月销量分析</a>')
                    else:
                        out.append(f'{indent}<a href="{CN[mm2 - 1]}月销量分析.html" class="nav-btn">{mm2}月销量分析</a>')
                blocks += 1
                i = j
                continue
            out.append(lines[i])
            i += 1
        new_text = '\n'.join(out)
        if new_text != text:
            changed += 1
            print(f'[2] nav：{os.path.basename(path)}（{blocks} 处月份块）')
            if not dry:
                write_text(path, new_text)
    print(f'[2] nav 合计更新 {changed} 个生成器')


# ---------------------------------------------------------------- 3. modules.json
def patch_modules(year, new_month, dry):
    path = os.path.join(ROOT, 'modules.json')
    text = read_text(path)
    mm = f'{year}-{new_month:02d}'
    title = f'{CN[new_month - 1]}月'
    eng = EN[new_month - 1].capitalize()

    def insert_last(sub_key, new_line):
        nonlocal text
        k = text.find(f'"id": "{sub_key}"')
        if k < 0:
            print(f'[3] ⚠ modules.json 里找不到 {sub_key}，跳过')
            return
        sm = text.find('"subModules": [', k)
        end = text.find(']', sm)
        block = text[sm:end]
        tail_ws = block[len(block.rstrip()):] or '\n            '
        block = block.rstrip()
        if new_line.strip() in block:       # 幂等：已经有这个月就不重复插
            return
        block = re.sub(r',\s*"badge": "NEW"', '', block)   # 旧月的 NEW 徽标挪走
        text = text[:sm] + block + ',\n' + new_line + tail_ws + text[end:]

    insert_last('sales',
                f'            {{ "id": "sales{eng}", "title": "{title}", "monthKey": "{mm}", "badge": "NEW" }}')
    insert_last('monthlySummary',
                f'            {{ "id": "summary{eng}", "title": "{title}", '
                f'"url": "月度总结/{title}销量分析.html", "badge": "NEW" }}')

    try:
        json.loads(text)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f'modules.json 改完后 JSON 不合法：{e}')
    print(f'[3] modules.json：sales{eng} / summary{eng}（{title}）已追加，NEW 徽标挪到本月')
    if not dry:
        write_text(path, text)


# ---------------------------------------------------------------- 4. 缓存版本
def bump_cache(dry):
    path = os.path.join(ROOT, 'workbench.html')
    text = read_text(path)
    today = dt.date.today().strftime('%Y%m%d')
    new, n = re.subn(r"fetch\('modules\.json\?v=([^']*)'\)", f"fetch('modules.json?v={today}b')", text, count=1)
    if n == 0:
        print('[4] ⚠ workbench.html 里没找到 modules.json?v=，跳过')
        return
    print(f'[4] workbench.html：modules.json 缓存版本 → v={today}b')
    if not dry:
        write_text(path, new)


# ---------------------------------------------------------------- 5-7. 生成 + 自检
def run(cmd):
    print(f'    $ {cmd}')
    return subprocess.run(cmd, cwd=ROOT, shell=True, capture_output=True, text=True, encoding='utf-8')


def generate_and_verify(year, new_month, dry):
    cn = CN[new_month - 1]
    page = os.path.join(DOC_MONTH, f'{cn}月销量分析.html')
    py = sys.executable
    months = [mm for mm in range(1, 13) if os.path.exists(gen_path(mm))]
    if dry:
        print(f'[5] （dry-run）将依次重跑 {len(months)} 个生成器：'
              + '、'.join(os.path.basename(gen_path(mm)) for mm in months))
        print('[6] （dry-run）将运行 tools/inject_widget.py')
        print('[7] （dry-run）将自检 nav / 小管家 / JSON')
        return

    # 关键：nav 改的是"生成器"，已有页面必须重跑一遍才会带上新月份链接
    print(f'[5] 重跑全部生成器（{len(months)} 个，让历史页也带上新月份导航）')
    for mm in months:
        name = os.path.basename(gen_path(mm))
        r = run(f'"{py}" "tools/{name}"')
        last = [l for l in (r.stdout or '').strip().split('\n') if l.strip()]
        tag = 'OK ' if r.returncode == 0 else 'FAIL'
        print(f'    {tag} {name}' + (f'  ← {last[1].strip()}' if len(last) > 1 and r.returncode == 0 else ''))
        if r.returncode != 0:
            raise SystemExit(f'{name} 执行失败：\n' + (r.stderr or '')[-800:])

    print('[6] 补注入小管家')
    r = run(f'"{py}" tools/inject_widget.py')
    print('    ' + (r.stdout or '').strip().replace('\n', '\n    ')[-300:])

    print('[7] 自检')
    cfg = json.loads(read_text(os.path.join(ROOT, 'modules.json')))
    subs = {}
    for sec in cfg['sections']:
        for mod in sec['modules']:
            if mod.get('subModules'):
                subs[mod['id']] = [s.get('title') for s in mod['subModules']]
    print('    modules.sales =', subs.get('sales'))
    print('    modules.monthlySummary =', subs.get('monthlySummary'))

    months = [m for m in range(1, new_month + 1) if os.path.exists(gen_path(m))
              and os.path.exists(os.path.join(DOC_MONTH, f'{CN[m - 1]}月销量分析.html'))]
    bad = []
    for m in months:
        p = os.path.join(DOC_MONTH, f'{CN[m - 1]}月销量分析.html')
        t = read_text(p)
        if 'assistant-widget.js' not in t:
            bad.append(f'{CN[m - 1]}月：缺小管家')
        if m != new_month and f'{cn}月销量分析.html' not in t:
            bad.append(f'{CN[m - 1]}月：nav 缺 {cn}月链接')
    if not os.path.exists(page):
        bad.append(f'{cn}月页未生成')
    if bad:
        raise SystemExit('自检不通过：\n  - ' + '\n  - '.join(bad))
    print(f'    ✔ {len(months)} 个月页 nav 完整、小管家在位、{cn}月页已生成')


def print_manual_todo(year, new_month):
    cn = CN[new_month - 1]
    path = gen_path(new_month)
    tips = []
    if os.path.exists(path):
        for line_no, line in enumerate(read_text(path).split('\n'), start=1):
            s = line.strip()
            if '{{' in s or '}}' in s or s.startswith(('#', '/*', '* ', '//')):
                continue
            if any(k in s for k in ('双11', '大促', '618', '年终', '年货', '战略', '核心洞察', '重点方向')):
                if any('\u4e00' <= ch <= '\u9fff' for ch in s):
                    tips.append(f'{line_no}: {s[:110]}')
    print('\n📝 需要人工看一眼的叙述（换月后时令/节点可能过期，改生成器再重跑）：')
    if tips:
        for t in tips[:12]:
            print('   ' + t)
        print(f'   ↑ 共 {len(tips)} 处；把上个月的节点/对比基准改成新月份的说法，再重跑该月份生成器。')
    else:
        print('   （无）')
    print(f'   建议顺带核对：{cn}月战略方向 / 核心 KPI 目标 / 改进建议里的「与上月同期」口径')


def main():
    ap = argparse.ArgumentParser(description='新月一键准备（换月自动化）')
    ap.add_argument('month', help='目标月份，形如 2026-12')
    ap.add_argument('--dry-run', action='store_true', help='只打印计划，不写任何文件')
    args = ap.parse_args()

    m = re.fullmatch(r'(\d{4})-(\d{2})', args.month.strip())
    if not m:
        raise SystemExit('月份格式应为 YYYY-MM，例如 2026-12')
    year, new_month = int(m.group(1)), int(m.group(2))
    if not 1 <= new_month <= 12:
        raise SystemExit('月份需在 01~12')
    print(f'=== 准备 {year}-{new_month:02d}（{CN[new_month - 1]}月）{"（dry-run）" if args.dry_run else ""} ===')

    target = build_generator(year, new_month, args.dry_run)
    months = [mm for mm in range(1, 13) if os.path.exists(gen_path(mm))]
    if target and not args.dry_run:
        months = sorted(set(months) | {new_month})
    patch_nav(months, args.dry_run)
    patch_modules(year, new_month, args.dry_run)
    bump_cache(args.dry_run)
    generate_and_verify(year, new_month, args.dry_run)
    print_manual_todo(year, new_month)

    cn = CN[new_month - 1]
    print('\n📦 提交（跑完确认无误后）：')
    files = ['modules.json', 'workbench.html', f'tools/{os.path.basename(gen_path(new_month))}']
    files += [f'tools/generate_{EN[mm - 1]}_summary.py' for mm in months]
    files.append(f'"月度总结/{cn}月销量分析.html"')
    print('  git add ' + ' '.join(dict.fromkeys(files)))
    print(f'  git commit -m "feat: 新增{cn}月月度总结页，六页导航统一补 {new_month} 月标签" && git pull --rebase && git push')


if __name__ == '__main__':
    main()
