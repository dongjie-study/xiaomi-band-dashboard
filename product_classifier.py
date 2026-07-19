"""
Unified product name classification.
Single source of truth — all other scripts should import from here.

Usage:
    from product_classifier import classify_product
    short_name = classify_product(full_product_name)
"""


def classify_product(name):
    """
    Classify a full product name into its canonical short category name.

    Args:
        name: Raw product name string from Excel order data.

    Returns:
        Canonical product category name (str).
    """
    name = str(name)
    if '10Pro' in name or '10 Pro' in name:
        return '小米手环10 Pro'
    elif '10' in name and 'Pro' not in name and '9' not in name:
        return '小米手环10'
    elif '9 Pro' in name or '9Pro' in name:
        return '小米手环9 Pro'
    elif 'REDMI Watch 6' in name:
        return 'REDMI Watch 6'
    elif 'REDMI 手' in name:
        return 'REDMI 手环 3'
    elif 'Type-C' in name or '充电' in name:
        return '充电配件'
    elif 'Xiaomi Buds 6' in name:
        return 'Xiaomi Buds 6'
    elif 'Xiaomi Buds 5' in name:
        return 'Xiaomi Buds 5 Pro'
    elif '骨传导耳机' in name:
        return '小米骨传导耳机2'
    elif '开放式耳机' in name or '耳夹式耳机' in name:
        return 'Xiaomi 开放式耳机'
    elif 'Buds 8 Pro' in name:
        return 'REDMI Buds 8 Pro'
    elif 'Buds 8 青春' in name:
        return 'REDMI Buds 8 青春版'
    elif 'Buds 8 活力' in name:
        return 'REDMI Buds 8 活力版'
    elif 'Buds 8' in name:
        return 'REDMI Buds 8'
    elif 'Buds 7S' in name:
        return 'REDMI Buds 7S'
    elif 'Buds 6 活力' in name:
        return 'REDMI Buds 6 活力版'
    elif 'Buds 6' in name:
        return 'REDMI Buds 6'
    elif '颈挂式耳机' in name:
        return 'Xiaomi 颈挂式耳机2'
    elif '头戴' in name:
        return '头戴式耳机'
    elif '耳机' in name or 'Buds' in name:
        return '耳机配件'
    elif 'AI眼镜' in name or 'AI 眼镜' in name:
        return '小米AI眼镜'
    elif '手环8' in name or 'Band 8' in name:
        return '小米手环8'
    elif '插线板' in name or '插座' in name:
        return '插线板/配件'
    # Additional product categories
    elif '体重秤' in name or '体脂秤' in name or '电子秤' in name:
        return '体重秤'
    elif '摄像' in name or '监控' in name:
        return '智能摄像机'
    elif '路由' in name:
        return '路由器'
    elif '门铃' in name:
        return '智能门铃'
    elif 'Pad' in name or '平板' in name:
        return '平板/配件'
    elif '键盘' in name:
        return '键盘/配件'
    elif '风扇' in name:
        return '手持风扇'
    elif '台灯' in name or '吸顶灯' in name or '灯泡' in name:
        return '台灯/灯具'
    elif '鱼缸' in name:
        return '鱼缸配件'
    elif '米兔' in name or ('儿童' in name and ('手表' in name or '电话' in name)):
        return '儿童手表'
    elif '门锁' in name or '指纹锁' in name:
        return '智能门锁'
    elif '传感' in name:
        return '传感器'
    elif '螺丝刀' in name or '扳手' in name or '工具' in name:
        return '工具配件'
    elif '腕带' in name or '表带' in name or '链' in name:
        return '腕带/表带'
    elif '壳' in name or '膜' in name or '保护套' in name:
        return '保护壳/膜'
    elif '背包' in name or '双肩' in name or '箱包' in name or '斜挎' in name:
        return '箱包'
    elif '剃须' in name or '牙刷' in name or '吹风' in name or '洁面' in name or '美容' in name:
        return '个人护理'
    elif '净化' in name or '加湿' in name or '除湿' in name:
        return '环境电器'
    elif '音箱' in name or '音响' in name or 'Sound' in name or 'Speaker' in name:
        return '音箱'
    elif ('手机' in name or 'Phone' in name) and '手环' not in name and '手表' not in name:
        return '手机'
    elif '笔记本' in name or '电脑' in name or 'Book' in name or 'Laptop' in name:
        return '笔记本'
    elif '电视' in name or 'TV' in name:
        return '电视'
    elif '滑板' in name or '平衡车' in name or ('电动' in name and '车' in name):
        return '出行工具'
    elif '车载' in name or '汽车' in name:
        return '汽车用品'
    # Generic shortening for unmatched products
    else:
        # Try to find model number pattern and truncate after it
        import re
        m = re.search(r'[A-Z]{1,2}\d{2,4}[A-Z]?\d*', name, re.IGNORECASE)
        if m and m.start() > 1:
            cut = m.end()
            if 4 < cut < len(name):
                return name[:cut]
        # Still too long, truncate
        if len(name) > 18:
            return name[:18]
        return name[:25]


# Alias for backwards compatibility
shorten_product = classify_product
