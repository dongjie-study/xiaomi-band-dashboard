# -*- coding: utf-8 -*-
"""
直播间归属文档生成器 —— 消灭「team_config.py 和 markdown 两边同步」的漂移。

单一数据源：`team_config.py`（TEAM_MAP / OUR_ROOMS / LIANGMI_ROOMS / IGNORED_ROOMS）
本脚本负责把它的机械内容写进三个地方：

  1. `直播间分类.md`      —— 重写 <!-- GEN:* --> 标记内的区块，标记外的手写内容一字不动
  2. `直播间服务商汇总.md` —— 整份重新生成（它是 `直播间销量汇总.py` 的**运行时输入**，格式有硬契约）
  3. `docs/03-直播间与团队.md` —— 知识库全量对照表

为什么 2 要整份生成：它是被代码 `load_service_map()` 解析的数据文件，不是给人看的文档。
历史上「小米耳机」（09-13 加进 team_config）漏同步，导致该文件与代码不一致。

安全设计：生成 `直播间服务商汇总.md` 后，会调用**真正的解析器**回读一遍做断言，
解析不出预期条数就**不落盘**（保留原文件），避免把运行时的数据源写坏。

用法：
    python tools/gen_room_docs.py            # 生成
    python tools/gen_room_docs.py --check    # 只检查是否已过期（过期退出码 1，供 CI 用）
"""
import argparse
import importlib.util
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import team_config as tc  # noqa: E402

CLASSIFY_MD = os.path.join(ROOT, "直播间分类.md")
SERVICE_MD = os.path.join(ROOT, "直播间服务商汇总.md")
DOCS_MD = os.path.join(ROOT, "docs", "03-直播间与团队.md")
SERVICE_PY = os.path.join(ROOT, "直播间销量汇总.py")

# ---------------------------------------------------------------------------
# 手写区：这些是 team_config.py 里没有、只能人工维护的知识。
# 改这里，不要改生成出来的 md（改了下次也会被覆盖）。
# ---------------------------------------------------------------------------

# 团队 → 服务商名。vendor 用于《直播间分类.md》，vendor_disp 用于《直播间服务商汇总.md》
TEAM_META = {
    "我司":     {"vendor": "阳光雨蔚",    "vendor_disp": "阳光雨蔚（我司）",     "bold": True},
    "机械空间": {"vendor": "机器空间",    "vendor_disp": "机器空间（机械空间）", "bold": False},
    "纵横":     {"vendor": "纵横 / 综讯", "vendor_disp": "纵横 / 综讯（纵横）",  "bold": False},
    "凝云":     {"vendor": "渡云",        "vendor_disp": "渡云（凝云）",         "bold": False},
    "逐梦":     {"vendor": "逐梦",        "vendor_disp": "逐梦",                "bold": False},
    "斐纳":     {"vendor": "—",           "vendor_disp": "斐纳",                "bold": False},
    "乐群":     {"vendor": "乐群",        "vendor_disp": "乐群",                "bold": False},
    "炽木电商": {"vendor": "炽木电商",    "vendor_disp": "炽木电商",            "bold": False},
    "米乐":     {"vendor": "米乐",        "vendor_disp": "米乐",                "bold": False},
    "良米":     {"vendor": "—",           "vendor_disp": "良米",                "bold": False},
}

# 直播间 → 备注（《直播间服务商汇总.md》第二列）
ROOM_NOTES = {
    "小米智能设备旗舰店直播间": "只卖儿童手表/路由器，无 10Pro 销售",
    "小米官方手环账号": "2026-09-04 新增",
    "小米手环智能穿戴官方直播间": "2026-09-08 新增",
    "小米手环官方": "2026-09-06 新增（新服务商）",
    "小米手环11直播间": "2026-09-04 新增",
    "小米耳机": "2026-09-13 用户确认（此前靠兜底归良米，结果一致）",
}

# 商品卡渠道（无实体直播间）
CARD_CHANNELS = [("我司商品卡", "阳光雨蔚（我司）"), ("良米商品卡", "良米")]

