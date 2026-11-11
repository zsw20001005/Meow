"""Recover source-video detail at 2x resolution while retaining approved poses.

The reviewed matte is the geometry guide. Original RGB supplies interior detail;
interpolated poses use registered source detail, with disagreement falling back
to the reviewed pixels. No new action frames or timing are invented.
"""
from pathlib import Path
import argparse, json, math, shutil, hashlib
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/lulu-hires'
BASE=WORK/'original'
OUT=WORK/'assets'
ASSETS=ROOT/'windows/Meow.Windows/Assets/Lulu'
VIDEOS=ROOT/'build/lulu-jimeng'

def initial_bounds(path):
    reader=imageio_ffmpeg.read_frames(str(path),pix_fmt='rgb24',output_params=['-vf','fps=24,scale=-2:360'])
    meta=next(reader); im=Image.frombytes('RGB',meta['size'],next(reader)); reader.close()
    r,g,b=im.split(); low=ImageChops.darker(ImageChops.darker(r,g),b); high=ImageChops.lighter(ImageChops.lighter(r,g),b)
    eligible=ImageChops.multiply(low.point(lambda v:255 if v>145 else 0),ImageChops.subtract(high,low).point(lambda v:255 if v<42 else 0))
    pad=Image.new('L',(im.width+2,im.height+2),255); pad.paste(eligible,(1,1)); ImageDraw.floodfill(pad,(0,0),128)
    alpha=ImageChops.invert(pad.crop((1,1,im.width+1,im.height+1)).point(lambda v:255 if v==128 else 0)).filter(ImageFilter.GaussianBlur(.35))
    left,top,right,bottom=alpha.point(lambda v:255 if v>160 else 0).getbbox()
    scale=256*.77/(bottom-top)
    offset=(round(128-(left+right)/2*scale)*2,round(256*.85-bottom*scale)*2)
    return (round(im.width*scale)*2,round(im.height*scale)*2),offset

cache_key=None; cache_frames=None
def native_frames(path,group,clip):
    global cache_key,cache_frames
    framing='video' if group=='Video' else 'walk' if clip in ['approach','depart'] else 'bed'
    key=(str(path),framing)
    if key==cache_key:return cache_frames
    cache_frames=None
    if framing=='video': target,offset=initial_bounds(path); canvas=(512,512)
    elif framing=='walk':
        m=json.loads((BASE/'Bed/manifest.json').read_text('utf-8-sig')); factor=m['render']['scale']*256/200
        target=(round(512*factor)*2,round(288*factor)*2)
        offset=(round(128-256*factor)*2,round(m['render']['y']*256/200)*2); canvas=(512,512)
    else: target=(1024,576); offset=(0,0); canvas=target
    reader=imageio_ffmpeg.read_frames(str(path),pix_fmt='rgb24',output_params=['-vf',f'fps=24,scale={target[0]}:{target[1]}:flags=lanczos'])
    next(reader); frames=[]
    for raw in reader:
        im=Image.frombytes('RGB',target,raw)
        if im.size!=canvas or offset!=(0,0):
            framed=Image.new('RGB',canvas,'white'); framed.paste(im,offset); im=framed
        frames.append(np.array(im))
    cache_key=key; cache_frames=frames
    return frames

