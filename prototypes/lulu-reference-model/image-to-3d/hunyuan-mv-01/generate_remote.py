"""One free public Gradio generation using approved reference views only."""
import json
import time
import argparse
from pathlib import Path
from gradio_client import Client, handle_file

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--shape-only', action='store_true')
args = parser.parse_args()
stage = 'shape' if args.shape_only else 'generation'
client = Client('https://tencent-hunyuan3d-2mv.hf.space', download_files=str(ROOT / 'downloads'))
job = client.submit(
    caption=None, image=None,
    mv_image_front=handle_file(str(ROOT / 'front.png')),
    mv_image_back=handle_file(str(ROOT / 'back.png')),
    mv_image_left=handle_file(str(ROOT / 'left.png')),
    mv_image_right=None,
    steps=5, guidance_scale=5.0, seed=1234,
    octree_resolution=384, check_box_rembg=True,
    num_chunks=8000, randomize_seed=False,
    api_name='/shape_generation' if args.shape_only else '/generation_all',
)
print('SUBMITTED once', flush=True)
previous = None
while not job.done():
    status = str(job.status())
    if status != previous:
        print(status, flush=True)
        previous = status
    time.sleep(5)
try:
    result = job.result()
    (ROOT / f'{stage}-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('COMPLETED', repr(result)[:1500], flush=True)
except Exception as exc:
    (ROOT / f'{stage}-error.txt').write_text(str(exc), encoding='utf-8')
    print('FAILED', str(exc), flush=True)
    raise
