import cv2
import os
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
FRAMES_DIR = BASE / "frames"
FRAMES_DIR.mkdir(exist_ok=True)

def sort_key(name):
    """Sort: 下载 (1).mp4, 下载 (2).mp4, ..., 下载.mp4 last"""
    m = re.search(r'\((\d+)\)', name)
    if m:
        return (0, int(m.group(1)))
    return (1, 0)  # 下载.mp4 goes last

def extract_frames(video_dir, prefix):
    """Extract 3 frames from each video, save as jpg thumbnails."""
    out_dir = FRAMES_DIR / prefix
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
                # Resize to max 640px wide
                if w > 640:
                    ratio = 640 / w
                    frame = cv2.resize(frame, (640, int(h * ratio)))
                fname = f"{idx}_{pct:.2f}.jpg"
                # cv2.imwrite doesn't support Chinese paths on Windows
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
        print(f"  [{prefix}] {vname} -> {len(frames)} frames ({duration:.1f}s)")

    return results

print("=== 提取良米视频帧 ===")
lm = extract_frames(BASE / "良米1-5号视频", "liangmi")
print(f"  共 {len(lm)} 个视频\n")

print("=== 提取我司视频帧 ===")
ws = extract_frames(BASE / "我司1-5号视频", "wosi")
print(f"  共 {len(ws)} 个视频\n")

print("Done!")
