"""Inspect actual decoded endpoints and measure jumps; never invent a pass."""
from pathlib import Path
import argparse, json, statistics
import imageio_ffmpeg
from PIL import Image, ImageChops, ImageStat, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["walk", "sleep", "eat", "stretch", "nod", "dance"])
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / "build" / "lulu-video-free" / args.action
reader = imageio_ffmpeg.read_frames(str(root / f"lulu-{args.action}.mp4"), pix_fmt="rgb24")
metadata = next(reader)
frames = [Image.frombytes("RGB", metadata["size"], data).resize((280, 416)) for data in reader]
if len(frames) < 4:
    raise RuntimeError("Too few decoded video frames")
roi = (30, 15, 250, 400)
def difference(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a.crop(roi), b.crop(roi))).mean) / 3
adjacent = [difference(a, b) for a, b in zip(frames, frames[1:])]
end_jump = difference(frames[-1], frames[0])
result = {
    "frames": len(frames), "fps": metadata["fps"], "duration": metadata["duration"],
    "size": metadata["size"], "first_last_rgb_error": round(end_jump, 3),
    "median_adjacent_rgb_error": round(statistics.median(adjacent), 3),
    "p95_adjacent_rgb_error": round(sorted(adjacent)[int((len(adjacent)-1)*.95)], 3),
    "seam_jump_vs_typical_frame": round(end_jump / max(.001, statistics.median(adjacent)), 2),
    "note": "Numerical screening only; endpoint poses require visual review."
}
(root / "seam-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
sheet = Image.new("RGB", (1120, 446), "#eee9e1")
draw = ImageDraw.Draw(sheet)
for i, (label, frame) in enumerate([("FIRST", frames[0]), ("PRE-LAST", frames[-2]), ("LAST", frames[-1]), ("LOOP -> FIRST", frames[0])]):
    sheet.paste(frame, (i*280, 0)); draw.text((i*280+10, 425), label, fill="black")
sheet.save(root / "seam-review.png")
print(json.dumps(result, indent=2))
