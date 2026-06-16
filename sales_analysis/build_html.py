"""Build the HTML dashboard — template copy (data loaded via fetch at runtime)."""
import os
import shutil

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    src = os.path.join(DATA_DIR, 'dashboard.html')
    out_path = os.path.join(DATA_DIR, 'index.html')

    # Simple copy — data is loaded asynchronously via fetch('./history.json') at runtime
    shutil.copy2(src, out_path)
    print(f'HTML dashboard built: {out_path} (data loaded via fetch at runtime)')


if __name__ == '__main__':
    main()
