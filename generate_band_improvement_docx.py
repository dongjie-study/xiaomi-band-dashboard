"""
Generate Executive Proposal for Xiaomi Band Improvement - For Boss Review
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

def add_h(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.name = '微软雅黑'; run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    return h

def add_p(doc, text, bold=False, size=11, color=None, align=None, space=4):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = '微软雅黑'; run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run.font.size = Pt(size); run.bold = bold
    if color: run.font.color.rgb = RGBColor(*color)
    if align is not None: p.alignment = align
    p.paragraph_format.space_after = Pt(space)
    p.paragraph_format.space_before = Pt(1)
    return p

def add_kv(doc, key, value, size=10.5):
    p = doc.add_paragraph()
    r1 = p.add_run(key); r1.bold = True; r1.font.size = Pt(size)
    r1.font.name = '微软雅黑'; r1._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    r2 = p.add_run(value); r2.font.size = Pt(size)
    r2.font.name = '微软雅黑'; r2._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    p.paragraph_format.space_after = Pt(2)

def set_shading(cell, color):
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>'))

def fmt_cell(cell, text, bold=False, size=9, color=None, bg=None, align='center'):
    cell.text = ''
    p = cell.paragraphs[0]
    run = p.add_run(text)
    run.font.name = '微软雅黑'; run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run.font.size = Pt(size); run.bold = bold
    if color: run.font.color.rgb = RGBColor(*color)
    p.alignment = {'center': WD_ALIGN_PARAGRAPH.CENTER, 'left': WD_ALIGN_PARAGRAPH.LEFT}[align]
    if bg: set_shading(cell, bg)
    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)

def make_table(doc, headers, rows, col_widths=None, hdr_color='1E90FF'):
    t = doc.add_table(rows=1+len(rows), cols=len(headers))
    t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        fmt_cell(t.rows[0].cells[i], h, bold=True, size=9, color=(255,255,255), bg=hdr_color)
    for r, row_data in enumerate(rows):
        bg = 'F5F7FA' if r%2==0 else None
        for c, val in enumerate(row_data):
            fmt_cell(t.rows[r+1].cells[c], str(val), size=9, bg=bg)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in t.rows: row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t

def build_report():
    history = load_data()
    june = [d for d in history if d['date'].startswith('2026-06')]

    # Calc stats
    band_total = 0; band_rev = 0
    our_band = 0; liangmi_band = 0
    our_room_daily = 0; comp_room_daily = 0; days_count = 0

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
            if rname == '小米官方手环直播间':
                days_count += 1
                for pname, pinfo in rinfo.get('products', {}).items():
                    if any(bp in str(pname) for bp in ['手环','Band']):
                        our_room_daily += pinfo['orders']
            if rname == '小米手环':
                for pname, pinfo in rinfo.get('products', {}).items():
                    if any(bp in str(pname) for bp in ['手环','Band']):
                        comp_room_daily += pinfo['orders']

    our_avg = our_room_daily // days_count
    comp_avg = comp_room_daily // days_count
    our_share = our_band / band_total * 100
    liangmi_share = liangmi_band / band_total * 100

    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21); sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.5); sec.bottom_margin = Cm(2)
    sec.left_margin = Cm(2.5); sec.right_margin = Cm(2.5)

    style = doc.styles['Normal']
    style.font.name = '微软雅黑'; style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    # ============================================================
    # COVER
    # ============================================================
    for _ in range(4): doc.add_paragraph()

    # Red confidential banner
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('■ 内 部 方 案 · 请 勿 外 传 ■')
    r.font.size = Pt(9); r.font.color.rgb = RGBColor(200,50,50); r.bold = True
    r.font.name = '微软雅黑'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    doc.add_paragraph()

    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('小米手环直播间')
    r.font.size = Pt(18); r.font.color.rgb = RGBColor(60,60,60)
    r.font.name = '微软雅黑'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('销量提升方案')
    r.font.size = Pt(28); r.bold = True; r.font.color.rgb = RGBColor(255,105,0)
    r.font.name = '微软雅黑'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('—— 聚焦核心直播间，单点突破，拉动全盘 ——')
    r.font.size = Pt(11); r.font.color.rgb = RGBColor(130,130,130)
    r.font.name = '微软雅黑'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    for _ in range(4): doc.add_paragraph()

    # Meta info
    info = [
        ('呈报对象：', '管理层'),
        ('编制部门：', '直播运营部'),
        ('数据周期：', '2026年6月1日 - 6月30日'),
        ('报告日期：', '2026年7月2日'),
    ]
    for k, v in info:
        add_kv(doc, k, v)

    doc.add_page_break()

    # ============================================================
    # EXECUTIVE SUMMARY
    # ============================================================
    add_h(doc, '核心摘要', level=1)

    # Big number highlight
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(12)
    r = p.add_run(f'{our_avg}')
    r.font.size = Pt(48); r.bold = True; r.font.color.rgb = RGBColor(255,105,0)
    r.font.name = '微软雅黑'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run(f'我们最好的手环直播间，日均只卖 {our_avg} 单')
    r2.font.size = Pt(14); r2.bold = True
    r2.font.name = '微软雅黑'; r2._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    p3 = doc.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = p3.add_run(f'竞对同等定位直播间日均 {comp_avg} 单，是我们的 2 倍')
    r3.font.size = Pt(12); r3.font.color.rgb = RGBColor(231,76,60)
    r3.font.name = '微软雅黑'; r3._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    doc.add_paragraph()

    make_table(doc,
        ['指标', '我们（6月）', '竞对（良米）', '差距', '提升后预期'],
        [
            ['核心直播间日单量', f'{our_avg} 单', f'{comp_avg} 单', f'差 {comp_avg-our_avg} 单/天', '450→600 单/天'],
            ['手环全渠道市占率', f'{our_share:.1f}%', f'{liangmi_share:.1f}%', f'落后 {liangmi_share-our_share:.1f} 个点', '40%→45%'],
            ['月手环订单总量', f'{our_band:,} 单', f'{liangmi_band:,} 单', f'差 {liangmi_band-our_band:,} 单/月', '26,000→32,000 单/月'],
        ],
        [3, 2.5, 2.5, 3, 3.5], 'E74C3C')

    add_p(doc, '▎核心结论', bold=True, size=12, color=(255,105,0))
    add_p(doc, f'我们6间直播间手环月销 {our_band:,} 单，其中47%来自"小米官方手环直播间"。这个核心直播间日均仅 {our_avg} 单，而竞对同类直播间日均 {comp_avg} 单。不需要做6个直播间，只需要把这一间拉到竞对水平，我司整体市占率就能从 {our_share:.1f}% 跳升到 45%+，月增约 6,000 单手环订单。', size=10.5)

    add_p(doc, '▎投入产出预估', bold=True, size=12, color=(255,105,0))

    make_table(doc,
        ['投入项', '月增成本', '预期月增收', 'ROI'],
        [
            ['千川投放增量', '+¥60,000/月（从¥11万→¥17万）', '—', '—'],
            ['视频团队扩充', '+1人，约¥12,000/月', '—', '—'],
            ['抖加预算', '+¥20,000/月', '—', '—'],
            ['合计投入', '≈¥92,000/月', '6,000单×¥350均价=¥210万', '1 : 23'],
        ],
        [3.5, 3.5, 4, 2.5], '1DA85C')

    add_p(doc, '投入约9.2万/月，预期增收210万/月，ROI约1:23。该方案低风险、高确定性、本周即可启动。', bold=True, size=11, color=(29,168,92))

    doc.add_page_break()

    # ============================================================
    # SITUATION ANALYSIS
    # ============================================================
    add_h(doc, '一、现状与问题', level=1)

    add_h(doc, '1.1 市场格局', level=2)
    add_p(doc, f'6月手环全渠道直播间总订单 {band_total:,} 单，销售额 ¥{band_rev/10000:.0f} 万。各团队份额如下：', size=10.5)

    make_table(doc,
        ['团队', '直播间数', '手环月订单', '市占率', '日均单直播间产出', '定位'],
        [
            ['良米（竞对）', '10间', f'{liangmi_band:,}', f'{liangmi_share:.1f}%', f'{liangmi_band//10//30} 单/间/天', '市场领先者'],
            ['我司', '6间', f'{our_band:,}', f'{our_share:.1f}%', f'{our_band//6//30} 单/间/天', '追赶者'],
            ['机械空间', '2间', '10,511', '18.2%', '175 单/间/天', '国补走量型'],
            ['纵横', '1间', '486', '0.8%', '16 单/间/天', '边缘'],
        ],
        [2.5, 2, 2.5, 1.8, 3.5, 2.5])

    add_h(doc, '1.2 核心问题定位', level=2)

    add_p(doc, '问题不在直播间数量（我们6间 vs 良米10间），而在单直播间产出效率。', size=10.5)
    add_p(doc, '三个关键发现：', bold=True, size=11)

    findings = [
        f'【最大问题】我司头牌直播间"小米官方手环直播间"日均 {our_avg} 单，竞对"小米手环"直播间日均 {comp_avg} 单。同一个手环品类，同一个平台，我们只有竞对的 {our_avg/comp_avg*100:.0f}%。这不是流量问题，是直播间运营效率问题。',
        f'【最大机会】手环10 Pro（均价¥395）和手环10（均价¥288）两个品贡献了98%的订单。产品极度集中，意味着视频素材、话术、投放都可以高度聚焦，不需要分散资源。',
        f'【最快杠杆】该直播间贡献了我司47%的手环订单，它的提升可以直接拉动整体市占率。把这一个直播间做好，效果大于同时折腾6个直播间。',
    ]
    for i, f in enumerate(findings):
        add_p(doc, f, size=10.5)

    doc.add_page_break()

    # ============================================================
    # THE PLAN
    # ============================================================
    add_h(doc, '二、提升方案（三个抓手）', level=1)

    add_p(doc, '整体逻辑：视频/投放做大流量入口 → 话术提升转化率 → 视觉强化信任和停留。三管齐下，聚焦"小米官方手环直播间"这一个核心阵地。', bold=True, size=11, color=(255,105,0))

    # ---- 抓手1 ----
    add_h(doc, '抓手一：视频放量 + 千川加投（解决"没人进"的问题）', level=2)

    add_p(doc, '▎为什么这是第一优先？', bold=True, size=11, color=(255,105,0))
    add_p(doc, '直播间的订单 = 进房人数 × 转化率 × 客单价。当前核心直播间转化率和客单价正常，问题出在进房人数不够。进房人数来自两个渠道：视频引流（免费）+ 千川投放（付费）。目前两个都没做够。', size=10.5)

    add_p(doc, '▎具体措施', bold=True, size=11, color=(29,168,92))

    make_table(doc,
        ['措施', '现状', '目标', '执行要点'],
        [
            ['视频日产量', '约3-5条', '10条/天', '手机拍摄即可，15-25秒/条。5种类型轮换：开箱展示/使用场景/价格促销/功能测评/热点借势'],
            ['千川周投放', '¥27,000', '¥43,000', '重点投"抖音号主页素材"（当前ROI 15.7最优）。AIGC占比从36%降至15%'],
            ['素材赛马', '无系统机制', '每周两轮', '每批5条新素材同时上线¥200/条，24h后保留ROI>10的，淘汰ROI<5的'],
            ['抖加助推', '几乎没有', '¥5,000/周', '自然播放>3,000的视频立即¥200助推，撬动自然流量推荐'],
            ['热点追投', '没有', '每周至少跟2个', '日常监控抖音热点宝，出现#运动打卡 #数码好物 等话题4小时内跟拍发布'],
        ],
        [3, 2.5, 2.5, 7], '1E90FF')

    add_p(doc, '▎预期效果', bold=True, size=11)
    add_p(doc, '手环视频周播放量从88万提升至150万（+70%），日均进直播间人数提升40-50%。', size=10.5)

    # ---- 抓手2 ----
    add_h(doc, '抓手二：话术标准化（解决"进来留不住"的问题）', level=2)

    add_p(doc, '▎为什么这是第二优先？', bold=True, size=11, color=(255,105,0))
    add_p(doc, f'我们核心直播间均价¥348，竞对¥357——价格差不多，但我们单量只有竞对一半。说明用户进来了但没被转化。核心原因是缺少标准化逼单流程，靠主播个人发挥，效果不稳定。', size=10.5)

    add_p(doc, '▎"10分钟逼单循环"标准流程', bold=True, size=11, color=(29,168,92))

    make_table(doc,
        ['阶段', '时长', '主播要做什么', '关键话术（背下来）'],
        [
            ['开场钩子', '0-30秒', '喊住刷进来的人，给停留理由', '"刚进来的别走！手环10 Pro今天破价，扣1给你看底价"（每3-5分钟一轮）'],
            ['产品展示', '30秒-3分钟', '手腕实戴，亮屏滑动，展示功能', '"你看这个陶瓷质感，抬手就亮，昨晚的睡眠数据一目了然"'],
            ['卖点轰炸', '3-6分钟', '集中讲3个核心卖点', '"续航14天不用充电、独立GPS跑步不带手机、150+运动模式——399全搞定"'],
            ['价格对比', '6-8分钟', '建立价格超值感', '"官网449一分不少，今天到手399还送49块钱原装表带，相当于手环才350"'],
            ['逼单收网', '8-10分钟', '制造紧迫感，促成下单', '"限量100台出了82台了，最后18台。3号链接直接拍，拍完恢复原价"→回到开场钩子循环'],
        ],
        [2, 1.8, 4.5, 7], '1DA85C')

    add_p(doc, '另外，打印一张"异议处理速查卡"贴在主播电脑旁：', size=10.5)
    for x in [
        '"太贵了" → "一天5毛5，一杯奶茶钱换14天续航"',
        '"和10有什么区别" → "Pro有独立GPS，跑步不用带手机，多花100块值"',
        '"再看看" → "先拍下不付款，15分钟内有效，等会可能没了"',
    ]: add_p(doc, f'    {x}', size=10)

    add_p(doc, '▎预期效果', bold=True, size=11)
    add_p(doc, '转化率提升20-30%，核心直播间日均从317单→450单+。', size=10.5)

    # ---- 抓手3 ----
    add_h(doc, '抓手三：直播间视觉优化（解决"看着不专业"的问题）', level=2)

    add_p(doc, '▎竞对视觉对比', bold=True, size=11, color=(255,105,0))
    add_p(doc, '分析竞对"小米手环"直播间（日均645单），发现三个视觉差异：① 价格信息超大超醒目，3秒传达 ② 主播全程佩戴手环动态演示 ③ 画面简洁，用户注意力聚焦产品。我们的直播间在这三点上都有差距。', size=10.5)

    add_p(doc, '▎立即调整项（0成本，本周完成）', bold=True, size=11, color=(29,168,92))

    make_table(doc,
        ['调整项', '具体做法', '预期提升'],
        [
            ['放大价格信息', '底部价格条字体放大3倍，红底黄字，写"到手¥3XX | 赠表带 | 官方正品"', '用户决策时间缩短，点击率+15%'],
            ['强制佩戴展示', '主播全程手腕佩戴手环，每10分钟展示1次抬手亮屏+通知提醒+APP数据', '信任感+停留时长+20%'],
            ['清理画面', '桌面只保留手环+充电座+iPad展示APP界面，其余杂物全部清走', '产品焦点突出，视觉专业感提升'],
            ['增加紧迫浮窗', '逼单环节画面中央弹出"仅剩X台 | 倒计时X分钟"，用OBS叠加', '逼单环节转化率+30%'],
            ['轮播活动标签', '右上角轮播"今日特惠""限量赠品""官方正品"，每15分钟手动更新', '新进用户快速感知利益点'],
        ],
        [3, 7.5, 4], '1DA85C')

    doc.add_page_break()

    # ============================================================
    # EXECUTION
    # ============================================================
    add_h(doc, '三、执行计划与里程碑', level=1)

    add_h(doc, '3.1 本周（7月第一周）启动清单', level=2)

    make_table(doc,
        ['#', '事项', '负责', '完成标准', '截止'],
        [
            ['1', '视频日产从3-5条提升至10条', '视频组', '连续3天达标', '周三'],
            ['2', '千川手环预算调整至¥43,000/周', '投放', '后台已调整', '周二'],
            ['3', '新建5条素材开启第一轮赛马', '投放+视频', '24h出首轮数据', '周三'],
            ['4', '主播完成"10分钟逼单循环"培训', '运营+主播', '全员脱稿通过', '周四'],
            ['5', '异议处理速查卡打印上墙', '运营', '直播间可见', '周二'],
            ['6', '底部价格条更换为大字版', '设计', '开播前完成', '周二'],
            ['7', '直播间桌面清理+产品陈列规范', '主播', '开播前拍照确认', '周二'],
            ['8', '抖加助推预算¥5,000/周到账', '投放', '可随时使用', '周二'],
            ['9', '右上角活动标签轮播上线', '运营', '每15分钟手动刷新', '周二'],
            ['10', '建立每日数据复盘机制', '全员', '下播后30分钟内发群', '每天'],
        ],
        [0.8, 5.2, 2, 3.5, 1.5], '1E90FF')

    add_h(doc, '3.2 月度里程碑', level=2)

    make_table(doc,
        ['时间节点', '里程碑', '验收标准'],
        [
            ['7月第1周', '完成所有基础整改（话术+视觉+视频产量）', '10项清单全部打勾'],
            ['7月第2周', '首轮数据验证', '视频周播放量>100万，核心直播间日均>350单'],
            ['7月第3周', '优化迭代（赛马胜出素材追投+话术打磨）', '视频周播放量>130万，核心直播间日均>400单'],
            ['7月第4周', '月度总结', '视频周播放量>150万，核心直播间日均>450单，手环市占率>40%'],
        ],
        [2.5, 4.5, 7], 'FF6900')

    add_h(doc, '3.3 资源需求', level=2)

    make_table(doc,
        ['资源', '当前', '需求', '月增量成本', '说明'],
        [
            ['千川投放', '¥11万/月', '¥17万/月', '+¥6万', '按ROI 14计算，增量投放带来¥84万增量成交'],
            ['抖加', '零星', '¥2万/月', '+¥2万', '主要用于爆款助推和粉丝增长'],
            ['视频人员', '1-2人', '3人（+1剪辑）', '+¥1.2万', '支撑日产10条视频的剪辑量'],
            ['合计', '—', '—', '≈¥9.2万/月', '预期增量月收入¥210万，ROI约1:23'],
        ],
        [2.2, 2, 2.2, 2.5, 5.5], '1DA85C')

    doc.add_page_break()

    # ============================================================
    # TARGETS
    # ============================================================
    add_h(doc, '四、目标与考核', level=1)

    add_p(doc, '围绕三个核心KPI考核，不贪多：', size=10.5)

    make_table(doc,
        ['核心KPI', '6月基线', '7月目标', '8月目标', '考核方式'],
        [
            ['核心直播间日均订单', f'{our_avg} 单', '450 单 (+42%)', '600 单 (+89%)', '每日播报，周度复盘'],
            ['手环视频周播放量', '88 万', '150 万 (+70%)', '250 万 (+184%)', '每周一统计'],
            ['我司手环市占率', f'{our_share:.1f}%', '40%+', '45%+', '月度核算'],
        ],
        [3, 2.5, 3, 3, 3.5], 'FF6900')

    add_p(doc, '')
    add_p(doc, f'一句话总结：6间直播间不用全动，集中火力把"小米官方手环直播间"这一个核心阵地的日均单量从 {our_avg} 拉到 450+，市占率就能从 {our_share:.0f}% 突破 40%。投入可控、路径清晰、本周就能启动。', bold=True, size=12, color=(255,105,0))

    doc.add_paragraph()
    doc.add_paragraph()
    add_p(doc, '— 方案完 —', size=10, color=(180,180,180), align=WD_ALIGN_PARAGRAPH.CENTER)
    add_p(doc, '内部资料 · 请勿外传', size=9, color=(200,200,200), align=WD_ALIGN_PARAGRAPH.CENTER)

    output_path = os.path.join(DATA_DIR, '小米手环直播间提升方案（呈报版）.docx')
    doc.save(output_path)
    print(f'Done: {output_path}')

if __name__ == '__main__':
    build_report()