def recover(guide,native=None,register=False):
    a=np.array(guide).astype(np.float32)/255
    h,w=a.shape[:2]; size=(w*2,h*2)
    alpha=cv2.resize(a[:,:,3],size,interpolation=cv2.INTER_CUBIC)
    # Reconstruct a subpixel contour from the low-resolution matte, rather than
    # magnifying its staircase. Only alpha is smoothed; original RGB stays sharp.
    alpha=cv2.GaussianBlur(alpha,(0,0),.95)
    alpha=np.clip((alpha-.035)/.93,0,1)
    premul=cv2.resize(a[:,:,:3]*a[:,:,3:],size,interpolation=cv2.INTER_CUBIC)
    raw_alpha=cv2.resize(a[:,:,3],size,interpolation=cv2.INTER_CUBIC)
    rgb=np.clip(premul/np.maximum(raw_alpha[:,:,None],.001),0,1)
    if native is not None:
        candidate=native.astype(np.float32)/255
        if register:
            target=np.uint8(np.clip((a[:,:,:3]*a[:,:,3:]+1-a[:,:,3:])*255,0,255))
            source=cv2.resize(native,(w,h),interpolation=cv2.INTER_AREA)
            flow=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_FAST).calc(cv2.cvtColor(target,cv2.COLOR_RGB2GRAY),cv2.cvtColor(source,cv2.COLOR_RGB2GRAY),None)
            flow=cv2.resize(flow,size,interpolation=cv2.INTER_LINEAR)*2
            yy,xx=np.mgrid[:h*2,:w*2].astype(np.float32)
            candidate=cv2.remap(candidate,xx+flow[:,:,0],yy+flow[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=(1,1,1))
        distance=cv2.distanceTransform((alpha>.985).astype(np.uint8),cv2.DIST_L2,5)
        weight=np.clip((distance-1)/3,0,1)
        # Misregistered limbs or prop regions retain their reviewed pixels.
        mismatch=np.mean(np.abs(candidate-rgb),axis=2)
        weight*=np.clip((.24-mismatch)/.12,0,1)
        rgb=rgb*(1-weight[:,:,None])+candidate*weight[:,:,None]
    rgba=np.dstack((rgb,alpha))
    rgba[alpha<.002]=0
    return Image.fromarray(np.uint8(np.clip(rgba*255+.5,0,255)))

def load_frame(group,clip,index,m):
    w=clip.get('width',m.get('cellSize',m.get('width'))); h=clip.get('height',m.get('cellSize',m.get('height')))
    page=m.get('pageFrames',clip['frames']); local=index%page
    filename=clip.get('file',f"{clip['_key']}-{index//page}.png")
    path=BASE/group/filename
    if load_frame.path!=path:
        load_frame.image=Image.open(path).convert('RGBA');load_frame.path=path
    x,y=local%m['columns']*w,local//m['columns']*h
    return load_frame.image.crop((x,y,x+w,y+h))
load_frame.path=None;load_frame.image=None

def main():
    p=argparse.ArgumentParser();p.add_argument('--preview',action='store_true');args=p.parse_args()
    for group in ['Video','Bed']:
        if not (BASE/group).exists():shutil.copytree(ASSETS/group,BASE/group)
        (OUT/group).mkdir(parents=True,exist_ok=True)
    report=[];samples=[]
    for group in ['Video','Bed']:
        m=json.loads((BASE/group/'manifest.json').read_text('utf-8-sig'))
        revised=json.loads(json.dumps(m))
        revised.update(columns=4,pageFrames=24)
        if group=='Video':revised['cellSize']=512
        else:revised.update(pixelScale=2,assetPrefix='hd-')
        for key,clip in m['clips'].items():
            if key=='fall':continue
            if args.preview and key not in ['idle','eat','approach','depart','loop']:continue
            clip={**clip,'_key':key}
            native=None
            if 'source' in clip:
                path=(VIDEOS if group=='Video' else VIDEOS/'s5-floor-bed')/clip['source']
                if path.exists():native=native_frames(path,group,key)
            if key in ['entry-walk','wake-walk']:
                native=native_frames(VIDEOS/'s5-floor-bed'/('entry-r3.mp4' if key=='entry-walk' else 'wake.mp4'),group,key)
            nframes=clip['frames']; page_image=None
            indices=[0,nframes//3,nframes-1] if args.preview else range(nframes)
            for i in indices:
                old=load_frame(group,clip,i,m)
                raw=None;register=False
                if native is not None:
                    if group=='Video':
                        position=round(clip['interval'][0]*24)+i
                        if key=='walk': position=round(clip['interval'][0]*24)+4+round(i*21/53)%21;register=True
                    elif key=='wake':
                        position=i*24/clip.get('fps',m['fps'])
                        register=i/clip.get('fps',m['fps'])>=3.5 and i%5!=0
                        if not register:position=math.floor(position+1e-7)
                    else:
                        position=clip.get('sourceStart',0)*24+i*24/clip.get('fps',m['fps'])
                        register=abs(position-round(position))>.001
                    raw=native[min(len(native)-1,round(position))]
                frame=recover(old,raw,register)
                if i==nframes//3 or args.preview:samples.append((f'{group}/{key} {i}',old,frame))
                if not args.preview:
                    local=i%24
                    if local==0:page_image=Image.new('RGBA',(frame.width*4,frame.height*math.ceil(min(24,nframes-i)/4)))
                    page_image.paste(frame,(local%4*frame.width,local//4*frame.height))
                    if local==23 or i==nframes-1:page_image.save(OUT/group/f'hd-{key}-{i//24}.png',compress_level=3)
            if group=='Video':revised['clips'][key]['file']=f'hd-{key}-{{page}}.png'
            report.append({'group':group,'clip':key,'frames':nframes,'nativeRGB':native is not None})
            print(group,key,nframes,'native' if native is not None else 'reviewed transition',flush=True)
        if group=='Video':revised['clips']['fall']['file']=revised['clips']['drag']['file']
        if not args.preview:
            if group=='Bed':
                for name in ['arrive-bed','leave-bed','arrive-character','leave-character','entry-first','entry-last','loop-first','loop-last','wake-first','wake-last']:
                    old=Image.open(BASE/group/(name+'.png')).convert('RGBA')
                    source,index=('entry-r3.mp4',0) if name.startswith('arrive') else ('wake.mp4',112) if name.startswith('leave') else (m['clips'][name.split('-')[0]]['source'],0 if name.endswith('first') else {'entry':239,'loop':138,'wake':173}[name.split('-')[0]])
                    originals=native_frames(VIDEOS/'s5-floor-bed'/source,group,'static')
                    recover(old,originals[min(index,len(originals)-1)]).save(OUT/group/f'hd-{name}.png')
            (OUT/group/'manifest.json').write_text(json.dumps(revised,ensure_ascii=False,indent=2),'utf-8')
    for page in range(0,len(samples),4):
        sheet=Image.new('RGB',(1024,4*344),'#777777');d=ImageDraw.Draw(sheet)
        for row,(name,before,after) in enumerate(samples[page:page+4]):
            d.text((5,row*344+5),name+' | current / source-detail 2x',fill='white')
            for col,im in enumerate([before,after]):
                bg=Image.new('RGBA',im.size,'#172131');bg.alpha_composite(im);bg=bg.convert('RGB');scale=min(512/im.width,320/im.height);bg=bg.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
                sheet.paste(bg,(col*512,row*344+24))
        sheet.save(WORK/f'{"preview" if args.preview else "review"}-{page//4}.png')
    (WORK/('preview.json' if args.preview else 'build.json')).write_text(json.dumps(report,indent=2),'utf-8')

if __name__=='__main__':main()
