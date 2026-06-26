"""
Update product categories in history.json
Only keep 3 Xiaomi Band categories:
- 小米手环10 Pro (anything with 10Pro or 10 Pro)
- 小米手环10 (anything with 10 but not Pro)
- 小米手环9 Pro (anything with 9 Pro or 9Pro)
"""
import json
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(DATA_DIR, 'sales_analysis', 'history.json')

def reclassify_product(name):
    """Reclassify product name to one of the 3 categories"""
    name = str(name)
    if '10Pro' in name or '10 Pro' in name:
        return '小米手环10 Pro'
    elif '10' in name and 'Pro' not in name and '9' not in name:
        return '小米手环10'
    elif '9 Pro' in name or '9Pro' in name:
        return '小米手环9 Pro'
    else:
        return name  # Keep other products as-is

def merge_products(products_dict):
    """Merge product entries that now map to the same category"""
    merged = {}
    for old_name, stats in products_dict.items():
        new_name = reclassify_product(old_name)
        if new_name in merged:
            # Merge with existing entry
            merged[new_name]['orders'] += stats.get('orders', 0)
            merged[new_name]['revenue'] += stats.get('revenue', 0)
            # Recalculate avg_price
            if merged[new_name]['orders'] > 0:
                merged[new_name]['avg_price'] = round(
                    merged[new_name]['revenue'] / merged[new_name]['orders'], 2
                )
        else:
            merged[new_name] = {
                'orders': stats.get('orders', 0),
                'revenue': stats.get('revenue', 0),
                'avg_price': stats.get('avg_price', 0)
            }
    return merged

def update_history():
    """Update all product categories in history.json"""
    print(f"Loading history from: {HISTORY_FILE}")
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        history = json.load(f)

    print(f"Found {len(history)} days of data")

    # Track changes
    changes = {}

    for day in history:
        # Update top-level products
        if 'products' in day:
            old_products = day['products']
            day['products'] = merge_products(old_products)

            # Track changes
            for old_name in old_products:
                new_name = reclassify_product(old_name)
                if old_name != new_name:
                    if old_name not in changes:
                        changes[old_name] = new_name

        # Update room-level products
        if 'rooms' in day:
            for room_name, room_data in day['rooms'].items():
                if 'products' in room_data:
                    room_data['products'] = merge_products(room_data['products'])

                # Update hourly stats products
                if '_hourly_stats' in room_data:
                    for hour, hour_data in room_data['_hourly_stats'].items():
                        if 'products' in hour_data:
                            hour_data['products'] = merge_products(hour_data['products'])

        # Update hourly stats at day level
        if '_hourly_stats' in day:
            for hour, hour_data in day['_hourly_stats'].items():
                if 'products' in hour_data:
                    hour_data['products'] = merge_products(hour_data['products'])

    # Print summary of changes
    print(f"\nProduct reclassifications:")
    for old, new in sorted(changes.items()):
        print(f"  {old} -> {new}")

    # Save updated history
    print(f"\nSaving updated history to: {HISTORY_FILE}")
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, separators=(',', ':'))

    print("Done!")

    # Verify the changes
    print("\nVerifying latest day products:")
    latest = history[-1]
    for name, stats in latest['products'].items():
        print(f"  {name}: {stats['orders']} orders, RMB {stats['revenue']:,.2f}")

if __name__ == '__main__':
    update_history()
