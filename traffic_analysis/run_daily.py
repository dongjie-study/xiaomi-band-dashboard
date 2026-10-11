#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""流量分析「一条命令跑完」入口：xlsx -> 入库 -> 环比/规则/日报 -> git commit -> push。

给桌面上的「刷流量数据.bat」调用，也可以手动跑：

    python traffic_analysis/run_daily.py                      # 自动找桌面 流量数据.xlsx / 流量数据 文件夹 / 最新的「xx流量」文件夹
    python traffic_analysis/run_daily.py "D:\\x\\10.11流量.xlsx"
    python traffic_analysis/run_daily.py "C:\\Users\\Administrator\\Desktop\\10.10日流量"   # 文件夹：多直播间一天一次入库
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
DEFAULT_XLSX = os.path.join(DESKTOP, '流量数据.xlsx')
DEFAULT_DIR = os.path.join(DESKTOP, '流量数据')
GIT_ADD_PATHS = ['traffic_analysis/data', 'traffic_analysis/reports']


def find_default_input():
    """不带参数时自动找当天要入库的东西（先单文件、再文件夹、再桌面上最新的「xx流量」文件夹）。

    多直播间的一天是「一个文件夹装几份表」（如 10.10日流量/ 里 6 份），
    文件名就是直播间名，所以文件夹也算合法输入。
    """
    if os.path.isfile(DEFAULT_XLSX):
        return DEFAULT_XLSX
    if os.path.isdir(DEFAULT_DIR):
        return DEFAULT_DIR
    if os.path.isdir(DESKTOP):
        cands = []
        for name in os.listdir(DESKTOP):
            p = os.path.join(DESKTOP, name)
            if os.path.isdir(p) and '流量' in name:
                cands.append((os.path.getmtime(p), p))
        if cands:
            cands.sort(reverse=True)
            return cands[0][1]
    return None


def xlsx_count(path):
    """文件夹里有几份表（用于打印「6 份表 = 6 个直播间」）。"""
    if not os.path.isdir(path):
        return 0
    n = 0
    for name in os.listdir(path):
        if name.lower().endswith(('.xlsx', '.xls', '.csv')):
            n += 1
    return n


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

    # ---------- 1. 入库 ----------
    if rebuild_only:
        log('\n[1/3] 只重建 index.json + 全部日报（--rebuild-only）…')
        if not run_py(update_py, ['--rebuild']):
            log('❌ 重建失败，已中止，未做任何提交。')
            return 1
    else:
        if argv:
            src = os.path.abspath(argv[0])
        else:
            src = find_default_input()
            if src:
                log('\n    自动找到输入：%s' % src)
        if not src or not os.path.exists(src):
            log('\n❌ 找不到流量表 / 流量文件夹：%s' % (src or DEFAULT_XLSX))
            log('   两种放法（随便选一种，都在桌面）：')
            log('     A. 单份表 → 命名「流量数据.xlsx」')
            log('     B. 多间直播间 → 放一个文件夹，如「10.10日流量\\」里面装 6 份表，文件名就是直播间名')
            log('   然后双击桌面「刷流量数据.bat」；或手动指定：python traffic_analysis/run_daily.py "<路径>"')
            return 1
        log('\n[1/3] 解析入库 + 生成日报 …')
        if os.path.isdir(src):
            log('    源文件夹：%s（%d 份表 = %d 个直播间）' % (src, xlsx_count(src), xlsx_count(src)))
        else:
            log('    源文件：%s' % src)
        if not run_py(update_py, [src]):
            log('\n❌ 入库失败，已中止，未做任何提交。上面有具体报错。')
            return 1

    # ---------- 2. 提交 ----------
    log('\n[2/3] 提交到 git …')
    run_git(['add'] + GIT_ADD_PATHS)
    ok, _ = run_git(['diff', '--cached', '--quiet'], check=False)
    if ok:
        log('    本次数据无变化，跳过提交。')
    else:
        from datetime import date
        d = date.today()
        msg = 'feat: 流量数据 %d.%d日更新' % (d.month, d.day)
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
