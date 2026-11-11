"""Build one forward, phase-matched walking cycle with a periodic 60 fps seam.

Input is the original 56-frame RGBA atlas, not a previously processed output.
No reverse playback, duplicated endpoint or transparent crossfade is used.
"""
from pathlib import Path
import argparse, hashlib, json, math
import cv2
import numpy as np
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('--output', type=Path, default=Path('windows/Meow.Windows/Assets/Lulu/Video'))
p.add_argument('--review', type=Path, default=Path('build/lulu-walk-loop-fix'))
args = p.parse_args()
args.review.mkdir(parents=True, exist_ok=True)
source = Image.open(args.source).convert('RGBA')
start, end, count, fps = 4, 25, 53, 60
cells = [np.asarray(source.crop((i % 8 * 256, i // 8 * 256, i % 8 * 256 + 256, i // 8 * 256 + 256)), dtype=np.float32) / 255 for i in range(start, end)]
yy, xx = np.mgrid[:256, :256].astype(np.float32)

def gray(a):
    return cv2.cvtColor(np.uint8(np.clip((a[:, :, :3] * a[:, :, 3:] + 1 - a[:, :, 3:]) * 255, 0, 255)), cv2.COLOR_RGB2GRAY)

def distance(a):
    mask = np.uint8(a[:, :, 3] > .5)
    return cv2.distanceTransform(mask, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - mask, cv2.DIST_L2, 5)

def warp(a, flow, t):
    mx, my = xx.copy(), yy.copy()
    for _ in range(4):
        f = cv2.remap(flow, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        mx, my = xx - t * f[:, :, 0], yy - t * f[:, :, 1]
    return cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

flows = []
for i, a in enumerate(cells):
    b = cells[(i + 1) % len(cells)]
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    flows.append((dis.calc(gray(a), gray(b), None), dis.calc(gray(b), gray(a), None)))
premultiplied = [np.concatenate((a[:, :, :3] * a[:, :, 3:], a[:, :, 3:]), axis=2) for a in cells]
distances = [distance(a) for a in cells]
frames = []
for n in range(count):
    phase = n * len(cells) / count
    i = int(phase); j = (i + 1) % len(cells); t = phase - i
    if t < 1e-8:
        rgba = cells[i]
    else:
        ab, ba = flows[i]
        mixed = warp(premultiplied[i], ab, t) * (1 - t) + warp(premultiplied[j], ba, 1 - t) * t
        rgb = np.divide(mixed[:, :, :3], mixed[:, :, 3:], out=np.zeros_like(mixed[:, :, :3]), where=mixed[:, :, 3:] > 1e-6)
        alpha = np.clip(warp(distances[i], ab, t) * (1 - t) + warp(distances[j], ba, 1 - t) * t + .5, 0, 1)
        rgba = np.concatenate((rgb, alpha[:, :, None]), axis=2)
    frames.append(Image.fromarray(np.uint8(np.clip(rgba * 255, 0, 255))))
atlas = Image.new('RGBA', (2048, math.ceil(count / 8) * 256))
for n, frame in enumerate(frames):
    atlas.paste(frame, (n % 8 * 256, n // 8 * 256))
atlas.save(args.output / 'walk.png', compress_level=3)
manifest_path = args.output / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['clips']['walk'].update(frames=count, fps=fps, mode='loop', processing={
    'method': 'Forward complete stride; periodic bidirectional motion compensation including wrap',
    'originalAtlasSha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
    'originalFrameInterval': [start, end], 'originalFps': 24,
    'outputDurationSeconds': count / fps, 'duplicateEndpoint': False,
})
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
sheet = Image.new('RGB', (8 * 192, 7 * 210), '#34475a'); draw = ImageDraw.Draw(sheet)
for n, frame in enumerate(frames):
    thumb = frame.resize((192, 192)); x, y = n % 8 * 192, n // 8 * 210
    sheet.paste(thumb, (x, y), thumb); draw.text((x + 5, y + 193), str(n), fill='white')
sheet.save(args.review / 'fixed-cycle.jpg')
print(f'Built {count} frames / {fps} fps, {count / fps:.4f}s loop')
