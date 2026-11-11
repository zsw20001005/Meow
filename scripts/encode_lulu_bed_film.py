"""Encode exported WPF frames using their declared frame rate and frame count."""
from pathlib import Path
import argparse,subprocess
import imageio_ffmpeg
p=argparse.ArgumentParser();p.add_argument('frames',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
rate=(a.frames/'frame-rate.txt').read_text().strip() if (a.frames/'frame-rate.txt').exists() else '24'
count=(a.frames/'frame-count.txt').read_text().strip()
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate',rate,'-i',str(a.frames/'%04d.png'),'-frames:v',count,'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output)],check=True,capture_output=True)
print(a.output.resolve())
