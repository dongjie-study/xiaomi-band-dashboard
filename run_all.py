"""
小米手环竞对分析平台 - 统一入口
Usage:
  python run_all.py sales <excel_path>             # 更新直播间销量数据
  python run_all.py sales <comp_path> <our_path>   # 竞对 + 我方 双文件模式
"""
import sys
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SALES_DIR = ROOT / "sales_analysis"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def run_sales(excel_path, our_path=None):
    try:
        os.chdir(SALES_DIR)
        print("=" * 60)
        print("  更新直播间销量数据")
        print("=" * 60)
        cmd = [sys.executable, "daily_update.py", excel_path]
        if our_path:
            cmd.append(our_path)
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        subprocess.run(cmd, check=True, env=env)

        # Copy outputs to shared output
        for f in ["index.html", "dashboard.png", "room_comparison.png", "comparison.png",
                  "history.json", "b10pro_history.json"]:
            src = SALES_DIR / f
            dst = OUTPUT_DIR / f
            if src.exists():
                shutil.copy2(src, dst)

        # 同步 hourly 数据目录（index.html 按日期 fetch 使用）
        hourly_src = SALES_DIR / "hourly"
        hourly_dst = OUTPUT_DIR / "hourly"
        if hourly_src.exists():
            shutil.copytree(hourly_src, hourly_dst, dirs_exist_ok=True)

        print(f"\nOutputs copied to: {OUTPUT_DIR}")
    finally:
        os.chdir(ROOT)


def print_usage():
    print(__doc__)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "sales":
        if len(sys.argv) < 3:
            print("Usage: python run_all.py sales <excel_path> [our_excel_path]")
            sys.exit(1)
        excel_path = sys.argv[2]
        our_path = sys.argv[3] if len(sys.argv) > 3 else None
        run_sales(excel_path, our_path)
    else:
        print_usage()
