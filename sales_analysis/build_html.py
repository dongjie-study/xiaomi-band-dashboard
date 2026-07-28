"""Build the HTML dashboard — index.html loads data via fetch at runtime, no template needed."""
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    out_path = os.path.join(DATA_DIR, 'index.html')
    if os.path.exists(out_path):
        print(f'HTML dashboard ready: {out_path} (data loaded via fetch at runtime)')
    else:
        print(f'Warning: index.html not found at {out_path}')


if __name__ == '__main__':
    main()
