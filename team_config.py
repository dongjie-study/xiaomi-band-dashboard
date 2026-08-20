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
    # 我司 (Our Company) — 6 rooms
    '小米官方手表': '我司',
    '小米官方手环直播间': '我司',
    '小米数码旗舰店': '我司',
    '小米官方耳机直播间': '我司',
    '小米手环10Pro直播间': '我司',
    '小米官旗手表直播间': '我司',
    '小米智能设备旗舰店直播间': '我司',
    '小米手环官旗直播间': '我司',
    # 机械空间 (Jixie Space) — 2 rooms
    '小米智能穿戴国补号': '机械空间',
    '小米智能穿戴授权号': '机械空间',
    # 纵横 (Zongheng) — 1 room
    '小米官方手表直播号': '纵横',
    # 凝云 (Ningyun) — 3 rooms
    '小米手环官方直播间': '凝云',
    '小米手环新品直播间': '凝云',
    '小米手环直播间': '凝云',
    # 逐梦 (Zhumeng) — 1 room
    '小米手环官方账号': '逐梦',
    # 良米 (Liangmi) — explicitly listed rooms
    'watch数码手环直播间': '良米',
    'watch智能手环直播间': '良米',
    '小米手表': '良米',
    '小米手表官方直播间': '良米',
    '小米手环': '良米',
    '小米数码智能旗舰店': '良米',
    '小米智能手表旗舰店': '良米',
    '小米官方手表直播': '良米',
    '小米官方手表直播间': '良米',
    '小米官方手环号': '良米',
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
    '我司商品卡',  # 商品卡渠道
}

LIANGMI_ROOMS = {
    'watch数码手环直播间',
    'watch智能手环直播间',
    '小米手表',
    '小米手表官方直播间',
    '小米手环',
    '小米数码智能旗舰店',
    '小米智能手表旗舰店',
    '小米官方手表直播',
    '小米官方手表直播间',
    '小米官方手环号',
    '良米商品卡',  # 商品卡渠道
}

# === Team display order ===
TEAM_ORDER = ['我司', '机械空间', '纵横', '凝云', '逐梦', '良米']

# === All teams list (used for iteration) ===
ALL_TEAMS = TEAM_ORDER

# === Team display colors ===
TEAM_COLORS = {
    '我司': '#1E90FF',
    '机械空间': '#FF6B35',
    '纵横': '#7c6ff7',
    '凝云': '#e74c3c',
    '逐梦': '#0d9488',
    '良米': '#94a3b8',
}

# === Team display markers ===
TEAM_MARKERS = {
    '我司': '★',
    '机械空间': '◆',
    '纵横': '▲',
    '凝云': '●',
    '逐梦': '◇',
    '良米': '·',
}

# === Our team identifier ===
OUR_TEAM = '我司'


def classify_room(room_name):
    """Classify a room name into its team. Defaults to '良米'."""
    return TEAM_MAP.get(str(room_name).strip(), '良米')
