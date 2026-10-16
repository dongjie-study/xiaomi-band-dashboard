#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""流量分析「一条命令跑完」入口：xlsx -> 入库 -> 环比/规则/日报 -> git commit -> push。

给桌面上的「刷流量数据.bat」调用，也可以手动跑：

    python traffic_analysis/run_daily.py                      # 自动找（桌面 流量数据.xlsx / 流量数据 文件夹 / 桌面+下载里最新的「xx流量」文件夹与散装表）
    python traffic_analysis/run_daily.py "D:\\x\\10.11流量.xlsx"
    python traffic_analysis/run_daily.py "C:\\Users\\Administrator\\Desktop\\10.10日流量"   # 文件夹：多直播间一天一次入库
    python traffic_analysis/run_daily.py "下载\\A10.8日流量.xlsx" "下载\\A10.9日流量.xlsx"     # 多份/多天一起给也行，按日期自动分批
    python traffic_analysis/run_daily.py --no-push            # 只入库+复核+提交，不推
    python traffic_analysis/run_daily.py --no-commit          # 只入库+复核（不提交不推送），先人眼核对
    python traffic_analysis/run_daily.py --no-verify          # 跳过复核（不推荐）
    python traffic_analysis/run_daily.py --page               # 额外跑一次页面校验（page_check.py，约 4 秒）
    python traffic_analysis/run_daily.py --no-live            # 推送后不校验线上是否同步
    python traffic_analysis/run_daily.py --room "小米智能设备旗舰店直播间" "…\10.13日流量.xlsx"
    python traffic_analysis/run_daily.py --rebuild-only       # 只重建 index.json + 全部日报

四步：① 解析入库 + 生成日报 ② 自动复核（verify_day.py：源表「整体」行 ↔ 日档 ↔ 全店汇总 ↔
日报 ↔ 索引 ↔ 环比%）③ git commit ④ pull --rebase + push + **线上同步校验**（拉线上 index.json / 当天日档
跟本地逐字节比对，只警告不失败，--no-live 可跳过）。**复核没过就不提交**，避免把错数据推上线。

