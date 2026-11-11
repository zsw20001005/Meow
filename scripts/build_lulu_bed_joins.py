"""Build short, registered bed-scene joins from WPF-exported RGBA endpoints.

Run Meow.exe --bed-seamframes on the unmodified source assets first. These
joins preserve endpoint poses and warp the premultiplied foreground before
mixing, rather than fading two unregistered character silhouettes.
"""
from pathlib import Path
import argparse,json,sys,math
import cv2
import numpy as np
from PIL import Image,ImageDraw

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('--output-dir',type=Path,default=root/'windows/Meow.Windows/Assets/Lulu/Bed')
parser.add_argument('--review-dir',type=Path,default=root/'build/lulu-jimeng/s5-floor-bed/join-review')
parser.add_argument('--clips',nargs='+',choices=['start','approach','sleep','breath','wake','return','idle'],default=['start','approach','sleep','breath','wake','return','idle'])
args=parser.parse_args();source=args.source;out=args.output_dir
review=args.review_dir;review.mkdir(parents=True,exist_ok=True)
m=json.loads((out/'manifest.json').read_text())
for name in args.clips:
    a=np.array(Image.open(source/f'{name}-from.png').convert('RGBA'),dtype=np.float32)/255
    b=np.array(Image.open(source/f'{name}-to.png').convert('RGBA'),dtype=np.float32)/255
    h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w].astype(np.float32)
    def gray(v):
        rgb=v[:,:,:3]*v[:,:,3:]+1-v[:,:,3:]
        return cv2.cvtColor(np.uint8(np.clip(rgb*255,0,255)),cv2.COLOR_RGB2GRAY)
    flow=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    ab=flow.calc(gray(a),gray(b),None);ba=flow.calc(gray(b),gray(a),None)
    a[:,:,:3]*=a[:,:,3:];b[:,:,:3]*=b[:,:,3:]
    duration=float((source/f'{name}.txt').read_text());count=round(duration*60)+1
    frames=[]
    for i in range(count):
        t=i/(count-1)
        # Inverse mapping with a few fixed-point refinements follows the actual
        # displacement field, including feet and silhouette edges.
        def warp(im,field,fraction):
            mx=xx.copy();my=yy.copy()
            for _ in range(4):
                f=cv2.remap(field,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
                mx=xx-fraction*f[:,:,0];my=yy-fraction*f[:,:,1]
            return cv2.remap(im,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        wa=warp(a,ab,t);wb=warp(b,ba,1-t)
        blended=wa*(1-t)+wb*t
        alpha=blended[:,:,3:];blended[:,:,:3]=np.divide(blended[:,:,:3],alpha,out=np.zeros_like(blended[:,:,:3]),where=alpha>1e-6)
        # Interpolate one opaque contour rather than leaving two translucent
        # arms/feet when an occluded region has imperfect flow correspondence.
        def distance(v):
            mask=np.uint8(v[:,:,3]>.5)
            return cv2.distanceTransform(mask,cv2.DIST_L2,5)-cv2.distanceTransform(1-mask,cv2.DIST_L2,5)
        contour=distance(wa)*(1-t)+distance(wb)*t
        blended[:,:,3]=np.clip(contour+.5,0,1)
        frames.append(Image.fromarray(np.uint8(np.clip(blended*255,0,255))))
    # Exact endpoints avoid a one-frame resampling mismatch at either cut.
    frames[0]=Image.open(source/f'{name}-from.png').convert('RGBA');frames[-1]=Image.open(source/f'{name}-to.png').convert('RGBA')
    atlas=Image.new('RGBA',(w*m['columns'],h*math.ceil(count/m['columns'])))
    for i,f in enumerate(frames):atlas.paste(f,(i%m['columns']*w,i//m['columns']*h))
    atlas.save(out/f'join-{name}-0.png',compress_level=3)
    m['clips']['join-'+name]=dict(frames=count,fps=60,width=w,height=h,durationSeconds=duration,method='bidirectional registered RGBA warp')
    sheet=Image.new('RGB',(w*3,h+30),'#34475a');d=ImageDraw.Draw(sheet)
    for j,n in enumerate([0,count//2,count-1]):sheet.paste(frames[n],(j*w,0),frames[n]);d.text((j*w+4,h+4),f'{name} frame {n}/{count-1}',fill='white')
    sheet.save(review/f'{name}.jpg')
    print(name,count,flush=True)
(out/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