# 极易混淆的直播间（人工判断，代码里没有）
CONFUSING = [
    ("小米**官方手环**直播间", "阳光雨蔚（我司）", "「官方」在前"),
    ("小米**手环官方**直播间", "纵横 / 综讯", "「手环」在前"),
    ("小米**手环官方**", "米乐", "无「直播间」/「账号」后缀，独立新服务商"),
    ("小米官方手环**号**", "良米", "「号」后缀"),
    ("小米官方手环**账号**", "斐纳", "「账号」后缀"),
    ("小米**手环官方账号**", "逐梦", "整串连写"),
    ("小米官方手表**直播号**", "纵横 / 综讯", "「直播号」后缀"),
    ("小米官方手表**直播**", "良米", "「直播」后缀"),
    ("小米**手表官方**直播间", "良米", "「手表」在前"),
    ("小米官方手表", "阳光雨蔚（我司）", "无后缀"),
]

# 待确认归属（暂按现归属执行）
PENDING = [
    ("小米智能穿戴官方直播间", "斐纳", "对应表写「纵横 / 综讯」", "¥7,063；若改则斐纳无直播间"),
    ("小米手环新品直播间", "良米（兜底）", "历史数据曾标为凝云 6 天", "¥7,421"),
]

# 特殊说明（不进 team_config，靠兜底）
SPECIAL = [
    ("小米官方平板直播间", "2026-09-02 用户确认忽视、不同步分类，未显式入库；若出现在订单中，默认归良米"),
]

# 业绩面板 roomId（源：主播业绩/业绩demo.html 的 ROOMS 数组）
ROOMID = [
    ("小米数码旗舰店", "room_xiaomi_digital"),
    ("小米官方手环直播间", "room_xiaomi_band"),
    ("小米官方手表", "room_xiaomi_watch"),
    ("小米官旗手表直播间", "room_xiaomi_watch_flagship"),
    ("小米官方耳机直播间", "room_xiaomi_earphone"),
    ("小米AI眼镜直播间", "room_xiaomi_glasses"),
    ("小米智能设备旗舰店直播间", "room_xiaomi_smart_device"),
    ("小米手环官旗直播间", "room_xiaomi_band_flagship"),
    ("手环预约期业绩", "room_xiaomi_band_preorder"),  # 伪直播间，非真实渠道
]

GEN_HEADER = "<!-- ⚙️ 本区块由 tools/gen_room_docs.py 自动生成，请勿手工编辑；改归属请改 team_config.py 后重跑脚本 -->"


# ---------------------------------------------------------------------------
# 构建：把 TEAM_MAP 整理成 团队 → [直播间]（按 TEAM_ORDER 排序）
# ---------------------------------------------------------------------------
def rooms_by_team():
    """团队 → [直播间]。**排除商品卡渠道**——它们不是直播间，在各文件里有自己的章节。"""
    cards = {c for c, _ in CARD_CHANNELS}
    buckets = {t: [] for t in tc.TEAM_ORDER}
    for room, team in tc.TEAM_MAP.items():
        if room in cards:
            continue
        buckets.setdefault(team, []).append(room)
    # 保持 TEAM_MAP 里的插入顺序（Python 3.7+ dict 有序），不额外排序
    return {t: rooms for t, rooms in buckets.items() if rooms}


# ---------------------------------------------------------------------------
# 生成 1：直播间分类.md 内的三个自动区块
# ---------------------------------------------------------------------------
def block_team_map():
    lines = [GEN_HEADER, "## 全部团队归属（`TEAM_MAP`）", "",
             "| 团队 | 服务商（对应表原文） | 直播间 |",
             "|------|-------------------|--------|"]
    for team, rooms in rooms_by_team().items():
        meta = TEAM_META.get(team, {})
        name = f"**{team}**" if meta.get("bold") else team
        lines.append(f"| {name} | {meta.get('vendor', '—')} | {'、'.join(rooms)} |")
    return "\n".join(lines)


def block_key_lists():
    our = set(tc.OUR_ROOMS)
    lm = set(tc.LIANGMI_ROOMS)
    # 名单按 TEAM_MAP 顺序输出，便于和上面的总表对照
    ordered = list(tc.TEAM_MAP.keys())
    our_s = "、".join([r for r in ordered if r in our])
    lm_s = "、".join([r for r in ordered if r in lm])
    return "\n".join([
        GEN_HEADER,
        f"- **`OUR_ROOMS`**：{our_s}",
        f"- **`LIANGMI_ROOMS`**：{lm_s}",
    ])


