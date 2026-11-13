"""One official multi-view reconstruction using the approved, separated T-pose."""
import json, time, argparse
from pathlib import Path
from gradio_client import Client, handle_file
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--textured',action='store_true')
args=parser.parse_args()
stage='textured' if args.textured else 'shape'
REF=ROOT.parent/'references-v2/t-pose-views-v1'
params=dict(caption=None,image=None,mv_image_front=handle_file(str(REF/'front.png')),
    mv_image_back=handle_file(str(REF/'back.png')),mv_image_left=handle_file(str(REF/'left.png')),
    mv_image_right=None,steps=5,guidance_scale=5.0,seed=1234,octree_resolution=512,
    check_box_rembg=True,num_chunks=8000,randomize_seed=False)
(ROOT/'generation-settings.json').write_text(json.dumps({'service':'tencent/Hunyuan3D-2mv','input':str(REF),'steps':5,'octree_resolution':512,'seed':1234,'notes':'Turbo native 5-step setting; highest UI octree resolution. Three-quarter image reserved for QA, not mislabeled as right view.'},indent=2),encoding='utf-8')
try:
    client=Client('https://tencent-hunyuan3d-2mv.hf.space',download_files=str(ROOT/'downloads'))
    job=client.submit(**params,api_name='/generation_all' if args.textured else '/shape_generation')
    print('SUBMITTED once',flush=True)
    previous=None
    while not job.done():
        status=str(job.status())
        if status!=previous: print(status,flush=True);previous=status
        time.sleep(5)
    result=job.result()
    (ROOT/f'{stage}-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('COMPLETED',repr(result)[:1000],flush=True)
except Exception as exc:
    (ROOT/f'{stage}-error.txt').write_text(str(exc),encoding='utf-8')
    raise
