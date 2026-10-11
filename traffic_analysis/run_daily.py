#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""流量分析「一条命令跑完」入口：xlsx -> 入库 -> 环比/规则/日报 -> git commit -> push。

给桌面上的「刷流量数据.bat」调用，也可以手动跑：

    python traffic_analysis/run_daily.py                      # 自动找（桌面 流量数据.xlsx / 流量数据 文件夹 / 桌面+下载里最新的「xx流量」文件夹与散装表）
    python traffic_analysis/run_daily.py "D:\\x\\10.11流量.xlsx"
    python traffic_analysis/run_daily.py "C:\\Users\\Administrator\\Desktop\\10.10日流量"   # 文件夹：多直播间一天一次入库
    python traffic_analysis/run_daily.py "下载\\A10.8日流量.xlsx" "下载\\A10.9日流量.xlsx"     # 多份/多天一起给也行，按日期自动分批
    python traffic_analysis/run_daily.py --no-push            # 只入库+提交，不推
    python traffic_analysis/run_daily.py --rebuild-only       # 只重建 index.json + 全部日报

所有中文提示都走 sys.stdout（UTF-8），不依赖 cmd 的代码页 —— 见 WORKFLOW 🅲。
"""
import os
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAFFIC = os.path.join(ROOT, 'traffic_analysis')
DESKTOP = os.path.join(os.path.expanduser('~'), 'Desktop')
DOWNLOADS = os.path.join(os.path.expanduser('~'), 'Downloads')
SEARCH_DIRS = [DESKTOP, DOWNLOADS]
DEFAULT_XLSX = os.path.join(DESKTOP, '流量数据.xlsx')
DEFAULT_DIR = os.path.join(DESKTOP, '流量数据')
GIT_ADD_PATHS = ['traffic_analysis/data', 'traffic_analysis/reports']
TABLE_EXT = ('.xlsx', '.xls', '.csv')

# 复用入库脚本的日期解析（文件名「A10.8日流量.xlsx」、文件夹名「10.10日流量」都能认）
sys.path.insert(0, TRAFFIC)
try:
    import daily_update as _du
except Exception:                                     # noqa: BLE001 —— 解析不到就退化成「用今天」
    _du = None


def date_of_label(name):
    """从文件名 / 文件夹名推日期（YYYY-MM-DD），推不出返回 None。"""
    if _du is None:
        return None
    try:
        return _du.parse_date_from_name(os.path.basename(str(name).rstrip('\\/')))
    except Exception:                                 # noqa: BLE001
        return None


def _scan():
    """在桌面 + 下载里找「名字含流量」的文件夹与散装表（排除 ~$ 临时文件）。"""
    folders, files = [], []
    for base in SEARCH_DIRS:
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            if name.startswith('~$') or '流量' not in name:
                continue
            p = os.path.join(base, name)
            if os.path.isdir(p):
                folders.append(p)
            elif name.lower().endswith(TABLE_EXT):
                files.append(p)
    folders.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return folders, files


def find_default_input():
    """不带参数时自动找要入库的东西，返回**列表**（可能同时含文件夹和散装表、跨多天）。

    优先级：桌面「流量数据.xlsx」 > 桌面「流量数据」文件夹 >
    桌面+下载里最新的「xx流量」文件夹（再加上散装表；与文件夹同一天的表跳过，避免同一天入库两遍）。
    """
    if os.path.isfile(DEFAULT_XLSX):
        return [DEFAULT_XLSX]
    if os.path.isdir(DEFAULT_DIR):
        return [DEFAULT_DIR]
    folders, files = _scan()
    out = []
    folder_date = None
    if folders:
        out.append(folders[0])
        folder_date = date_of_label(folders[0])
    for f in files:
        d = date_of_label(f)
        if folder_date and d == folder_date:
            continue
        if f not in out:
            out.append(f)
    return out


def xlsx_count(path):
    """文件夹里有几份表（用于打印「6 份表 = 6 个直播间」）。"""
    if not os.path.isdir(path):
        return 0
    n = 0
    for name in os.listdir(path):
        if name.lower().endswith(TABLE_EXT):
            n += 1
    return n


def label_from_sources(sources):
    """提交信息里的日期标签：从输入文件名/文件夹名推，如「10.8」「10.8-10.9」「10.8、10.10」。"""
    ds = []
    for s in sources or []:
        d = date_of_label(s)
        if d and d not in ds:
            ds.append(d)
    if not ds:
        from datetime import date
        t = date.today()
        return '%d.%d' % (t.month, t.day)
    ds.sort()

    def md(x):
        _y, m, dd = x.split('-')
        return '%d.%d' % (int(m), int(dd))

    if len(ds) == 1:
        return md(ds[0])
    if len(ds) == 2:
        return md(ds[0]) + '-' + md(ds[1])
    return '、'.join(md(x) for x in ds)


def log(msg=''):
    print(msg, flush=True)


def run_git(args, check=True):
    """跑一条 git 命令并把输出原样转出来；返回 (ok, 合并输出)。"""
    p = subprocess.run(['git'] + args, cwd=ROOT, capture_output=True)
    out = (p.stdout or b'') + (p.stderr or b'')
    text = out.decode('utf-8', errors='replace').strip()
    if text:
        for line in text.splitlines():
            log('    ' + line)
    ok = (p.returncode == 0)
    if not ok and check:
        log('    ⚠️ git %s 退出码 %d' % (' '.join(args), p.returncode))
    return ok, text


def run_py(script, extra):
    p = subprocess.run([sys.executable, script] + extra, cwd=ROOT)
    return p.returncode == 0


def main():
    argv = sys.argv[1:]
    no_push = '--no-push' in argv
    rebuild_only = '--rebuild-only' in argv
    argv = [a for a in argv if a not in ('--no-push', '--rebuild-only')]

    log('=' * 60)
    log('  流量数据入库 → 环比 → 平台规则匹配 → 同步线上')
    log('=' * 60)

    update_py = os.path.join(TRAFFIC, 'daily_update.py')
    if not os.path.exists(update_py):
        log('❌ 找不到入库脚本：%s' % update_py)
        return 1

    sources = []
    # ---------- 1. 入库 ----------
    if rebuild_only:
        log('\n[1/3] 只重建 index.json + 全部日报（--rebuild-only）…')
        if not run_py(update_py, ['--rebuild']):
            log('❌ 重建失败，已中止，未做任何提交。')
            return 1
    else:
        if argv:
            sources = [os.path.abspath(a) for a in argv]
        else:
            sources = find_default_input()
            if sources:
                log('\n    自动找到 %d 个输入：' % len(sources))
                for s in sources:
                    if os.path.isdir(s):
                        log('      - %s（%d 份表）' % (s, xlsx_count(s)))
                    else:
                        log('      - %s' % s)
        missing = [s for s in sources if not os.path.exists(s)]
        if not sources or missing:
            log('\n❌ 找不到流量表 / 流量文件夹：%s' % ('、'.join(missing) if missing else DEFAULT_XLSX))
            log('   放法（随便选一种）：')
            log('     A. 单份表 → 桌面命名为「流量数据.xlsx」')
            log('     B. 多间直播间 → 桌面放一个文件夹，如「10.10日流量\\」里面装 6 份表，文件名就是直播间名')
            log('     C. 多天多间 → 直接把表丢进「下载」文件夹，文件名带日期（如 A直播间10.8日流量.xlsx），本脚本会按日期分批入库')
            log('   然后双击桌面「刷流量数据.bat」；或手动指定：python traffic_analysis/run_daily.py "<路径>" "<路径2>"')
            return 1
        log('\n[1/3] 解析入库 + 生成日报 …')
        for s in sources:
            if os.path.isdir(s):
                log('    源文件夹：%s（%d 份表）' % (s, xlsx_count(s)))
            else:
                log('    源文件：%s' % s)
        if not run_py(update_py, sources):
            log('\n❌ 入库失败，已中止，未做任何提交。上面有具体报错。')
            return 1

    # ---------- 2. 提交 ----------
    log('\n[2/3] 提交到 git …')
    run_git(['add'] + GIT_ADD_PATHS)
    ok, _ = run_git(['diff', '--cached', '--quiet'], check=False)
    if ok:
        log('    本次数据无变化，跳过提交。')
    else:
        msg = 'feat: 流量数据 %s日更新' % label_from_sources(sources)
        ok, _ = run_git(['commit', '-m', msg])
        if not ok:
            log('❌ git commit 失败，数据已入库但未提交。')
            return 1

    if no_push:
        log('\n（--no-push：跳过 push）')
        return 0

    # ---------- 3. 推送 ----------
    log('\n[3/3] 推送到 GitHub …')
    ok, text = run_git(['pull', '--rebase'], check=False)
    stashed = False
    if not ok and ('unstaged changes' in text or 'local changes' in text):
        # 工作区还有别处没提交的改动（文档/脚本等），先临时收起来，pull 完再还原
        log('    工作区有未提交改动，先 git stash 收起来 …')
        sok, _ = run_git(['stash', 'push', '--keep-index', '-u'], check=False)
        if sok:
            stashed = True
            ok, text = run_git(['pull', '--rebase'], check=False)
    if not ok:
        if stashed:
            run_git(['stash', 'pop'], check=False)
        log('❌ git pull --rebase 没干净完成（大概率有冲突）。')
        log('   处理：git status 看冲突文件 → 改完 git add → git rebase --continue → 再跑本脚本。')
        log('   想放弃这次 rebase：git rebase --abort')
        return 1
    if stashed:
        run_git(['stash', 'pop'], check=False)
    ok, text = run_git(['push'], check=False)
    if not ok:
        log('❌ push 被拒。可试：')
        log('   git stash push && git pull --rebase && git stash pop')
        return 1
    run_git(['log', '--oneline', '-1'])
    log('\n✅ 完成。线上页面：工作台 → 流量分析，刷新即可看到当天数据。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