def block_ignored():
    lines = [GEN_HEADER, "## 忽略不入库", "",
             "| 直播间 | 处理 | 说明 |", "|--------|------|------|"]
    for room in tc.IGNORED_ROOMS:
        lines.append(f"| {room} | 忽略，不入库 | 见 `team_config.IGNORED_ROOMS` |")
    return "\n".join(lines)


def splice(text, marker, new_block):
    """把 <!-- GEN:X:BEGIN --> ... <!-- GEN:X:END --> 之间的内容换成 new_block。"""
    begin, end = f"<!-- GEN:{marker}:BEGIN -->", f"<!-- GEN:{marker}:END -->"
    i, j = text.find(begin), text.find(end)
    if i < 0 or j < 0:
        raise SystemExit(f"✗ {CLASSIFY_MD} 里找不到标记 {marker}，无法生成")
    return text[:i] + begin + "\n" + new_block + "\n" + text[j:]


def render_classify_md():
    with open(CLASSIFY_MD, encoding="utf-8") as f:
        text = f.read()
    for marker, fn in (("TEAM_MAP", block_team_map),
                       ("KEY_LISTS", block_key_lists),
                       ("IGNORED", block_ignored)):
        text = splice(text, marker, fn())
    return text


# ---------------------------------------------------------------------------
# 生成 2：直播间服务商汇总.md  ← 运行时输入，格式有硬契约
# ---------------------------------------------------------------------------
def render_service_md():
    buckets = rooms_by_team()
    n_rooms = sum(len(r) for r in buckets.values())
    lines = [
        "# 直播间服务商汇总",
        "",
        f"> 最后更新：{date.today():%Y-%m-%d}",
        "> 数据来源：`team_config.py`（`TEAM_MAP` / `IGNORED_ROOMS`）+ `直播间分类.md`（对照《小米店铺与服务商对应表》）",
        "> ⚙️ **本文件由 `tools/gen_room_docs.py` 自动生成，请勿手工编辑**——它是 `直播间销量汇总.py` 的运行时输入，"
        "改归属请改 `team_config.py` 后重跑脚本。",
        "",
        f"共 **{len(buckets)} 个服务商 / 团队**、**{n_rooms} 个直播间**"
        f"（含 {len(CARD_CHANNELS)} 个商品卡渠道标识），另有 **{len(tc.IGNORED_ROOMS)} 个直播间忽略不入库**。",
        "",
        "---",
        "",
        "## 一、直播间 ↔ 服务商 全量对照表",
        "",
    ]
    for team, rooms in buckets.items():
        meta = TEAM_META.get(team, {})
        lines.append(f"### {meta.get('vendor_disp', team)} — {len(rooms)} 个直播间")
        lines.append("")
        lines.append("| 直播间 | 备注 |")
        lines.append("|--------|------|")
        for r in rooms:
            lines.append(f"| {r} | {ROOM_NOTES.get(r, '')} |")
        lines.append("")

    lines += ["---", "", "## 二、商品卡渠道（无实体直播间，属渠道标识）", "",
              "| 渠道标识 | 服务商 |", "|----------|--------|"]
    for c, agent in CARD_CHANNELS:
        lines.append(f"| {c} | {agent} |")

    lines += ["", "---", "", "## 三、忽略不入库", "",
              "| 直播间 | 说明 |", "|--------|------|"]
    for r in tc.IGNORED_ROOMS:
        lines.append(f"| {r} | 归属未定，`IGNORED_ROOMS` 整间剔除，不参与统计 |")

    lines += ["", "---", "", "## 四、⚠️ 极易混淆的直播间（务必对照准确）", "",
              "这些名字只差一两个字，归属完全不同：", "",
              "| 直播间 | 服务商 |", "|--------|--------|"]
    for room, agent, _why in CONFUSING:
        lines.append(f"| {room} | {agent} |")

    lines += ["", "---", "", "## 五、特殊说明", "",
              "| 直播间 | 处理 |", "|--------|------|"]
    for room, note in SPECIAL:
        lines.append(f"| {room} | {note} |")

    lines += ["", "> **服务商名注**：「机器空间」（对应表原文）对应内部团队名「机械空间」；"
              "「渡云」对应「凝云」。二者源自《小米店铺与服务商对应表》，与内部团队命名略有差异，"
              "如有出入请以实际合同/资质为准。", ""]
    return "\n".join(lines)


