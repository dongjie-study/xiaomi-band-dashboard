"""
小米手环竞对分析平台 - 统一入口
Usage:
  python run_all.py video                          # 生成视频广告分析报告
  python run_all.py video --extract                # 提取视频帧 + 生成报告
  python run_all.py sales <excel_path>             # 更新直播间销量数据
  python run_all.py sales <comp_path> <our_path>   # 竞对 + 我方 双文件模式
  python run_all.py all <sales_excel>              # 运行全部分析（不含视频帧提取）
"""
import sys
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIDEO_DIR = ROOT / "video_analysis"
SALES_DIR = ROOT / "sales_analysis"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def run_video(extract=False):
    os.chdir(VIDEO_DIR)
    if extract:
        print("=" * 60)
        print("  步骤 1/2: 提取视频帧")
        print("=" * 60)
        subprocess.run([sys.executable, "extract_frames.py"], check=True)
        print()

    print("=" * 60)
    print("  生成视频广告分析报告")
    print("=" * 60)
    subprocess.run([sys.executable, "generate_report.py"], check=True)
    print(f"Video report saved to: {ROOT / '竞对视频分析报告.html'}")
    os.chdir(ROOT)


def run_sales(excel_path, our_path=None):
    os.chdir(SALES_DIR)
    print("=" * 60)
    print("  更新直播间销量数据")
    print("=" * 60)
    cmd = [sys.executable, "daily_update.py", excel_path]
    if our_path:
        cmd.append(our_path)
    subprocess.run(cmd, check=True)

    # Copy outputs to shared output
    import shutil
    for f in ["index.html", "dashboard.png", "room_comparison.png", "comparison.png"]:
        src = SALES_DIR / f
        dst = OUTPUT_DIR / f
        if src.exists():
            shutil.copy2(src, dst)
    print(f"\nOutputs copied to: {OUTPUT_DIR}")
    os.chdir(ROOT)


def print_usage():
    print(__doc__)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "video":
        extract = "--extract" in sys.argv
        run_video(extract=extract)
    elif cmd == "sales":
        if len(sys.argv) < 3:
            print("Usage: python run_all.py sales <excel_path> [our_excel_path]")
            sys.exit(1)
        excel_path = sys.argv[2]
        our_path = sys.argv[3] if len(sys.argv) > 3 else None
        run_sales(excel_path, our_path)
    elif cmd == "all":
        if len(sys.argv) < 3:
            print("Usage: python run_all.py all <sales_excel_path> [our_excel_path]")
            sys.exit(1)
        run_sales(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print("\n")
        run_video(extract=False)
        print("\n" + "=" * 60)
        print("  全部分析完成！报告在 output/ 目录")
        print("=" * 60)
    else:
        print_usage()