所有中文提示都走 sys.stdout（UTF-8），不依赖 cmd 的代码页 —— 见 WORKFLOW 🅲 与
traffic_analysis/每日流量流程.md。
"""
import json
import os
import socket
import subprocess
import sys
import time

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
VERIFY_PY = os.path.join(TRAFFIC, 'verify_day.py')      # 入库后的自动复核（纯 Python，约 0.2 秒）
PAGE_PY = os.path.join(TRAFFIC, 'page_check.py')        # 页面校验（要 playwright，--page 时才跑）
TABLE_EXT = ('.xlsx', '.xls', '.csv')
LIVE_BASE = 'https://xiaomi-band-dashboard.pages.dev'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

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


def http_get(url, retries=3, timeout=20):
    """GET 一个 URL（带浏览器 UA，DNS 强制 IPv4），返回 (bytes, 错误)。

    ★ 本机 IPv6 出网会 TLS 握手超时（urllib 报 handshake timed out、curl 不加 -4 也是 rc=28），
      这里把 getaddrinfo 临时钉到 IPv4 —— 等价于 curl -4。
    """
    import urllib.request
    orig = socket.getaddrinfo
    socket.getaddrinfo = lambda host, port, family=0, type=0, proto=0, flags=0: orig(
        host, port, socket.AF_INET, type, proto, flags)
    try:
        last = None
        for i in range(max(1, retries)):
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': UA, 'Cache-Control': 'no-cache', 'Pragma': 'no-cache'})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.read(), None
            except Exception as e:                     # noqa: BLE001
                last = e
                if i + 1 < max(1, retries):
                    time.sleep(1.5 * (i + 1))
        return None, last
    finally:
        socket.getaddrinfo = orig


def _norm_bytes(b):
    """比对前把换行归一成 LF。

    Windows 上检出/写盘会把 LF 变 CRLF（core.autocrlf），日档字节数会凭空多出「行数」个字节，
    和线上（仓库里存的是 LF）一比就假报「不一致」——2026-10-16 实测踩过。
    """
    return b.replace(b'\r\n', b'\n') if b else b


def live_check(days):
    """推送后确认线上已经同步（比对 index.json 与当天日档/日报字节）。

    只报告、不影响退出码：网络抖动 / Cloudflare 部署延迟都不该让「数据已入库并提交」变成失败。
    """
    t = time.time()
    log('\n[4/4·b] 线上同步校验：%s/traffic_analysis/' % LIVE_BASE)
    local_idx_p = os.path.join(TRAFFIC, 'data', 'index.json')
    try:
        local_idx = json.load(open(local_idx_p, encoding='utf-8'))
    except Exception as e:                             # noqa: BLE001
        log('    ⚠️ 读不到本地 index.json（%s），跳过线上校验' % e)
        return False
    local_days = [d.get('date') for d in (local_idx.get('days') or []) if isinstance(d, dict)]
    local_tail = local_days[-1] if local_days else None
    raw, err = http_get(LIVE_BASE + '/traffic_analysis/data/index.json')
    if raw is None:
        log('    ⚠️ 拉不到线上 index.json：%s' % err)
        log('       网络或 Cloudflare 波动，本次提交照样有效；稍后刷新线上页面确认即可。')
        return False
    try:
        idx = json.loads(raw.decode('utf-8'))
    except Exception as e:                             # noqa: BLE001
        log('    ⚠️ 线上 index.json 解析失败：%s' % e)
        return False
    online = [d.get('date') for d in (idx.get('days') or []) if isinstance(d, dict)]
    tail = online[-1] if online else None
    if tail != local_tail:
        log('    ⚠️ 线上还停在 %s，本地已到 %s（部署通常 10~30 秒，稍后刷新页面再看）' % (tail, local_tail))
        return False
    targets = [d for d in (days or []) if d] or ([local_tail] if local_tail else [])
    want = sorted(set(targets + ([local_tail] if local_tail else [])))
    ok_n, bad = 0, []
    for d in want:
        if d not in online:
            bad.append('%s（线上索引里没有）' % d)
            continue
        lp = os.path.join(TRAFFIC, 'data', d[:4], d + '.json')
        if not os.path.exists(lp):
            continue
        lb = open(lp, 'rb').read()
        rb, e2 = http_get('%s/traffic_analysis/data/%s/%s.json' % (LIVE_BASE, d[:4], d))
        if rb is None:
            bad.append('%s（拉不到：%s）' % (d, e2))
        elif _norm_bytes(rb) != _norm_bytes(lb):
            nb_r, nb_l = len(_norm_bytes(rb)), len(_norm_bytes(lb))
            bad.append('%s（线上 %d 字节 ≠ 本地 %d 字节，已按 LF 归一）' % (d, nb_r, nb_l))
        else:
            ok_n += 1
    # 日报（全店）也顺手比一份，确认 reports 一起上线了
    if local_tail:
        import urllib.parse
        rp = os.path.join(TRAFFIC, 'reports', local_tail[:4], local_tail, '全店.json')
        if os.path.exists(rp):
            rb, _e3 = http_get('%s/traffic_analysis/reports/%s/%s/%s'
                               % (LIVE_BASE, local_tail[:4], local_tail,
                                  urllib.parse.quote('全店.json')))
            if rb is not None and _norm_bytes(rb) != _norm_bytes(open(rp, 'rb').read()):
                bad.append('日报 %s/全店.json 与本地不一致' % local_tail)
    if bad:
        log('    ⚠️ 线上校验有异常：%s' % '；'.join(bad))
        log('       若 push 显示成功，多等 10~30 秒（Cloudflare 部署）再刷新页面；仍不对就跑 --no-live 之外的复检。')
        return False
    log('    ✅ 线上已同步：index 末条 %s（共 %s 天）、%s 天日档与本地逐字节一致（按 LF 归一，%.1f 秒）'
        % (tail, len(online), ok_n, time.time() - t))
    log('       页面：%s/traffic_analysis/' % LIVE_BASE)
    return True


def dates_from_sources(sources):
    """输入里能认出的日期（升序去重）；认不出返回空列表。"""
    out = []
    for s in sources or []:
        d = date_of_label(s)
        if d and d not in out:
            out.append(d)
    out.sort()
    return out


def main():
    if any(a in ('-h', '--help') for a in sys.argv[1:]):
        log((__doc__ or '').strip())                  # ★ 以前跑 --help 会真的开始入库，现在只打用法
        return 0
    t_all = time.time()
    argv = sys.argv[1:]
    flags = {}
    for f in ('--no-push', '--no-commit', '--no-verify', '--page', '--rebuild-only', '--no-live'):
        flags[f] = f in argv
    room = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--room' and i + 1 < len(argv):
            room = argv[i + 1]
            i += 2
            continue
        if a.startswith('--room='):
            room = a.split('=', 1)[1]
            i += 1
            continue
        rest.append(a)
        i += 1
    argv = [a for a in rest if not a.startswith('--')]
    if room:
        log('    手动指定直播间：%s（--room 会覆盖所有输入文件）' % room)

    log('=' * 60)
    log('  流量数据：入库 → 复核 → 提交 → 同步线上（4 步）')
    log('=' * 60)

    update_py = os.path.join(TRAFFIC, 'daily_update.py')
    if not os.path.exists(update_py):
        log('❌ 找不到入库脚本：%s' % update_py)
        return 1

    sources = []
    # ---------- 1. 入库 ----------
    t1 = time.time()
    if flags['--rebuild-only']:
        log('\n[1/4] 只重建 index.json + 全部日报（--rebuild-only）…')
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
        log('\n[1/4] 解析入库 + 生成日报 …')
        for s in sources:
            if os.path.isdir(s):
                log('    源文件夹：%s（%d 份表）' % (s, xlsx_count(s)))
            else:
                log('    源文件：%s' % s)
        if not run_py(update_py, sources + (['--room', room] if room else [])):
            log('\n❌ 入库失败，已中止，未做任何提交。上面有具体报错。')
            return 1
    log('    ✅ 入库完成（%.1f 秒）' % (time.time() - t1))

    # ---------- 2. 复核（不通过就不提交，避免把错数据推上线） ----------
    t2 = time.time()
    if flags['--no-verify']:
        log('\n[2/4] 复核：已跳过（--no-verify）')
    else:
        log('\n[2/4] 复核：源表「整体」行 ↔ 日档 ↔ 全店汇总 ↔ 日报 ↔ 索引 ↔ 环比% …')
        # 把输入文件所在目录一并交给复核脚本，这样源表放在桌面/下载之外也能做 A/F 两段比对
        src_args = []
        for d in sorted({(s if os.path.isdir(s) else os.path.dirname(s)) for s in sources}):
            src_args += ['--src', d]
        if src_args:
            log('    源表目录：%s' % '、'.join(src_args[1::2]))
        for d in (dates_from_sources(sources) or [None]):
            if not run_py(VERIFY_PY, ([d] if d else []) + src_args):
                log('\n❌ 复核没通过，已中止：**没有提交，线上不受影响**。')
                log('   看上面的 ❌ 明细：是我方 bug 就改脚本，是平台口径异常就人工确认。')
                log('   确实要强行过（不推荐）：加 --no-verify')
                return 1
    if flags['--page']:
        log('\n    页面校验 page_check.py（浏览器布局 + 全口径 + 多宽度）…')
        if not os.path.exists(PAGE_PY) or not run_py(PAGE_PY, []):
            log('\n❌ 页面校验没过，已中止，未提交。')
            return 1
    log('    ✅ 复核通过（%.1f 秒）' % (time.time() - t2))

    # ---------- 3. 提交 ----------
    if flags['--no-commit']:
        log('\n[3/4] 提交：已跳过（--no-commit）—— 数据已入库，自己看 git status / git diff')
        log('\n⏱ 全流程 %.1f 秒（未提交、未推送）' % (time.time() - t_all))
        return 0
    t3 = time.time()
    log('\n[3/4] 提交到 git …')
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

    log('    ✅ 提交完成（%.1f 秒）' % (time.time() - t3))

    if flags['--no-push']:
        log('\n（--no-push：跳过 push）')
        log('\n⏱ 全流程 %.1f 秒' % (time.time() - t_all))
        return 0

    # ---------- 4. 推送 ----------
    t4 = time.time()
    log('\n[4/4] 推送到 GitHub …')
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
    log('    ✅ 推送完成（%.1f 秒）' % (time.time() - t4))

    # ---------- 4·b. 线上同步校验（只报告，不影响退出码） ----------
    if flags['--no-live']:
        log('\n[4/4·b] 线上同步校验：已跳过（--no-live）')
    else:
        live_check(dates_from_sources(sources))

    log('\n✅ 完成。线上页面：工作台 → 流量分析，刷新即可看到当天数据。')
    log('⏱ 全流程 %.1f 秒' % (time.time() - t_all))
    return 0


if __name__ == '__main__':
    sys.exit(main())
