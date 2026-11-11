"""Matte and loop the approved Google screen-edge clip without a gray panel."""
from pathlib import Path
import json, math, hashlib
import numpy as np
import cv2
from PIL import Image, ImageDraw
import imageio_ffmpeg
from match_lulu_edge_color import correction, recolor, MIDTONE_LIFT

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/lulu-edge-design'
OUT=ROOT/'windows/Meow.Windows/Assets/Lulu/Edge'

def matte(rgb):
    f=rgb.astype(np.float32);lo=f.min(2);span=f.max(2)-lo
    neutral=((lo>145)&(span<43))|((lo>85)&(span<21))
    # Only background-connected neutral regions are removed. Enclosed eye whites
    # remain part of the character, including during blinks.
    n,labels,stats,_=cv2.connectedComponentsWithStats(neutral.astype(np.uint8))
    outer=np.unique(np.concatenate([labels[0],labels[-1],labels[:,0],labels[:,-1]]))
    background=np.isin(labels,outer[outer!=0]);fg=(~background).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(fg)
    fg=np.uint8(lab==(1+np.argmax(st[1:,4])))
    # Remove neutral pockets well below the glasses, if the hands enclose one.
    yy,xx=np.indices(fg.shape)
    fg[(yy>670)&neutral]=0
    alpha=cv2.GaussianBlur(fg.astype(np.float32),(0,0),.7)
    inner=cv2.distanceTransform(fg,cv2.DIST_L2,5)
    outerdist=cv2.distanceTransform(1-fg,cv2.DIST_L2,5)
    valid=inner>5
    _,nearest=cv2.distanceTransformWithLabels((~valid).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    colors=np.zeros((int(nearest.max())+1,3),np.float32);colors[nearest[valid]]=f[valid];front=colors[nearest]
    bgvalid=outerdist>7
    _,nearestbg=cv2.distanceTransformWithLabels((~bgvalid).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    colors=np.zeros((int(nearestbg.max())+1,3),np.float32);colors[nearestbg[bgvalid]]=f[bgvalid];back=colors[nearestbg]
    direction=back-front;energy=(direction*direction).sum(2)
    mix=((f-front)*direction).sum(2)/np.maximum(energy,1)
    error=np.sqrt(np.mean((f-front-direction*mix[:,:,None])**2,axis=2))
    rim=(inner<6)&(outerdist<3)&(alpha>.001)
    spill=np.where(rim&(energy>900)&(error<25),np.clip(mix,0,.92),0)
    corrected=np.clip((f-back*spill[:,:,None])/np.maximum(1-spill[:,:,None],.08),0,255)
    alpha*=1-spill
    corrected[rim&(outerdist>0)]=front[rim&(outerdist>0)]
    result=np.dstack((corrected,alpha*255)).clip(0,255).astype(np.uint8)
    result[result[:,:,3]==0]=0
    return Image.fromarray(result)

def bridge(a,b,count):
    a=np.array(a).astype(np.float32)/255;b=np.array(b).astype(np.float32)/255
    h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w].astype(np.float32)
    def gray(v):return cv2.cvtColor(np.uint8((v[:,:,:3]*v[:,:,3:]+1-v[:,:,3:])*255),cv2.COLOR_RGB2GRAY)
    flow=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    ab=flow.calc(gray(a),gray(b),None);ba=flow.calc(gray(b),gray(a),None)
    a[:,:,:3]*=a[:,:,3:];b[:,:,:3]*=b[:,:,3:]
    result=[]
    for i in range(count):
        u=i/count;t=u*u*(3-2*u)
        def warp(v,field,fraction):
            mx=xx.copy();my=yy.copy()
            for _ in range(4):
                f=cv2.remap(field,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
                mx=xx-fraction*f[:,:,0];my=yy-fraction*f[:,:,1]
            return cv2.remap(v,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        wa=warp(a,ab,t);wb=warp(b,ba,1-t);v=wa*(1-t)+wb*t
        rgb=np.divide(v[:,:,:3],v[:,:,3:],out=np.zeros_like(v[:,:,:3]),where=v[:,:,3:]>1e-5)
        def distance(v):
            m=np.uint8(v[:,:,3]>.5)
            return cv2.distanceTransform(m,cv2.DIST_L2,5)-cv2.distanceTransform(1-m,cv2.DIST_L2,5)
        alpha=np.clip(distance(wa)*(1-t)+distance(wb)*t+.5,0,1)
        result.append(Image.fromarray(np.uint8(np.clip(np.dstack((rgb,alpha))*255,0,255))))
    return result

def main():
    OUT.mkdir(exist_ok=True)
    source=WORK/'google-edge-loop-r1.mp4';reader=imageio_ffmpeg.read_frames(str(source),pix_fmt='rgb24');meta=next(reader)
    originals=[];frames=[]
    for i,raw in enumerate(reader):
        rgb=np.array(Image.frombytes('RGB',meta['size'],raw));f=matte(rgb)
        originals.append(rgb);frames.append(f)
        if i%48==0:print('matted',i,flush=True)
    # One fixed crop for the entire loop. Never recenter each frame: hands must
    # remain anchored to the real screen edge while the head breathes.
    bounds=np.array([f.getbbox() for f in frames]);l=int(bounds[:,0].min())-8;t=int(bounds[:,1].min())-8
    r=int(bounds[:,2].max())+8;b=int(bounds[:,3].max())+8
    scale=496/(b-t);w=math.ceil((r-l)*scale)+16;w=math.ceil(w/8)*8;h=512
    packed=[]
    for f in frames:
        small=f.crop((l,t,r,b)).resize((round((r-l)*scale),496),Image.Resampling.LANCZOS)
        canvas=Image.new('RGBA',(w,h));canvas.paste(small,(8,8));packed.append(canvas)
    # Preserve the source action, then close its small pose mismatch with one
    # registered opaque contour instead of a translucent silhouette crossfade.
    join_count=12
    loop=packed+bridge(packed[-1],packed[0],join_count)[1:]
    color_delta=correction(loop[0])
    loop=[recolor(f,color_delta) for f in loop]
    for start in range(0,len(loop),24):
        page=Image.new('RGBA',(w*4,h*math.ceil(min(24,len(loop)-start)/4)))
        for local,f in enumerate(loop[start:start+24]):page.paste(f,(local%4*w,local//4*h))
        page.save(OUT/f'edge-{start//24}.png',compress_level=3)
    # Gray panel boundary from the upper empty background, independent of hands.
    profile=originals[0][50:180].mean(0).mean(1)
    panel_columns=np.where((profile<232)&(profile>150)&(np.arange(len(profile))>len(profile)*.5))[0]
    panel=int(panel_columns[0]) if len(panel_columns) else r-35
    manifest=dict(version=1,width=w,height=h,columns=4,pageFrames=24,frames=len(loop),fps=24,
                  anchorX=8+(panel-l)*scale,source=source.name,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  crop=[l,t,r,b],sourceFrames=len(frames),joinFrames=join_count-1,
                  colorMatch=dict(reference='Video/hd-idle-0.png frame 0',labOffsets=color_delta.tolist(),midtoneLift=MIDTONE_LIFT,alphaUnchanged=True))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),'utf-8')
    sheet=Image.new('RGB',(1200,800),'#172131');draw=ImageDraw.Draw(sheet)
    for j,i in enumerate(np.linspace(0,len(loop)-1,12).astype(int)):
        f=loop[i];bg=Image.new('RGBA',f.size,'#172131');bg.alpha_composite(f);bg.thumbnail((200,370));x=j%6*200;y=j//6*400;sheet.paste(bg.convert('RGB'),(x,y+24));draw.text((x+3,y+4),f'frame {i}',fill='white')
    sheet.save(WORK/'edge-matte-review.png')
    loop[0].save(WORK/'edge-cutout.png')
    print(json.dumps(manifest),flush=True)

if __name__=='__main__':main()
