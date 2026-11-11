"""Create review artifacts from the authorized free video trial (no uploads)."""
from pathlib import Path
import subprocess
import imageio_ffmpeg
from PIL import Image, ImageDraw
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--action", choices=["wave", "walk", "sleep", "eat", "stretch", "nod", "dance"], default="wave")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / "build" / "lulu-video-free"
if args.action != "wave":
    root /= args.action
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
video = root / f"lulu-{args.action}.mp4"
metadata = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video)], capture_output=True, text=True).stderr
(root / "video-metadata.txt").write_text(metadata, encoding="utf-8")
subprocess.run([ffmpeg, "-y", "-i", str(video), "-vf", "fps=3,scale=240:-1", str(root / "review-%02d.png")], check=True, capture_output=True)
frames = [Image.open(p).convert("RGB") for p in sorted(root.glob("review-*.png"))]
if not frames:
    raise RuntimeError("No decoded video frames")
w, h = frames[0].size
sheet = Image.new("RGB", (w * 4, (h + 24) * ((len(frames) + 3) // 4)), "#eee9e1")
draw = ImageDraw.Draw(sheet)
for i, frame in enumerate(frames):
    x, y = (i % 4) * w, (i // 4) * (h + 24)
    sheet.paste(frame, (x, y))
    draw.text((x + 8, y + h + 5), f"{i / 3:.2f}s", fill="black")
sheet.save(root / "video-review.png")
subprocess.run([ffmpeg, "-y", "-i", str(video), "-filter_complex", "[0:v]scale=400:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse", "-loop", "0", str(root / f"lulu-{args.action}.gif")], check=True, capture_output=True)
print(metadata)
print(f"Created lulu-{args.action}.gif and video-review.png")
