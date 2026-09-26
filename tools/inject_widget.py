#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把「数据小管家」悬浮组件（assistant-widget.js）注入到项目各页面。

特点
  - 幂等：重复运行只会更新版本号，不会插入多个标签
  - 自动计算相对路径（子目录页面自动用 ../）
  - 只动 </body> 前的一行，其余内容零改动
  - 想撤销：把生成的标签行删掉即可，或用 git checkout

用法：
  python tools/inject_widget.py          # 注入 / 更新
  python tools/inject_widget.py --check  # 只检查当前状态，不写文件
  python tools/inject_widget.py --remove # 移除组件
"""
import io
import os
import re
import sys

VERSION = "2"                      # 改了 assistant-widget.js 就把这个数字 +1
WIDGET = "assistant-widget.js"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 不注入的目录（生成物 / 第三方 / 后端）
EXCLUDE_DIRS = {
    ".git", ".github", ".agents", ".claude", ".mimocode", ".workbuddy",
    "archive", "_artifacts", "node_modules", "__pycache__",
    "assistant-server", "cloudbase-assistant", "entry-assets", "assets",
}

# 不注入的单文件（自身就是完整聊天页）
EXCLUDE_FILES = {"数据小管家/index.html"}

TAG_RE = re.compile(
    r'[ \t]*<script[^>]*src=["\'][^"\']*' + re.escape(WIDGET) + r'(\?v=\d+)?["\'][^>]*>\s*</script>\s*\n?'
)


def targets():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.lower().endswith((".html", ".htm")):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            if rel in EXCLUDE_FILES:
                continue
            out.append((full, rel))
    return sorted(out, key=lambda x: x[1])


def prefix_for(rel):
    """子目录页面返回 '../'，根目录返回 ''"""
    depth = rel.count("/")
    return "../" * depth


def build_tag(rel):
    return '<script src="%s%s?v=%s" defer></script>\n' % (prefix_for(rel), WIDGET, VERSION)


def read(path):
    with io.open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
        return f.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(text)


def inject(html, rel):
    """返回 (新内容, 状态)  状态: added / updated / same"""
    tag = build_tag(rel)
    had = TAG_RE.search(html)

    # 先去掉旧标签（含不同版本号 / 不同前缀）
    cleaned = TAG_RE.sub("", html)

    idx = cleaned.rfind("</body>")
    if idx == -1:
        new = cleaned.rstrip("\n") + "\n" + tag
    else:
        new = cleaned[:idx] + tag + cleaned[idx:]

    if not had:
        return new, "added"
    if new == html:
        return new, "same"
    return new, "updated"


def remove(html):
    new = TAG_RE.sub("", html)
    return (new, "removed") if new != html else (html, "same")


def main():
    mode = "inject"
    if "--check" in sys.argv:
        mode = "check"
    elif "--remove" in sys.argv:
        mode = "remove"

    files = targets()
    print("扫描到 %d 个 HTML 页面（根目录：%s）\n" % (len(files), ROOT))
    stat = {"added": 0, "updated": 0, "same": 0, "removed": 0}
    for full, rel in files:
        html = read(full)
        if mode == "remove":
            new, st = remove(html)
        else:
            new, st = inject(html, rel)
        stat[st] = stat.get(st, 0) + 1
        mark = {"added": "＋", "updated": "～", "same": "＝", "removed": "－"}.get(st, "?")
        print("  %s %-46s %s" % (mark, rel, st))
        if mode != "check" and st in ("added", "updated", "removed"):
            write(full, new)
    print("\n结果：新增 %d / 更新 %d / 无变化 %d / 移除 %d" % (
        stat.get("added", 0), stat.get("updated", 0), stat.get("same", 0), stat.get("removed", 0)))
    if mode == "check":
        print("（--check 模式，未写入任何文件）")


if __name__ == "__main__":
    main()
