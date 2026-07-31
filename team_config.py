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
    # 机械空间 (Jixie Space) — 2 rooms
    '小米智能穿戴国补号': '机械空间',
    '小米智能穿戴授权号': '机械空间',
    # 纵横 (Zongheng) — 1 room
    '小米官方手表直播号': '纵横',
    # 凝云 (Ningyun) — 3 rooms
    '小米手环官方直播间': '凝云',
    '小米手环新品直播间': '凝云',
    '小米手环直播间': '凝云',
    # 商品卡渠道标识
    '我司商品卡': '我司',
    '良米商品卡': '良米',
}

# === Team display order ===
TEAM_ORDER = ['我司', '机械空间', '纵横', '凝云', '良米']

# === All teams list (used for iteration) ===
ALL_TEAMS = TEAM_ORDER

# === Team display colors ===
TEAM_COLORS = {
    '我司': '#1E90FF',
    '机械空间': '#FF6B35',
    '纵横': '#7c6ff7',
    '凝云': '#e74c3c',
    '良米': '#94a3b8',
}

# === Team display markers ===
TEAM_MARKERS = {
    '我司': '★',
    '机械空间': '◆',
    '纵横': '▲',
    '凝云': '●',
    '良米': '·',
}

# === Our team identifier ===
OUR_TEAM = '我司'


def classify_room(room_name):
    """Classify a room name into its team. Defaults to '良米'."""
    return TEAM_MAP.get(str(room_name).strip(), '良米')