def verify_service_md(text):
    """用真正的解析器回读生成结果，确认格式契约没被破坏。"""
    spec = importlib.util.spec_from_file_location("_svc", SERVICE_PY)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    except Exception as e:  # 模块顶层若有副作用失败，不阻塞生成校验
        return None, f"解析器模块导入失败：{type(e).__name__}: {e}"

    tmp = SERVICE_MD + ".verify-tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        parsed, ignored = mod.load_service_map(tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    problems = []
    # 盘古特殊说明里的兜底项 + 商品卡，会让解析结果比 TEAM_MAP 多
    expect = set(tc.TEAM_MAP) | {c for c, _ in CARD_CHANNELS} | {r for r, _ in SPECIAL}
    missing = expect - set(parsed)
    if missing:
        problems.append(f"解析漏了：{sorted(missing)}")
    if set(ignored) != set(tc.IGNORED_ROOMS):
        problems.append(f"忽略项不符：解析={sorted(ignored)} 期望={sorted(tc.IGNORED_ROOMS)}")
    # 归属一致性（排除兜底平板间）
    for room, agent in parsed.items():
        if room in (r for r, _ in SPECIAL):
            continue
        want = tc.TEAM_MAP.get(room)
        if want and AGENT_ALIAS.get(agent, agent) != want:
            problems.append(f"{room} 归属不符：解析={agent} 期望={want}")
    return problems, None


# 解析器读到的服务商名 → 内部团队名。两处差异来源：
#   1) 解析器会把「阳光雨蔚」重命名成「我司阳光」
#   2) 对应表原名与内部团队名不同（机器空间/机械空间、渡云/凝云、纵横/综讯）
AGENT_ALIAS = {
    "阳光雨蔚": "我司",
    "我司阳光": "我司",
    "机器空间": "机械空间",
    "纵横/综讯": "纵横",
    "渡云": "凝云",
}


