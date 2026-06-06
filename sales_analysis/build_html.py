"""Build the HTML dashboard with injected multi-room data."""
import json
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')


def main():
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        history = json.load(f)

    if not history:
        print("No history data found")
        return

    today = history[-1]

    with open(os.path.join(DATA_DIR, 'dashboard.html'), 'r', encoding='utf-8') as f:
        html = f.read()

    html = html.replace('__DATA_PLACEHOLDER__', json.dumps(today, ensure_ascii=False))
    html = html.replace('__HISTORY_PLACEHOLDER__', json.dumps(history, ensure_ascii=False))

    out_path = os.path.join(DATA_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    room_count = len(today.get('rooms', {}))
    print(f'HTML dashboard built: {out_path} ({len(history)} days, {room_count} rooms today)')


if __name__ == '__main__':
    main()
