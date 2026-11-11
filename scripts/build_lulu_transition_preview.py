"""Return action clips to one shared idle image using motion-compensated bridges."""
from pathlib import Path
import argparse, json, subprocess
import imageio_ffmpeg
from PIL import Image, ImageChops, ImageStat, ImageDraw

root = Path(__file__).resolve().parents[1] / "build" / "lulu-video-free"
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
size = (400, 594)
fps = 16

def read(path):
    stream = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgb24")
    meta = next(stream)
    return [Image.frombytes("RGB", meta["size"], data).resize(size, Image.Resampling.LANCZOS) for data in stream]

def write_video(path, frames):
    writer = imageio_ffmpeg.write_frames(str(path), size, fps=fps, codec="libx264", pix_fmt_in="rgb24", pix_fmt_out="yuv420p", macro_block_size=2, output_params=["-crf", "18", "-preset", "fast"])
    writer.send(None)
    for frame in frames:
        writer.send(frame.tobytes())
    writer.close()

def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3

def write_gif(path, frames):
    # Shared palette and lossless input preserve the exact idle endpoints.
    process = subprocess.Popen([ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "pipe:0", "-filter_complex", "split[a][b];[a]palettegen[p];[b][p]paletteuse", "-loop", "0", str(path)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for frame in frames:
        process.stdin.write(frame.tobytes())
    process.stdin.close()
    error = process.stderr.read().decode(errors="replace")
    if process.wait() != 0:
        raise RuntimeError(error)
    with Image.open(path) as animation:
        start = animation.convert("RGB")
        animation.seek(animation.n_frames - 1)
        if ImageChops.difference(start, animation.convert("RGB")).getbbox() is not None:
            raise RuntimeError(f"Encoded GIF loop endpoints differ: {path}")
    return True

parser = argparse.ArgumentParser()
parser.add_argument("--actions", nargs="+", choices=["walk", "sleep", "eat", "stretch", "nod", "dance"], default=["walk", "sleep"])
parser.add_argument("--combined", action="store_true")
args = parser.parse_args()
clips = {name: read(root / name / f"lulu-{name}.mp4") for name in args.actions}
idle = read(root / "walk" / "lulu-walk.mp4")[0]
sequence = [idle] * 8
reports = {}
for name, frames in clips.items():
    work = root / name / "transition"
    work.mkdir(exist_ok=True)
    for i, frame in enumerate([frames[-1], frames[-1], idle, idle]):
        frame.save(work / f"input-{i:02d}.png")
    # Motion compensation aligns moving features instead of alpha-overlapping
    # two mismatched faces. Only a small, stationary endpoint correction is used.
    subprocess.run([ffmpeg, "-y", "-framerate", "2", "-i", str(work / "input-%02d.png"), "-vf", "minterpolate=fps=16:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none,trim=start=0.5:end=1,setpts=PTS-STARTPTS", str(work / "bridge-%02d.png")], check=True, capture_output=True)
    bridge = [Image.open(p).convert("RGB") for p in sorted(work.glob("bridge-*.png"))]
    if len(bridge) != 8:
        raise RuntimeError(f"Expected 8 bridge frames, got {len(bridge)}")
    before = diff(frames[-1], idle)
    boundary = [frames[-1], *bridge, idle]
    jumps = [diff(a, b) for a, b in zip(boundary, boundary[1:])]
    reports[name] = {"original_cut_rgb_error": round(before, 3), "bridge_max_step_rgb_error": round(max(jumps), 3), "exact_idle_loop_endpoints": True, "bridge_frames": len(bridge), "fps": fps}
    loop = [idle] * 4 + frames[1:] + bridge + [idle] * 8
    write_video(root / name / f"lulu-{name}-loop.mp4", loop)
    reports[name]["encoded_gif_loop_identical"] = write_gif(root / name / f"lulu-{name}-loop.gif", loop)
    (root / name / "loop-report.json").write_text(json.dumps(reports[name], indent=2), encoding="utf-8")
    sequence += frames[1:] + bridge + [idle] * 8
    sheet = Image.new("RGB", (size[0] * 5, size[1] + 25), "#eee9e1")
    draw = ImageDraw.Draw(sheet)
    for i, (label, frame) in enumerate([("ACTION END", frames[-1]), ("BRIDGE 25%", bridge[2]), ("BRIDGE 50%", bridge[4]), ("BRIDGE 75%", bridge[6]), ("COMMON IDLE", idle)]):
        sheet.paste(frame, (size[0]*i, 0)); draw.text((size[0]*i+8,size[1]+5), label, fill="black")
    sheet.save(root / name / "transition-review.png")

if args.combined:
    write_video(root / "lulu-actions-preview.mp4", sequence)
    reports["encoded_gif_loop_identical"] = write_gif(root / "lulu-actions-preview.gif", sequence)
    (root / "transition-report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
print(json.dumps(reports, indent=2))