# ---------------------------------------------------------------------------
# 生成 3：docs/03-直播间与团队.md
# ---------------------------------------------------------------------------
def render_docs03():
    our, lm = set(tc.OUR_ROOMS), set(tc.LIANGMI_ROOMS)
    roomid = dict(ROOMID)
    lines = [
        "# 03 · 直播间与团队",
        "",
        "> ⚙️ 本文件由 `tools/gen_room_docs.py` 自动生成，**请勿手工编辑**。",
        "> 改归属请改 `team_config.py`，然后跑 `python tools/gen_room_docs.py`。",
        f"> 最后生成：{date.today():%Y-%m-%d}",
        "",
        "## 一、归属总表",
        "",
        "| 直播间 | 团队 | 服务商 | 主打手环名单 | roomId |",
        "|--------|------|--------|-------------|--------|",
    ]
    for room, team in tc.TEAM_MAP.items():
        meta = TEAM_META.get(team, {})
        if room in our:
            on_list = "我司 ✔"
        elif room in lm:
            on_list = "良米 ✔"
        else:
            on_list = "—"
        lines.append(f"| {room} | {team} | {meta.get('vendor', '—')} | {on_list} | {roomid.get(room, '—')} |")

    lines += ["", "## 二、⚠️ 极易混淆的直播间", "",
              "这些名字只差一两个字，归属完全不同，**误判一次就污染累计统计**。", "",
              "| 直播间 | 归属 | 区别在哪 |", "|--------|------|---------|"]
    for room, agent, why in CONFUSING:
        lines.append(f"| {room} | {agent} | {why} |")

    lines += ["", "## 三、商品卡渠道（无实体直播间）", "",
              "| 渠道标识 | 归属 |", "|----------|------|"]
    for c, agent in CARD_CHANNELS:
        lines.append(f"| {c} | {agent} |")

    lines += ["", "## 四、忽略不入库", "",
              "`team_config.IGNORED_ROOMS`，`daily_update.py` 在 `load_and_clean` 中整间剔除，"
              "不参与任何统计。**源文件行数对不上时先减掉这几间再比对。**", "",
              "| 直播间 | 说明 |", "|--------|------|"]
    for r in tc.IGNORED_ROOMS:
        lines.append(f"| {r} | 归属未定，整间剔除 |")

    lines += ["", "## 五、待确认归属", "",
              "**暂按现归属执行**。确认后改 `team_config.py` 并重跑 `tools/migrate_reclassify.py`。", "",
              "| 直播间 | 现归属 | 疑点 | 影响 |", "|--------|--------|------|------|"]
    for r, cur, doubt, impact in PENDING:
        lines.append(f"| {r} | {cur} | {doubt} | {impact} |")

    lines += ["", "## 六、特殊处理", "", "| 直播间 | 处理 |", "|--------|------|"]
    for r, note in SPECIAL:
        lines.append(f"| {r} | {note} |")

    lines += ["", "## 七、团队展示色与标记", "",
              "源：`team_config.TEAM_COLORS` / `TEAM_MARKERS`。", "",
              "| 团队 | 颜色 | 标记 |", "|------|------|------|"]
    for t in tc.TEAM_ORDER:
        lines.append(f"| {t} | `{tc.TEAM_COLORS.get(t, '—')}` | {tc.TEAM_MARKERS.get(t, '—')} |")

    lines += [
        "",
        "## 八、兜底规则与风险",
        "",
        "- `classify_room()` 对 `TEAM_MAP` 里没有的名字**兜底归「良米」**。兜底是静默的——"
        "新直播间名不会报错，只会悄悄算进良米。",
        "- 因此 `WORKFLOW.md` 有一条硬规则：**遇到从未见过的新直播间名，先找用户确认归属，不要静默兜底**。",
        "- 新增直播间后必须做的事：改 `team_config.py` → 跑 `python tools/gen_room_docs.py`（本文件与两份 md 一起更新）"
        "→ 若涉及历史数据重划分，再跑 `python tools/migrate_reclassify.py`。",
        "",
        "---",
        "",
        "## 相关",
        "",
        "- 人工判断部分（易混淆原因、待确认疑点）的原始出处：`直播间分类.md`（本文件已收录，那边保留详注）",
        "- 变更历史：见 `直播间分类.md` 的「变更日志」",
        "- 运行时被谁读：`直播间销量汇总.py:load_service_map()` 解析 `直播间服务商汇总.md`",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="从 team_config.py 生成直播间归属文档")
    ap.add_argument("--check", action="store_true", help="只检查是否过期，不写文件")
    args = ap.parse_args()

    targets = {
        CLASSIFY_MD: render_classify_md(),
        DOCS_MD: render_docs03(),
    }
    service_text = render_service_md()

    # 硬校验：生成的服务商汇总必须能被真正的解析器读懂
    problems, err = verify_service_md(service_text)
    if err:
        print(f"⚠️  {err}\n   跳过《直播间服务商汇总.md》的生成，其余文件照常。")
    elif problems:
        print("✗ 生成的《直播间服务商汇总.md》未通过解析器自校验，**已中止、原文件未改动**：")
        for p in problems:
            print(f"    - {p}")
        return 2
    else:
        targets[SERVICE_MD] = service_text
        print("✓ 《直播间服务商汇总.md》通过解析器自校验")

    stale = []
    for path, text in targets.items():
        old = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                old = f.read()
        if old != text:
            stale.append(path)
            if not args.check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)

    if args.check:
        if stale:
            print("✗ 以下文档已过期，请跑 `python tools/gen_room_docs.py`：")
            for p in stale:
                print(f"    - {os.path.relpath(p, ROOT)}")
            return 1
        print("✓ 直播间归属文档与 team_config.py 一致")
        return 0

    for p in stale:
        print(f"✓ 已更新 {os.path.relpath(p, ROOT)}")
    if not stale:
        print("✓ 文档已是最新，无需改动")
    return 0


if __name__ == "__main__":
    sys.exit(main())
