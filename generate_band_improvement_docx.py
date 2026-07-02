"""
Generate Xiaomi Band Urgent Action Plan - Concise & Actionable
"""
import json, os
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def load_data():
    with open(os.path.join(DATA_DIR, 'sales_analysis', 'history.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

def get_team(rname):
    r = str(rname)
    if '小米官方手表直播号' == r: return '纵横'
    if '小米智能穿戴国补号' == r or '小米智能穿戴授权号' == r: return '机械空间'
    if any(kw in r for kw in ['小米官方','小米数码旗舰店','小米手环10Pro直播间','小米官旗手表直播间']): return '我司'
    return '良米'

def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.name = '微软雅黑'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    return h

def add_p(doc, text, bold=False, size=11, color=None, align=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = '微软雅黑'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run.font.size = Pt(size)
    run.bold = bold
    if color: run.font.color.rgb = RGBColor(*color)
    if align is not None: p.alignment = align
    p.paragraph_format.space_after = Pt(4)
    return p

def add_bullet(doc, text, size=10.5, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    p.clear()
    if bold_prefix:
        r1 = p.add_run(bold_prefix)
        r1.bold = True
        r1.font.name = '微软雅黑'
        r1._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        r1.font.size = Pt(size)
        r2 = p.add_run(text)
        r2.font.name = '微软雅黑'
        r2._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        r2.font.size = Pt(size)
    else:
        run = p.add_run(text)
        run.font.name = '微软雅黑'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        run.font.size = Pt(size)
    return p

def set_cell_shading(cell, color):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def fmt_cell(cell, text, bold=False, size=9, color=None, bg=None):
    cell.text = ''
    p = cell.paragraphs[0]
    run = p.add_run(text)
    run.font.name = '微软雅黑'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run.font.size = Pt(size)
    run.bold = bold
    if color: run.font.color.rgb = RGBColor(*color)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if bg: set_cell_shading(cell, bg)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)

def make_table(doc, headers, rows, col_widths=None, header_color='FF6900'):
    t = doc.add_table(rows=1+len(rows), cols=len(headers))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        fmt_cell(t.rows[0].cells[i], h, bold=True, size=9, color=(255,255,255), bg=header_color)
    for r, row_data in enumerate(rows):
        for c, val in enumerate(row_data):
            fmt_cell(t.rows[r+1].cells[c], str(val), size=9, bg='FFF7ED' if r%2==0 else None)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in t.rows: row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t

def build_report():
    history = load_data()
    june = [d for d in history if d['date'].startswith('2026-06')]

    # Calc band stats
    band_total = 0; band_rev = 0
    our_band = 0; liangmi_band = 0; jixie_band = 0
    our_room_orders = 0; comp_room_orders = 0

    for d in june:
        for pname, pinfo in d.get('products', {}).items():
            if any(bp in str(pname) for bp in ['手环','Band']):
                band_total += pinfo['orders']
                band_rev += pinfo['revenue']
        for rname, rinfo in d.get('rooms', {}).items():
            t = get_team(rname)
            for pname, pinfo in rinfo.get('products', {}).items():
                if any(bp in str(pname) for bp in ['手环','Band']):
                    if t == '我司': our_band += pinfo['orders']
                    elif t == '良米': liangmi_band += pinfo['orders']
                    elif t == '机械空间': jixie_band += pinfo['orders']
            if rname == '小米官方手环直播间':
                for pname, pinfo in rinfo.get('products', {}).items():
                    if any(bp in str(pname) for bp in ['手环','Band']):
                        our_room_orders += pinfo['orders']
            if rname == '小米手环':
                for pname, pinfo in rinfo.get('products', {}).items():
                    if any(bp in str(pname) for bp in ['手环','Band']):
                        comp_room_orders += pinfo['orders']

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21); section.page_height = Cm(29.7)
    section.top_margin = Cm(2); section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5); section.right_margin = Cm(2.5)

    style = doc.styles['Normal']
    style.font.name = '微软雅黑'; style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    # ===== COVER =====
    for _ in range(5): doc.add_paragraph()
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run('小米手环 · 紧急提升方案')
    r.font.size = Pt(26); r.bold = True; r.font.color.rgb = RGBColor(255,105,0)
    r.font.name = '微软雅黑'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    doc.add_paragraph()
    s = doc.add_paragraph(); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = s.add_run('只讲重点 · 立即能落地 · 本周就开干')
    r.font.size = Pt(13); r.font.color.rgb = RGBColor(120,120,120)
    r.font.name = '微软雅黑'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    doc.add_paragraph(); doc.add_paragraph()
    for line in [f'数据周期：2026年6月（30天）| 报告日期：7月2日']:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(line); r.font.size = Pt(10); r.font.color.rgb = RGBColor(150,150,150)
        r.font.name = '微软雅黑'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    doc.add_page_break()

    # ===== 1. 最核心的一个数字 =====
    add_heading(doc, '一、一个数字说明一切', level=1)

    add_p(doc, f'6月手环总订单 {band_total:,} 单，我们占 {our_band/band_total*100:.1f}%，良米占 {liangmi_band/band_total*100:.1f}%。', bold=True, size=12)
    add_p(doc, '但！看单直播间产出：', size=11)

    make_table(doc,
        ['', '直播间', '日均手环订单', '月总手环订单', '差 距'],
        [
            ['🥇 竞对', '良米 - 小米手环', f'{comp_room_orders//30} 单/天', f'{comp_room_orders} 单', '——'],
            ['🥈 我方', '小米官方手环直播间', f'{our_room_orders//30} 单/天', f'{our_room_orders} 单', f'落后 {(comp_room_orders-our_room_orders)//30} 单/天'],
        ],
        [3, 4, 3, 3, 4], 'E74C3C')

    add_p(doc, '结论：光这一个直播间，每天比竞对少卖 328 单，一个月差 9,849 单。把这个直播间拉到竞对水平，我司市占率直接从35%跳升到45%+。', bold=True, size=11, color=(231,76,60))

    add_heading(doc, '二、三件事，按紧急度排', level=1)

    # ===== 2. 视频+投放 =====
    add_heading(doc, '🥇 第一紧急：视频量产 + 千川追投（本周启动）', level=2)

    add_p(doc, '为什么排第一？因为最快见效。视频→播放量→进直播间→成交，这个链路今天优化明天就出数据。', size=10.5)

    add_p(doc, '▎现在的问题：', bold=True, size=11, color=(255,105,0))
    for x in [
        '手环视频日产不足5条，良米日产估计15条+',
        '千川周消耗仅¥27,434（手环专属），良米预估¥50,000+',
        'AIGC素材占比过高(36%)，真人实拍素材不够',
        '爆款视频（播放>10万）几乎没有',
    ]: add_bullet(doc, x)

    add_p(doc, '▎本周立刻做：', bold=True, size=11, color=(29,168,92))

    make_table(doc,
        ['动作', '具体做法', '频次/量', '预期效果'],
        [
            ['1. 视频量产', '手机拍摄即可：①手环10 Pro开箱特写(15s) ②手腕实戴展示(15s) ③价格优惠口播(15s) ④功能实测对比(20s)', '每天10条', '3天内播放量翻倍'],
            ['2. 千川加投', '手环专属预算从¥27K→¥43K/周。重点投"抖音号主页素材"（ROI 15.7最高）', '每周¥43,000', '手环订单+20%'],
            ['3. 素材赛马', '每天新建5条素材同时投放¥200/条，24h后看ROI，ROI>10的保留加投，<5的关停', '每天一轮', '找到3-5条爆款素材'],
            ['4. 抖加助推', '自然播放>3000且互动率>5%的视频，立即¥200抖加助推进直播间', '随爆随投', '放大爆款10x'],
        ],
        [2.5, 6.5, 2.5, 3.5], '1DA85C')

    add_p(doc, '特别提醒：视频不需要专业设备！手机拍就行，关键是"前3秒必须有钩子"（价格/好奇心/痛点），时长15-25秒。', bold=True, size=10.5, color=(231,76,60))

    # ===== 3. 话术 =====
    add_heading(doc, '🥈 第二紧急：话术三板斧（本周落地）', level=2)

    add_p(doc, '为什么排第二？话术是转化率的核心。用户进来了，能不能成交，就看主播怎么说。', size=10.5)

    add_p(doc, '▎现在的问题：', bold=True, size=11, color=(255,105,0))
    for x in [
        '官方手环直播间均价¥348 vs 竞对"小米手环"均价¥357 → 我们价格更低但单量只有人家一半，说明转化话术有差距',
        '高峰时段仅15单/小时 → 流量承接能力弱',
        '缺少标准化的逼单流程，依赖主播个人发挥',
    ]: add_bullet(doc, x)

    add_p(doc, '▎本周立刻做：', bold=True, size=11, color=(29,168,92))

    add_p(doc, '板斧一：开场30秒钩子（留住人）', bold=True, size=11)
    for x in [
        '"刚进来的宝宝别走！手环10 Pro今天破价，扣1给你看底价"（每5分钟喊一次）',
        '"昨天600多人抢到了，今天补了100台，扣1的优先安排"（制造稀缺）',
    ]: add_bullet(doc, x)

    add_p(doc, '板斧二：10分钟逼单循环（转化人）', bold=True, size=11)
    for x in [
        '0-2分钟：展示产品（手腕实戴，开屏幕，滑功能）',
        '2-5分钟：讲3个核心卖点（续航14天/GPS/150+运动模式）',
        '5-8分钟：价格对比轰炸（"官网¥449→今天¥399，还送¥49表带"）',
        '8-10分钟：倒计时逼单（"还剩最后X台，3号链接直接拍"）→ 然后循环',
    ]: add_bullet(doc, x)

    add_p(doc, '板斧三：异议处理速查卡（搞定犹豫的人）', bold=True, size=11)
    for x in [
        '"太贵了" → "一天5毛5，一杯奶茶钱换14天续航，哪里贵了哥哥"',
        '"和10有什么区别" → "Pro有独立GPS跑步不用带手机，多¥100值得"',
        '"再看看" → "先拍下不付款，15分钟内有效。过会儿可能真没了"',
    ]: add_bullet(doc, x)

    # ===== 4. 视觉 =====
    add_heading(doc, '🥉 第三紧急：直播间视觉调整（本周完成）', level=2)

    add_p(doc, '为什么排第三？视觉影响停留时长和信任感，但改动成本低、见效快。', size=10.5)

    add_p(doc, '▎竞对良米"小米手环"直播间的视觉我们分析了，3个差异：', bold=True, size=11, color=(255,105,0))
    for x in [
        '价格贴片超大超醒目，3秒内看清优惠 → 我们的价格信息不够突出',
        '主播全程佩戴手环，动态展示通知/数据 → 我们是静态展示多',
        '画面简洁纯色背景，注意力集中在产品 → 我们画面元素偏杂',
    ]: add_bullet(doc, x)

    add_p(doc, '▎本周立刻改：', bold=True, size=11, color=(29,168,92))

    make_table(doc,
        ['改什么', '怎么改', '为什么'],
        [
            ['底部价格条', '增大3倍字体，红底黄字，写"到手¥3XX | 赠原装表带 | 官方直播间"', '用户3秒内看清价格和利益点'],
            ['右上角活动标签', '加"今日特惠""限量赠品"轮播标签，每15分钟手动刷新', '制造紧迫感和新鲜感'],
            ['主播佩戴要求', '强制要求：主播全程佩戴手环，每10分钟至少展示1次抬手亮屏/通知提醒', '让用户"看到就想戴"'],
            ['清理画面杂物', '桌面只保留手环+充电座+iPad（展示APP），其余全部清走', '注意力100%在产品和主播'],
            ['增加倒计时浮窗', '逼单环节，画面中央出现"最后X台 | 倒计时X分钟"浮窗', '逼单转化率至少+30%'],
        ],
        [3, 7, 5], '1DA85C')

    # ===== 5. 执行检查清单 =====
    doc.add_page_break()
    add_heading(doc, '三、本周执行检查清单', level=1)

    add_p(doc, '以下所有项本周五之前必须完成，已完成打✓：', bold=True, size=11)

    make_table(doc,
        ['序号', '事项', '负责人', '完成标准', '截止'],
        [
            ['1', '视频日产从5条提升到10条', '视频组', '连续3天日产10条+', '本周三'],
            ['2', '千川手环预算调整到¥43K/周', '投放组', '后台预算已调整', '本周二'],
            ['3', '新建5条素材开启赛马测试', '投放+视频', '5条全部上线，24h后出第一轮数据', '本周三'],
            ['4', '主播话术培训（三板斧）', '主播+运营', '全部主播能脱稿讲完10分钟逼单循环', '本周四'],
            ['5', '异议处理速查卡打印张贴', '运营', '直播间桌面/电脑旁可见', '本周二'],
            ['6', '底部价格条更换（大字版）', '设计', '直播间开播时已更换', '本周二'],
            ['7', '右上角活动标签轮播上线', '运营', '每15分钟手动更新一次', '本周二'],
            ['8', '直播间桌面清理+产品陈列规范', '主播', '开播前拍照发群确认', '本周二'],
            ['9', '抖加助推预算¥5,000/周到账', '投放组', '账户余额可查', '本周二'],
            ['10', '每日数据复盘（视频播放+直播间转化）', '全员', '每天下播后30分钟内发群', '每天'],
        ],
        [1, 5.5, 2, 4, 2], '1E90FF')

    # ===== 6. 目标 =====
    add_heading(doc, '四、7月目标（就盯这3个数）', level=1)

    make_table(doc,
        ['指标', '6月实际', '7月目标', '怎么达到'],
        [
            ['官方手环间日均订单', '317单/天', '450单/天 (+42%)', '话术升级+视觉整改+千川引流'],
            ['手环视频周播放量', '88万', '150万 (+70%)', '日产10条+素材赛马+抖加助推'],
            ['我司手环市占率', '35.3%', '40%+', '核心直播间突破拉动整体份额'],
        ],
        [3.5, 2.5, 3.5, 6], 'FF6900')

    add_p(doc, '')
    add_p(doc, '一句话总结：把"小米官方手环直播间"的日均单量从317拉到450，就这一件事做到了，市占率就能从35%跳到40%。其他都是辅助。', bold=True, size=12, color=(255,105,0))

    doc.add_paragraph()
    add_p(doc, '— 报告完 —', size=10, color=(180,180,180), align=WD_ALIGN_PARAGRAPH.CENTER)

    output_path = os.path.join(DATA_DIR, '小米手环直播间提升方案_v2.docx')
    doc.save(output_path)
    print(f'Done: {output_path}')

if __name__ == '__main__':
    build_report()
