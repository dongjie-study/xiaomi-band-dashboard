# -*- coding: utf-8 -*-
"""
直播间销量汇总自动化工具
用法:
    python 直播间销量汇总.py <订单.xlsx> [输出.xlsx]
说明:
    - 达人昵称列 -> 按同目录《直播间服务商汇总.md》映射到服务商
    - 忽略表中的直播间不入库
    - 按 服务商 -> 直播间 两级聚合: 订单数 / 销售额 / 占比 / ROI(=销售额/订单数)
    - 未匹配到的达人昵称会在控制台列出, 请补进服务商表
"""
import sys, os, re, glob
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))


def load_service_map(md_path):
    """解析《直播间服务商汇总.md》, 返回 (room_to_agent, ignored_rooms)"""
    with open(md_path, encoding="utf-8") as f:
        text = f.read()

    room_to_agent = {}
    ignored = set()

    def section(start_marker, end_marker=None):
        i = text.find(start_marker)
        if i < 0:
            return ""
        j = text.find(end_marker, i) if end_marker else len(text)
        if j < 0:
            j = len(text)
        return text[i:j]

    def parse_table_rooms(block):
        """从 markdown 表格块提取 (第一列, 第二列或None) 列表"""
        out = []
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells:
                continue
            first = cells[0]
            # 跳过分隔线 / 表头
            if set(first) <= set("-: "):
                continue
            out.append((first, cells[1] if len(cells) > 1 else None))
        return out

    # 一、各服务商章节(只取 "## 一、" 到 "## 二、" 之间, 避免误读后面章节)
    sec1 = section("## 一、", "## 二、")
    for sec in sec1.split("\n### ")[1:]:
        header = sec.splitlines()[0]
        agent = header.split("—")[0]
        agent = re.sub(r"[（(].*?[）)]", "", agent).strip().replace(" / ", "/")
        for name, _second in parse_table_rooms(sec):
            if name in ("直播间",):
                continue
            room_to_agent[name] = agent

    # 二、商品卡渠道表: | 渠道标识 | 服务商 |
    sec2 = section("## 二、", "## 三、")
    for name, agent_raw in parse_table_rooms(sec2):
        if name in ("渠道标识",) or not agent_raw:
            continue
        agent = re.sub(r"[（(].*?[）)]", "", agent_raw).strip().replace(" / ", "/")
        room_to_agent[name] = agent

    # 三、忽略不入库
    sec3 = section("## 三、", "## 四、")
    for name, _ in parse_table_rooms(sec3):
        if name == "直播间":
            continue
        ignored.add(name)

    # 五、特殊说明: 小米官方平板直播间 -> 良米
    if "小米官方平板直播间" not in room_to_agent:
        room_to_agent["小米官方平板直播间"] = "良米"

    # 显示名重命名（数据源 md 不改，仅输出时替换）
    AGENT_RENAME = {"阳光雨蔚": "我司阳光"}
    room_to_agent = {k: AGENT_RENAME.get(v, v) for k, v in room_to_agent.items()}

    return room_to_agent, ignored


