# -*- coding: utf-8 -*-
"""Build the updated rawData section with all July violations merged."""
import json

# All existing data + new July violations
# Format: {room: [{time, reason, location, action, penalty, product, phrase, ticket, isNew, isJuly}]}

data = {
  "小米官方手环直播间": [
    {"time":"2026-05-02","reason":"赠品活动信息与宣传不符","location":"直播口播","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"小米手环9 Pro","phrase":"赠品六选一","ticket":"76466358056411958309","isNew":False,"isJuly":False},
    {"time":"2026-05-24","reason":"售后服务不符","location":"直播画面","action":"已撤销","penalty":"警告(已撤销)","product":"-","phrase":"一年质保","ticket":"7643349423544205583","isNew":False,"isJuly":False},
    {"time":"2026-06-06","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"小米手环10Pro","phrase":"全国联保","ticket":"7648165811143688500","isNew":False,"isJuly":False},
    {"time":"2026-06-11","reason":"赠品活动信息与宣传不符","location":"直播画面","action":"预警","penalty":"下架商品+冻结佣金5%","product":"小米手环10Pro","phrase":"-","ticket":"7649934301415331248","isNew":True,"isJuly":False},
    {"time":"2026-07-21","reason":"违规买赠","location":"直播口播","action":"已撤销","penalty":"警告(已撤销，申诉成功)","product":"小米手环10Pro","phrase":"可以去挑一挑，选一选，喜欢哪个回来直接和我说","ticket":"7664714745605898506","isNew":True,"isJuly":True},
  ],
  "小米官方手表": [
    {"time":"2026-07-04","reason":"售后服务不符","location":"直播口播","action":"预警","penalty":"警告(申诉失败)","product":"-","phrase":"你就找那个附近有这个小米店或者小米之家的，你去，让店员帮你查验一下","ticket":"7658380441224773924","isNew":True,"isJuly":True},
    {"time":"2026-05-06","reason":"效果虚假","location":"直播口播","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播+关闭商品分享1天","product":"REDMI Watch","phrase":"五十米深度防水(夸大宣传)","ticket":"7536494293812658473","isNew":False,"isJuly":False},
    {"time":"2026-05-13","reason":"赠品活动信息与宣传不符","location":"直播画面","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"REDMI Watch","phrase":"-","ticket":"7539301178585292806","isNew":False,"isJuly":False},
    {"time":"2026-05-21","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"-","phrase":"一年质保","ticket":"76422923203391491190","isNew":False,"isJuly":False},
    {"time":"2026-06-07","reason":"赠品活动信息与宣传不符","location":"管理员评论","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"REDMI Watch","phrase":"凑单到手403起+教育优惠返20+额外腕带","ticket":"7648496881592516883","isNew":False,"isJuly":False},
    {"time":"2026-06-10","reason":"未使用平台福袋工具","location":"直播口播","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"REDMI Watch","phrase":"引导观众扣订单号到评论区抽奖","ticket":"76530149197860","isNew":False,"isJuly":False},
    {"time":"2026-06-23","reason":"款式/颜色/图案/形状不符","location":"直播画面","action":"预警","penalty":"下架商品+冻结佣金5%","product":"REDMI Watch 6","phrase":"宣传款式与详情页不一致","ticket":"7654339375326398245","isNew":True,"isJuly":False},
    {"time":"2026-07-04","reason":"违规买赠","location":"直播口播","action":"预警","penalty":"警告(超时未申诉)","product":"REDMI Watch 6","phrase":"你扣两个字，你扣一个金属，我这边给你备注上","ticket":"7658577744452043062","isNew":True,"isJuly":True},
    {"time":"2026-07-10","reason":"赠品活动信息与宣传不符","location":"直播画面","action":"预警","penalty":"警告(超时未申诉)","product":"-","phrase":"宣传赠品信息未在详情页体现","ticket":"7660783473019633920","isNew":True,"isJuly":True},
    {"time":"2026-07-11","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告(超时未申诉)","product":"-","phrase":"过度承诺售后服务（终身售后/永久免费等）","ticket":"7661119761891655982","isNew":True,"isJuly":True},
    {"time":"2026-07-13","reason":"违规买赠","location":"直播口播","action":"预警","penalty":"警告(申诉失败)","product":"-","phrase":"礼品腕带留在公屏上这边给您再配上一条","ticket":"7662018655999623450","isNew":True,"isJuly":True},
  ],
  "小米官方耳机直播间": [
    {"time":"2026-05-02","reason":"赠品活动信息与宣传不符","location":"直播口播","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"REDMI Buds Pro","phrase":"赠送耳机包","ticket":"76352147209546632040","isNew":False,"isJuly":False},
    {"time":"2026-05-13","reason":"违规买赠","location":"直播画面","action":"预警","penalty":"警告","product":"-","phrase":"买赠活动信息未在详情页展示","ticket":"7650559382040853760","isNew":True,"isJuly":False},
    {"time":"2026-05-16","reason":"赠品活动信息与宣传不符","location":"直播口播","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"REDMI Buds 8 Pro","phrase":"-","ticket":"75404001323196910625","isNew":False,"isJuly":False},
    {"time":"2026-05-18","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"-","phrase":"无忧质保","ticket":"75411094941515287305","isNew":False,"isJuly":False},
    {"time":"2026-05-23","reason":"售后服务不符","location":"直播口播","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"Xiaomi夹式耳机","phrase":"一年官方质保以及全国联保","ticket":"7642750111487148331","isNew":False,"isJuly":False},
    {"time":"2026-05-23","reason":"赠品活动信息与宣传不符","location":"直播口播","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"Xiaomi Buds","phrase":"-","ticket":"7642974458155474226","isNew":False,"isJuly":False},
    {"time":"2026-05-23","reason":"售后服务不符","location":"直播口播","action":"违规","penalty":"冻结佣金14,650.79元/30天","product":"Xiaomi夹式耳机","phrase":"一年质保和全国联保保质保证","ticket":"7642986916338123062","isNew":False,"isJuly":False},
    {"time":"2026-05-25","reason":"售后服务不符","location":"直播口播","action":"违规","penalty":"冻结佣金4,192.5元/30天+关闭商品分享3天","product":"Xiaomi夹式耳机","phrase":"线上线下都可以维修","ticket":"7543509078755770086","isNew":False,"isJuly":False},
    {"time":"2026-05-26","reason":"综合判定高风险(账号)","location":"达人账号","action":"违规","penalty":"提升风险保证金至3,000元/90天","product":"-","phrase":"-","ticket":"76440321333458865140","isNew":False,"isJuly":False},
    {"time":"2026-05-29","reason":"售后服务不符","location":"直播画面","action":"已撤销","penalty":"警告(已撤销)","product":"-","phrase":"品质质保","ticket":"7645066775767286054","isNew":False,"isJuly":False},
    {"time":"2026-07-26","reason":"违规买赠","location":"直播口播","action":"预警","penalty":"警告(申诉失败)","product":"Xiaomi Buds 6","phrase":"点个小关小注加粉粉群送手持风扇耳机包","ticket":"7666708955757805824","isNew":True,"isJuly":True},
  ],
  "小米手环10pro直播间": [
    {"time":"2026-05-27","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"便携式折叠衣架","phrase":"-","ticket":"7542513087310921218","isNew":False,"isJuly":False},
    {"time":"2026-06-07","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"小米手环10Pro","phrase":"全国联保","ticket":"7548406803645267658","isNew":False,"isJuly":False},
    {"time":"2026-06-07","reason":"售后服务不符","location":"直播文案","action":"预警","penalty":"警告","product":"-","phrase":"-","ticket":"7648621291297407270","isNew":False,"isJuly":False},
  ],
  "小米数码旗舰店": [
    {"time":"2026-05-02","reason":"赠品活动信息与宣传不符","location":"直播口播","action":"预警","penalty":"下架商品+冻结佣金5%+中断直播","product":"小米手环9 Pro","phrase":"-","ticket":"7635206695983235370","isNew":False,"isJuly":False},
    {"time":"2026-06-20","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"小米手环10Pro","phrase":"-","ticket":"7645124267600383931","isNew":True,"isJuly":False},
  ],
  "小米官旗手表直播间": [
    {"time":"2026-05-03","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"-","phrase":"-","ticket":"7649336590503633802","isNew":True,"isJuly":False},
    {"time":"2026-05-07","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"小米手环10Pro","phrase":"全国联保","ticket":"7648406303546257653","isNew":True,"isJuly":False},
    {"time":"2026-05-07","reason":"售后服务不符","location":"直播画面","action":"预警","penalty":"警告","product":"-","phrase":"-","ticket":"7648521291297407270","isNew":True,"isJuly":False},
    {"time":"2026-05-25","reason":"不当竞争","location":"直播画面","action":"预警","penalty":"警告","product":"-","phrase":"贬低第三方同类产品","ticket":"765545910472747432","isNew":True,"isJuly":False},
    {"time":"2026-06-11","reason":"诱导互动","location":"直播画面","action":"预警","penalty":"警告","product":"-","phrase":"以利益诱导用户评论/点赞互动","ticket":"7543943557177331746","isNew":True,"isJuly":False},
    {"time":"2026-06-28","reason":"诱导互动","location":"直播画面","action":"预警","penalty":"警告","product":"-","phrase":"以利益诱导用户互动","ticket":"7656231531917039318","isNew":True,"isJuly":False},
    {"time":"2026-07-07","reason":"诱导互动","location":"直播口播","action":"预警","penalty":"警告(超时未申诉)","product":"-","phrase":"点个小关小注让后台助理给你加急发货","ticket":"7659753872462430504","isNew":True,"isJuly":True},
    {"time":"2026-07-09","reason":"售后服务不符","location":"直播口播","action":"预警","penalty":"警告(超时未申诉)","product":"-","phrase":"官方全店保质保终身","ticket":"7660197886068441363","isNew":True,"isJuly":True},
    {"time":"2026-07-09","reason":"违规买赠","location":"直播口播","action":"预警","penalty":"警告(超时未申诉)","product":"-","phrase":"想要s五的老板，评论备注，耳机音箱表带三选二","ticket":"7660357122517532934","isNew":True,"isJuly":True},
    {"time":"2026-07-23","reason":"售后服务不符","location":"直播口播","action":"已撤销","penalty":"警告(已撤销，申诉成功)","product":"-","phrase":"这是咱们能够去给你做一个官方的一个终身保障","ticket":"7665639986813255999","isNew":True,"isJuly":True},
  ],
}

# Compute stats
all_records = []
for room, items in data.items():
    for v in items:
        v['room'] = room
        all_records.append(v)

total = len(all_records)
effective = sum(1 for v in all_records if v['action'] != '已撤销')
revoked = sum(1 for v in all_records if v['action'] == '已撤销')

# July-specific
july_records = [v for v in all_records if v.get('isJuly')]
july_total = len(july_records)
july_effective = sum(1 for v in july_records if v['action'] != '已撤销')
july_revoked = sum(1 for v in july_records if v['action'] == '已撤销')
july_appeal_fail = sum(1 for v in july_records if '申诉失败' in v.get('penalty', ''))
july_appeal_timeout = sum(1 for v in july_records if '超时未申诉' in v.get('penalty', ''))

from collections import Counter
july_reasons = Counter(v['reason'] for v in july_records)
july_rooms = Counter(v['room'] for v in july_records)

print(f"=== UPDATED STATS ===")
print(f"Total violations: {total} (effective: {effective}, revoked: {revoked})")
print(f"July violations: {july_total} (effective: {july_effective}, revoked: {july_revoked})")
print(f"July room distribution: {dict(july_rooms)}")
print(f"July reason distribution: {dict(july_reasons)}")
print(f"July appeal stats: 申诉失败={july_appeal_fail}, 超时未申诉={july_appeal_timeout}")
print(f"Total rooms: {len(data)}")

# Save the rawData as JS for the HTML
js_data = "const rawData = " + json.dumps(data, ensure_ascii=False, indent=2) + ";"
with open(r'C:\Users\Administrator\Desktop\小米手环直播间销量分析\违规情况\updated_rawdata.js', 'w', encoding='utf-8') as f:
    f.write(js_data)
print("\nUpdated rawData JS saved.")
