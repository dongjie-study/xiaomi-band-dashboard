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
    else:
        return name[:25]


# Alias for backwards compatibility
shorten_product = classify_product