def read_orders(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    header = [c.value for c in ws[1]]
    # 定位列
    col = {name: i for i, name in enumerate(header)}
    idx_amt = col["订单应付金额"]
    idx_nick = col["达人昵称"]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[idx_nick] is None:
            continue
        nick = str(r[idx_nick]).strip()
        amt = r[idx_amt]
        try:
            amt = float(amt) if amt is not None else 0.0
        except (TypeError, ValueError):
            amt = 0.0
        rows.append((nick, amt))
    return rows


def build_summary(rows, room_to_agent, ignored):
    # agent -> room -> [orders, amount]
    tree = {}
    unmatched = {}
    ignored_hit = {}
    for nick, amt in rows:
        if nick in ignored:
            ignored_hit[nick] = ignored_hit.get(nick, 0) + 1
            continue
        agent = room_to_agent.get(nick)
        if agent is None:
            unmatched[nick] = unmatched.get(nick, 0) + 1
            continue
        tree.setdefault(agent, {})
        tree[agent].setdefault(nick, [0, 0.0])
        tree[agent][nick][0] += 1
        tree[agent][nick][1] += amt
    return tree, unmatched, ignored_hit


def write_report(out_path, tree, unmatched, ignored_hit, total_orders, total_amount, src_name):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "直播间销售汇总"

    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    title_font = Font(bold=True, size=14)
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="4472C4")
    agent_fill = PatternFill("solid", fgColor="D9E1F2")
    total_fill = PatternFill("solid", fgColor="FFE699")
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")

    headers = ["服务商 / 直播间", "订单数", "销售额(元)", "服务商内订单占比", "全盘销售额占比", "ROI(元/单)"]
    ws.append([f"直播间销售汇总 — {src_name}"])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    ws.cell(1, 1).font = title_font
    ws.cell(1, 1).alignment = center

    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(2, c)
        cell.font = head_font
        cell.fill = head_fill
        cell.alignment = center
        cell.border = border

    # 服务商按销售额降序
    agent_list = sorted(tree.items(), key=lambda kv: -sum(v[1] for v in kv[1].values()))
    r = 3
    for agent, rooms in agent_list:
        a_orders = sum(v[0] for v in rooms.values())
        a_amount = sum(v[1] for v in rooms.values())
        # 服务商行
        ws.cell(r, 1, agent)
        ws.cell(r, 2, a_orders)
        ws.cell(r, 3, round(a_amount, 2))
        ws.cell(r, 4, None)
        ws.cell(r, 5, (a_amount / total_amount) if total_amount else 0)
        ws.cell(r, 6, round(a_amount / a_orders) if a_orders else 0)
        for c in range(1, 7):
            cell = ws.cell(r, c)
            cell.fill = agent_fill
            cell.font = Font(bold=True)
            cell.border = border
            cell.alignment = left if c == 1 else center
        r += 1
        # 直播间按销售额降序
        for room, (o, amt) in sorted(rooms.items(), key=lambda x: -x[1][1]):
            ws.cell(r, 1, "　　" + room)
            ws.cell(r, 2, o)
            ws.cell(r, 3, round(amt, 2))
            ws.cell(r, 4, (o / a_orders) if a_orders else 0)
            ws.cell(r, 5, None)
            ws.cell(r, 6, round(amt / o) if o else 0)
            for c in range(1, 7):
                cell = ws.cell(r, c)
                cell.border = border
                cell.alignment = left if c == 1 else center
            r += 1

    # 合计行
    ws.cell(r, 1, "全平台合计")
    ws.cell(r, 2, total_orders)
    ws.cell(r, 3, round(total_amount, 2))
    ws.cell(r, 4, None)
    ws.cell(r, 5, 1.0)
    ws.cell(r, 6, round(total_amount / total_orders) if total_orders else 0)
    for c in range(1, 7):
        cell = ws.cell(r, c)
        cell.fill = total_fill
        cell.font = Font(bold=True)
        cell.border = border
        cell.alignment = left if c == 1 else center
    total_row = r

    # 数字格式
    for row in ws.iter_rows(min_row=3, max_row=total_row):
        row[1].number_format = "#,##0"
        row[2].number_format = "#,##0.00"
        row[3].number_format = "0.0%"
        row[4].number_format = "0.0%"
        row[5].number_format = "#,##0"

    widths = [34, 10, 16, 18, 16, 14]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A3"

    wb.save(out_path)
    return total_row, unmatched, ignored_hit


def main():
    if len(sys.argv) < 2:
        print("用法: python 直播间销量汇总.py <订单.xlsx> [输出.xlsx]")
        sys.exit(1)
    src = sys.argv[1]
    if len(sys.argv) >= 3:
        out = sys.argv[2]
    else:
        base = os.path.splitext(os.path.basename(src))[0]
        out = os.path.join(os.path.dirname(os.path.abspath(src)), f"{base}_直播间销售汇总.xlsx")

    md_candidates = [os.path.join(HERE, "直播间服务商汇总.md")] + \
                    glob.glob(os.path.join(os.path.dirname(os.path.abspath(src)), "*.md"))
    md_path = next((p for p in md_candidates if os.path.exists(p)), None)
    if not md_path:
        print("找不到《直播间服务商汇总.md》")
        sys.exit(1)

    room_to_agent, ignored = load_service_map(md_path)
    rows = read_orders(src)
    tree, unmatched, ignored_hit = build_summary(rows, room_to_agent, ignored)

    total_orders = sum(v[0] for rooms in tree.values() for v in rooms.values())
    total_amount = sum(v[1] for rooms in tree.values() for v in rooms.values())

    write_report(out, tree, unmatched, ignored_hit, total_orders, total_amount,
                 os.path.basename(src))

    print(f"输出: {out}")
    print(f"纳入订单数: {total_orders}  销售额: {total_amount:,.2f}")
    if unmatched:
        print("⚠️ 未匹配到服务商的达人昵称(请补进服务商表):")
        for k, v in sorted(unmatched.items(), key=lambda x: -x[1]):
            print(f"   {k}  x{v}")
    if ignored_hit:
        print("已按规则忽略:")
        for k, v in ignored_hit.items():
            print(f"   {k}  x{v}")


if __name__ == "__main__":
    main()
