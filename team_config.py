"""
Unified team classification configuration.
Single source of truth — all other scripts should import from here.
"""
import os
import json

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# === Primary Team Mapping (from daily_update.py) ===
# Room name → Team name. Anything not listed defaults to '良米'.
TEAM_MAP = {
    # 我司 (Our Company) — 9 rooms
    '小米官方手表': '我司',
    '小米官方手环直播间': '我司',
    '小米数码旗舰店': '我司',
    '小米官方耳机直播间': '我司',
    '小米手环10Pro直播间': '我司',
    '小米官旗手表直播间': '我司',
    '小米智能设备旗舰店直播间': '我司',
    '小米手环官旗直播间': '我司',
    '小米AI眼镜直播间': '我司',
    # 机械空间 (Jixie Space) — 2 rooms
    '小米智能穿戴国补号': '机械空间',
    '小米智能穿戴授权号': '机械空间',
    # 纵横 (Zongheng) — 2 rooms
    # 注意：'小米手环官方直播间'(纵横) 与 '小米官方手环直播间'(我司) 是两个不同直播间，勿混
    '小米官方手表直播号': '纵横',
    '小米手环官方直播间': '纵横',
    # 凝云 (Ningyun) — 1 room
    '小米手环直播间': '凝云',
    # 逐梦 (Zhumeng) — 1 room
    '小米手环官方账号': '逐梦',
    # 斐纳 (Feina) — 1 room
    '小米智能穿戴官方直播间': '斐纳',
    # 乐群 (Lequn) — 1 room
    '小米智能手表官方直播间': '乐群',
    # 炽木电商 (Chimu) — 1 room
    '小米耳机数码官方直播间': '炽木电商',
    # 良米 (Liangmi) — 12 rooms
    '小米官方手环号': '良米',
    '小米手环': '良米',
    '小米数码智能旗舰店': '良米',
    'watch智能手环直播间': '良米',
    'watch数码手环直播间': '良米',
    '小米智能手表旗舰店': '良米',
    '小米手表官方直播间': '良米',
    '小米手表': '良米',
    '小米官方手表直播': '良米',
    '小米耳机官方直播间': '良米',
    '小米官方Ai智能眼镜': '良米',
    # 商品卡渠道标识
    '我司商品卡': '我司',
    '良米商品卡': '良米',
}

# === 我司 vs 良米 直播间名单（10Pro 对比模块专用，显式名单） ===
# 用于「小米手环10Pro · 我司 vs 良米 销量对比」，未列入名单的直播间不计入该模块。
OUR_ROOMS = {
    '小米官方手表',
    '小米官方手环直播间',
    '小米数码旗舰店',
    '小米官方耳机直播间',
    '小米官旗手表直播间',
    '小米手环官旗直播间',
    '小米手环10Pro直播间',
    '小米AI眼镜直播间',
    '我司商品卡',  # 商品卡渠道
}
# 注：'小米智能设备旗舰店直播间' 属我司但不在此名单——该间只卖儿童手表/路由器，无 10Pro 销售。

LIANGMI_ROOMS = {
    '小米官方手环号',
    '小米手环',
    '小米数码智能旗舰店',
    'watch智能手环直播间',
    'watch数码手环直播间',
    '小米智能手表旗舰店',
    '小米手表官方直播间',
    '小米手表',
    '小米官方手表直播',
    '良米商品卡',  # 商品卡渠道
}
# 注：'小米耳机官方直播间'、'小米官方Ai智能眼镜' 属良米但不在此名单——两间均无 10Pro 销售。

# === Team display order ===
TEAM_ORDER = ['我司', '机械空间', '纵横', '凝云', '逐梦', '斐纳', '乐群', '炽木电商', '良米']

# === All teams list (used for iteration) ===
ALL_TEAMS = TEAM_ORDER

# === Team display colors ===
TEAM_COLORS = {
    '我司': '#1E90FF',
    '机械空间': '#FF6B35',
    '纵横': '#7c6ff7',
    '凝云': '#e74c3c',
    '逐梦': '#0d9488',
    '斐纳': '#c026d3',
    '乐群': '#f59e0b',
    '炽木电商': '#65a30d',
    '良米': '#94a3b8',
}

# === Team display markers ===
TEAM_MARKERS = {
    '我司': '★',
    '机械空间': '◆',
    '纵横': '▲',
    '凝云': '●',
    '逐梦': '◇',
    '斐纳': '△',
    '乐群': '✦',
    '炽木电商': '✧',
    '良米': '·',
}

# === Our team identifier ===
OUR_TEAM = '我司'


def classify_room(room_name):
    """Classify a room name into its team. Defaults to '良米'."""
    return TEAM_MAP.get(str(room_name).strip(), '良米')
