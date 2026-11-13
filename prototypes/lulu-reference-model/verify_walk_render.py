"""Check genuine rendered frame completeness and quantify the loop image seam."""
from pathlib import Path
from PIL import Image,ImageFilter
import numpy as np,json,hashlib,argparse
ap=argparse.ArgumentParser();ap.add_argument('--iteration',default='10');args=ap.parse_args()
root=Path(__file__).resolve().parent/'walk-review'/('iter_'+args.iteration);folder=root/'frames-final'
meta=json.loads((root/'motion-targets.json').read_text());fps=meta['fps'];cycle=round(fps*meta['period_seconds'])
paths=[folder/f'frame-{i:04d}.png' for i in range(1,cycle+2)]
assert all(p.exists() for p in paths),'Render incomplete'
hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
a=np.asarray(Image.open(paths[0]).convert('RGB'),dtype=float);b=np.asarray(Image.open(paths[-1]).convert('RGB'),dtype=float)
aa=np.asarray(Image.open(paths[0]).convert('RGB').filter(ImageFilter.GaussianBlur(1.2)),dtype=float);bb=np.asarray(Image.open(paths[-1]).convert('RGB').filter(ImageFilter.GaussianBlur(1.2)),dtype=float)
result={'rendered_frames':len(paths),'fps':fps,'cycle_unique_frames':cycle,'adjacent_identical_frames':[i+1 for i in range(cycle) if hashes[i]==hashes[i+1]],'first_last_rgb_mean_absolute_difference_255':float(abs(a-b).mean()),'first_last_blurred_mean_absolute_difference_255':float(abs(aa-bb).mean())}
(root/'render-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
