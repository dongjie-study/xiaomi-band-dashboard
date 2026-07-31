"""
Shared utility functions used across the project.
"""
import pandas as pd
import numpy as np


def to_num(s):
    """
    Convert string to float, handling thousands separator and percent sign.
    e.g., '1,234.56' → 1234.56, '7.23%' → 7.23

    Args:
        s: String or numeric value.

    Returns:
        Float value, or np.nan if unparseable.
    """
    if isinstance(s, str):
        return float(s.replace(',', '').replace('%', ''))
    return float(s) if pd.notna(s) else np.nan


def detect_excel_columns(df):
    """
    Auto-detect Excel column roles by keyword matching in column names.

    Args:
        df: pandas DataFrame.

    Returns:
        dict mapping logical names ('product','price','time','room','type') to
        actual column names, or None if not found.
    """
    col_map = {}
    for i, col in enumerate(df.columns):
        name = str(col)
        if any(kw in name for kw in ['商品', '产品', 'product']):
            col_map['product'] = i
        elif any(kw in name for kw in ['金额', '价格', 'price', '应付']):
            col_map['price'] = i
        elif any(kw in name for kw in ['时间', '提交', 'time', 'date']):
            col_map['time'] = i
        elif any(kw in name for kw in ['直播', '房间', 'room', '达人', '昵称']):
            col_map['room'] = i
        elif any(kw in name for kw in ['类型', '我方', '竞对', 'type']):
            col_map['type'] = i

    result = {}
    for key in ['product', 'price', 'time', 'room', 'type']:
        if key in col_map:
            result[key] = df.columns[col_map[key]]
        else:
            result[key] = None
    return result


def load_video_data(path):
    """
    Load Qianchuan video data Excel file with standard column layout (37 columns).

    Args:
        path: Path to Excel file.

    Returns:
        Cleaned DataFrame with standardized column names.
    """
    df = pd.read_excel(path)
    clean = pd.DataFrame()
    clean['name'] = df.iloc[:, 0]
    clean['source'] = df.iloc[:, 5]
    clean['tag'] = df.iloc[:, 6]
    clean['roi'] = df.iloc[:, 7].apply(to_num)
    clean['orders'] = pd.to_numeric(df.iloc[:, 8], errors='coerce')
    clean['deal_amt'] = df.iloc[:, 9].apply(to_num)
    clean['avg_price'] = pd.to_numeric(df.iloc[:, 10], errors='coerce')
    clean['impressions'] = df.iloc[:, 11].apply(to_num)
    clean['clicks'] = df.iloc[:, 12].apply(to_num)
    clean['ctr'] = df.iloc[:, 13].apply(to_num)
    clean['cvr'] = df.iloc[:, 14].apply(to_num)
    clean['cost'] = df.iloc[:, 15].apply(to_num)
    clean['pay_roi'] = df.iloc[:, 17].apply(to_num)
    clean['pay_amt'] = df.iloc[:, 18].apply(to_num)
    clean['pay_orders'] = pd.to_numeric(df.iloc[:, 19], errors='coerce')
    clean['cpc'] = pd.to_numeric(df.iloc[:, 22], errors='coerce')
    clean['cpm'] = df.iloc[:, 23].apply(to_num)
    clean['likes'] = pd.to_numeric(df.iloc[:, 27], errors='coerce')
    clean['new_fans'] = pd.to_numeric(df.iloc[:, 28], errors='coerce')
    clean['avg_watch_time'] = pd.to_numeric(df.iloc[:, 29], errors='coerce')
    clean['plays'] = df.iloc[:, 30].apply(to_num)
    clean['completion'] = df.iloc[:, 31].apply(to_num)
    clean['comments'] = pd.to_numeric(df.iloc[:, 32], errors='coerce')
    clean['play_2s'] = df.iloc[:, 33].apply(to_num)
    clean['play_3s'] = df.iloc[:, 34].apply(to_num)
    clean['play_5s'] = df.iloc[:, 35].apply(to_num)
    clean['play_10s'] = df.iloc[:, 36].apply(to_num)
    clean['plays'] = clean['plays'].fillna(0)
    return clean
