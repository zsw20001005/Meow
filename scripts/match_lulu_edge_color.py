"""Match edge clip materials to idle, with one fixed transform for every frame."""
from pathlib import Path
import argparse, json
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'windows/Meow.Windows/Assets/Lulu/Edge'
MIDTONE_LIFT = 14.0  # Lab L in 0..255; tapered before highlights to retain texture.

def reference():
    return Image.open(ROOT / 'windows/Meow.Windows/Assets/Lulu/Video/hd-idle-0.png').convert('RGBA').crop((0, 0, 512, 512))

def palette(image, idle=False):
    a = np.array(image); rgb = a[:, :, :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    h, s, v = [hsv[:, :, i] for i in range(3)]
    y = np.indices(h.shape)[0]
    masks = [(h >= 20) & (h < 28) & (s > 90) & (v > 170),
             (h > 7) & (h < 20) & (s > 130) & (y > 155) & (y < (255 if idle else 325)),
             (v < 105) & (y < (115 if idle else 130))]
    return np.array([np.median(lab[m & (a[:, :, 3] > 250)], axis=0) for m in masks])

def correction(first):
    # Measure once, not per frame: changing pose must not cause color flicker.
    return palette(reference(), True) - palette(first)

def recolor(image, delta):
    a = np.array(image); rgb = a[:, :, :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    h, s, v = [hsv[:, :, i] for i in range(3)]
    def smooth(x):
        t = np.clip(x, 0, 1); return t*t*(3-2*t)
    chroma = smooth((s-45)/65)
    bright = smooth((v-85)/75)
    warm = smooth((h-3)/5) * (1-smooth((h-28)/8))
    yellow = smooth((h-17)/4)
    weight = chroma*bright*warm
    shift = weight[:, :, None] * (yellow[:, :, None]*delta[0] + (1-yellow[:, :, None])*delta[1])
    shift += (chroma*(1-bright)*warm)[:, :, None]*delta[2]
    # The edge source has stronger directional shading than idle. Matching only
    # material medians left the visible cheek/arms too dark at desktop size.
    # Lift warm midtones, protecting hair, glasses, whites and bright fur.
    lightness = lab[:, :, 0] + shift[:, :, 0]
    shift[:, :, 0] += weight * MIDTONE_LIFT * (1-smooth((lightness-195)/45))
    adjusted = cv2.cvtColor(np.uint8(np.clip(lab+shift, 0, 255)), cv2.COLOR_LAB2RGB)
    a[:, :, :3] = np.where((np.max(np.abs(shift), axis=2) > .01)[:, :, None], adjusted, rgb)
    a[a[:, :, 3] == 0] = 0
    return Image.fromarray(a)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args(); source = args.source.resolve()
    if source == OUT.resolve(): raise ValueError('Use an immutable source, not the output directory')
    manifest = json.loads((source/'manifest.json').read_text())
    first = Image.open(source/'edge-0.png').crop((0, 0, manifest['width'], manifest['height']))
    delta = correction(first)
    for path in sorted(source.glob('edge-*.png')):
        original = Image.open(path).convert('RGBA'); result = recolor(original, delta)
        assert np.array_equal(np.array(original)[:, :, 3], np.array(result)[:, :, 3])
        result.save(OUT/path.name, compress_level=3)
    manifest['colorMatch'] = {'reference': 'Video/hd-idle-0.png frame 0', 'labOffsets': delta.tolist(), 'midtoneLift': MIDTONE_LIFT, 'alphaUnchanged': True}
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    recolor(first, delta).save(ROOT/'build/lulu-edge-design/edge-color-matched.png')
    print(json.dumps(manifest['colorMatch']))

if __name__ == '__main__': main()
