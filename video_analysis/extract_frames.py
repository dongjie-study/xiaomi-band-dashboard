import cv2
import os
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent

def sort_key(name):
    """Sort: 下载 (1).mp4, 下载 (2).mp4, ..., 下载.mp4 last"""
    m = re.search(r'\((\d+)\)', name)
    if m:
        return (0, int(m.group(1)))
    return (1, 0)

def discover_dirs():
    """Find all 良米* and 我司* directories with MP4 files."""
    all_dirs = []
    for entry in sorted(os.listdir(BASE)):
        entry_path = BASE / entry
        if not entry_path.is_dir():
            continue
        if entry.startswith('良米') or entry.startswith('我司'):
            mp4s = [f for f in os.listdir(entry_path) if f.endswith('.mp4')]
            if mp4s:
                all_dirs.append(entry)
    return all_dirs

def extract_frames(video_dir, out_dir):
    """Extract 3 frames from each video in video_dir, save to out_dir as jpg."""
    out_dir.mkdir(exist_ok=True)

    videos = sorted(
        [f for f in os.listdir(video_dir) if f.endswith('.mp4')],
        key=sort_key
    )
    results = []
    for idx, vname in enumerate(videos):
        vpath = os.path.join(video_dir, vname)
        cap = cv2.VideoCapture(vpath)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0

        frames = []
        for pct in [0.25, 0.50, 0.75]:
            frame_idx = int(total_frames * pct)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                if w > 640:
                    ratio = 640 / w
                    frame = cv2.resize(frame, (640, int(h * ratio)))
                fname = f"{idx}_{pct:.2f}.jpg"
                buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])[1]
                with open(str(out_dir / fname), 'wb') as f:
                    f.write(buf.tobytes())
                frames.append(fname)

        cap.release()
        results.append({
            'index': idx,
            'filename': vname,
            'frames': frames,
            'duration': round(duration, 1),
            'total_frames': total_frames,
        })
        print(f"  {vname} -> {len(frames)} frames ({duration:.1f}s)")

    return results

dirs = discover_dirs()
if not dirs:
    print("No video directories found (looking for 良米*/ or 我司*/ with MP4s)")
    exit(1)

print(f"Found {len(dirs)} video directories: {', '.join(dirs)}\n")

for d in dirs:
    print(f"=== 提取: {d} ===")
    video_dir = BASE / d
    frames_out = BASE / d / "frames"
    results = extract_frames(video_dir, frames_out)
    print(f"  Done: {len(results)} videos -> {frames_out}\n")

print("All frames extracted!")
