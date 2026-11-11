"""Offline matte cleanup. Always read immutable originals; never re-erode output."""
from pathlib import Path
import argparse, hashlib, json, re, shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'windows/Meow.Windows/Assets/Lulu'
REVIEW = ROOT / 'build/lulu-edge-cleanup'

def clean(image, floor=False, ball=False, fruit=False):
    old = np.array(image.convert('RGBA'))
    rgb = old[:, :, :3].astype(np.float32)
    alpha = old[:, :, 3].astype(np.float32) / 255
    removed = np.zeros(alpha.shape, bool)
    if floor:
        low, high = rgb.min(axis=2), rgb.max(axis=2)
        yy, xx = np.indices(alpha.shape)
        candidate = ((high-low)/np.maximum(high, 1) < .55) & (low > 25) & (yy > alpha.shape[0]*.65)
        if ball:
            blue = (rgb[:, :, 2] > rgb[:, :, 0]*1.2) & (rgb[:, :, 2] > 65) & (alpha > .2)
            by, bx = np.where(blue)
            if len(bx):
                cx, cy = (bx.min()+bx.max())/2, (by.min()+by.max())/2
                radius = max(bx.max()-bx.min(), by.max()-by.min())/2+5
                candidate &= (xx-cx)**2+(yy-cy)**2 > radius**2
        if fruit:
            # The pale rind is real foreground, including when the slice enters
            # from the bottom. Locate it by the red pulp, not by white pixels.
            hsv = cv2.cvtColor(old[:, :, :3], cv2.COLOR_RGB2HSV)
            pulp = (hsv[:, :, 0] < 12) & (hsv[:, :, 1] > 80) & (hsv[:, :, 2] > 100) & (rgb[:, :, 2] > 30) & (yy > alpha.shape[0]*.5) & (alpha > .2)
            py, px = np.where(pulp)
            if len(px) > 8:
                cx, cy = (px.min()+px.max())/2, (py.min()+py.max())/2
                rx, ry = (px.max()-px.min())/2+5, (py.max()-py.min())/2+8
                candidate &= ((xx-cx)/rx)**2+((yy-cy)/ry)**2 > 1
        # Only neutral/brown floor spill connected to the exterior; no interior
        # eye/prop masking. The actual yellow feet remain strongly saturated.
        traversable = ((alpha < .01) | candidate).astype(np.uint8)
        flood = traversable.copy()
        cv2.floodFill(flood, None, (0, 0), 2)
        removed = (flood == 2) & candidate & (alpha > 0)
        alpha[removed] = 0
    # Sample inward, not across the transparent white background. No interior
    # colour changes: only the narrow boundary band can be decontaminated.
    core = cv2.erode((alpha >= .98).astype(np.uint8), np.ones((3, 3), np.uint8))
    if not core.any():
        return image.copy(), {'changed': 0, 'coreChanged': 0}
    distance, labels = cv2.distanceTransformWithLabels(1-core, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    samples = np.zeros((int(labels.max()) + 1, 3), np.float32)
    samples[labels[core > 0]] = rgb[core > 0]
    foreground = samples[labels]
    white = 255 - foreground
    mix = np.sum((rgb-foreground)*white, axis=2) / np.maximum(np.sum(white*white, axis=2), 1)
    residual = np.sqrt(np.mean((rgb-foreground-white*mix[:, :, None])**2, axis=2))
    band = (distance > 0) & (distance <= 3.6) & (alpha > 0)
    # A genuinely white foreground has no reliable white-spill estimate.
    eligible = band & (foreground.min(axis=2) < 185) & (residual < 28) & (mix > .04)
    spill = np.where(eligible, np.clip(mix, 0, .85), 0)
    rgb = np.clip((rgb-255*spill[:, :, None]) / (1-spill[:, :, None]), 0, 255)
    coverage = alpha*(1-spill)
    # Subpixel antialias only: retain the opaque core and the existing silhouette.
    smooth = cv2.GaussianBlur(coverage, (3, 3), .48)
    boundary = (distance > 0) & (distance < 4.5)
    coverage = np.where(boundary, coverage*.65+smooth*.35, coverage)
    coverage[alpha == 0] = 0
    result = old.copy()
    result[:, :, :3] = np.rint(rgb).astype(np.uint8)
    result[:, :, 3] = np.rint(coverage*255).astype(np.uint8)
    result[result[:, :, 3] == 0, :3] = 0
    changed = np.any(result != old, axis=2) & (old[:, :, 3] > 0)
    return Image.fromarray(result), {'changed': int(changed.sum()), 'coreChanged': int((changed & (core > 0)).sum()), 'spillPixels': int(eligible.sum()), 'floorPixels': int(removed.sum())}

def jobs():
    for group in ['Video', 'Bed']:
        original = REVIEW/'original'/group
        if not original.exists():
            shutil.copytree(ASSETS/group, original)
        manifest = json.loads((original/'manifest.json').read_text('utf-8-sig'))
        listed = set()
        for key, clip in manifest['clips'].items():
            w = clip.get('width', manifest.get('cellSize', manifest.get('width')))
            h = clip.get('height', manifest.get('cellSize', manifest.get('height')))
            columns = manifest['columns']
            page = manifest.get('pageFrames', clip['frames'])
            for start in range(0, clip['frames'], page):
                name = clip.get('file', f'{key}-{start//page}.png')
                if name in listed: continue
                listed.add(name)
                yield group, name, w, h, columns, min(page, clip['frames']-start)
        for path in sorted(original.glob('*.png')):
            if path.name not in listed:
                # Obsolete pages left by an older, longer take are not loaded.
                if re.search(r'-\d+\.png$', path.name): continue
                with Image.open(path) as image: w, h = image.size
                yield group, path.name, w, h, 1, 1

def composite(image, color):
    bg = Image.new('RGBA', image.size, color)
    bg.alpha_composite(image)
    return bg.convert('RGB')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--only', default='', help='Optional atlas file name, e.g. eat.png')
    args = parser.parse_args()
    REVIEW.mkdir(parents=True, exist_ok=True)
    records = []
    examples = []
    for group, name, w, h, columns, count in jobs():
        if args.only and name != args.only: continue
        source = REVIEW/'original'/group/name
        atlas = Image.open(source).convert('RGBA')
        output = Image.new('RGBA', atlas.size)
        stats = {'changed': 0, 'coreChanged': 0, 'spillPixels': 0, 'floorPixels': 0}
        worst = None
        for i in range(count):
            x, y = (i % columns)*w, (i // columns)*h
            frame = atlas.crop((x, y, x+w, y+h))
            fixed, numbers = clean(frame, floor=group == 'Video' or name.startswith(('approach-', 'depart-')), ball=name == 'play.png', fruit=name == 'eat.png')
            for key in stats: stats[key] += numbers.get(key, 0)
            output.paste(fixed, (x, y))
            if worst is None or numbers.get('spillPixels', 0) > worst[0]:
                worst = (numbers.get('spillPixels', 0), i, frame, fixed)
        assert stats['coreChanged'] == 0, (group, name, stats)
        if args.apply:
            staged = REVIEW/'cleaned'/group/name
            staged.parent.mkdir(parents=True, exist_ok=True)
            output.save(staged)
        record = {'group': group, 'file': name, 'frames': count, 'size': atlas.size, 'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(), **stats}
        records.append(record)
        if group == 'Video' or name in ['entry-2.png', 'loop-1.png', 'wake-5.png', 'depart-2.png', 'arrive-bed.png', 'join-return-0.png']:
            examples.append((f'{group}/{name} frame {worst[1]}', worst[2], worst[3]))
        print(group, name, stats, flush=True)
    for page in range(0, len(examples), 6):
        sheet = Image.new('RGB', (1024, 6*285), '#777777')
        draw = ImageDraw.Draw(sheet)
        for row, (name, before, after) in enumerate(examples[page:page+6]):
            draw.text((8,row*285+4), name+' | before dark / after dark / before light / after light', fill='white')
            for col, (im, bg) in enumerate([(before,'#172131'),(after,'#172131'),(before,'#eeeeee'),(after,'#eeeeee')]):
                tile = composite(im, bg); tile.thumbnail((256,256), Image.Resampling.LANCZOS)
                sheet.paste(tile, (col*256,row*285+24))
        sheet.save(REVIEW/f'{Path(args.only).stem+"-" if args.only else ""}comparison-{page//6}.png')
    (REVIEW/f'{Path(args.only).stem+"-" if args.only else ""}review.json').write_text(json.dumps({'applied': args.apply, 'files': len(records), 'frames': sum(r['frames'] for r in records), 'records': records}, indent=2), 'utf-8')
    if args.apply:
        for record in records:
            destination = ASSETS/record['group']/record['file']
            temporary = destination.with_suffix('.tmp')
            shutil.copyfile(REVIEW/'cleaned'/record['group']/record['file'], temporary)
            temporary.replace(destination)

if __name__ == '__main__': main()
