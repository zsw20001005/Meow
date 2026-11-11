"""Remove enclosed white-backdrop pockets and neutral floor slivers from HD bed frames."""
from pathlib import Path
import argparse,json,math,shutil
import cv2,numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'build/lulu-hires';SOURCE=WORK/'before-gap-cleanup';OUT=WORK/'assets/Bed'

def clean(im):
    rgba=np.array(im); rgb=rgba[:,:,:3].astype(np.float32); alpha=rgba[:,:,3].astype(np.float32)/255
    h,w=alpha.shape; yy,xx=np.indices(alpha.shape)
    lo,hi=rgb.min(2),rgb.max(2)
    # Eyes and glasses are above the standing torso; small highlights are not
    # background pockets. The source cream mattress is warmer than this white.
    seed=(lo>242)&(hi-lo<14)&(alpha>.4)&(yy>h*.38)
    n,labels,stats,_=cv2.connectedComponentsWithStats(seed.astype(np.uint8))
    holes=np.zeros_like(seed)
    for k in range(1,n):
        x,y,cw,ch,area=stats[k]
        if area>=120 and min(cw,ch)>=8 and max(cw,ch)>=24:holes|=labels==k
    # Grow only a narrow rim; do not flood into pale-blue pillow highlights.
    near=cv2.dilate(holes.astype(np.uint8),np.ones((7,7),np.uint8))>0
    holes|=near&(lo>235)&(hi-lo<18)&(alpha>.05)
    distance=cv2.distanceTransform((alpha>.05).astype(np.uint8),cv2.DIST_L2,5)
    floor=(yy>h*.55)&(distance<6)&(lo>210)&(hi-lo<22)&(alpha>0)
    # Follow the actual blue binding and dark tan underside. Pale spill below
    # that line is floor, even when it is connected to the cream mattress.
    blue=(rgb[:,:,2]-rgb[:,:,0]>8)&(rgb[:,:,1]-rgb[:,:,0]>4)&(rgb[:,:,0]>70)&(rgb[:,:,2]<225)&(alpha>.6)&(yy>h*.62)&(yy<h*.90)&(xx>w*.30)
    right_columns=np.where(blue[:,int(w*.65):].any(axis=0))[0]+int(w*.65)
    if len(right_columns)>20:
        base_y=np.median([np.where(blue[:,x])[0][-1] for x in right_columns])
        blue&=yy>base_y-h*.045
    line=np.full(w,np.nan,np.float32)
    for x in np.where(blue.any(axis=0))[0]:
        last=int(np.where(blue[:,x])[0][-1]); end=min(h,last+13)
        rows=np.arange(last+1,end)
        brown=(rgb[rows,x,0]>rgb[rows,x,2]+5)&(rgb[rows,x,1]>rgb[rows,x,2]+3)&(hi[rows,x]<205)&(alpha[rows,x]>.4)
        if brown.any():
            candidates=rows[brown];line[x]=candidates[np.argmin(rgb[candidates,x].mean(1))]+2
    valid=np.where(np.isfinite(line))[0]
    if len(valid)>40:
        curve=np.interp(np.arange(w),valid,line[valid]).astype(np.float32)
        anchors=valid[(valid>w*.55)&(valid<w*.88)]
        if len(anchors)>40:
            fit=np.polyfit(anchors,line[anchors],1)
            anchors=anchors[np.abs(line[anchors]-np.polyval(fit,anchors))<5]
            if len(anchors)>30:
                fit=np.polyfit(anchors,line[anchors],1)
                curve[:int(w*.88)]=np.polyval(fit,np.arange(int(w*.88)))
        curve=cv2.GaussianBlur(cv2.medianBlur(curve[None,:],5),(0,0),1.2)[0]
        underneath=(yy>curve[None,:])&(xx>=max(w*.30,valid.min()-90))&(xx<=valid.max())
        floor|=underneath&(lo>100)&((hi-lo)/np.maximum(hi,1)<.45)&(alpha>0)
    remove=holes|floor
    if not remove.any():return im.copy(),0
    softened=cv2.GaussianBlur(remove.astype(np.float32),(0,0),.65)
    softened[cv2.erode(remove.astype(np.uint8),np.ones((3,3),np.uint8))>0]=1
    result_alpha=alpha*(1-softened)
    # Extend foreground colour into newly antialiased cut edges, never white.
    valid=(result_alpha>.95)&(~remove)&((lo<225)|(hi-lo>24))
    if valid.any():
        dist,nearest=cv2.distanceTransformWithLabels((~valid).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
        colors=np.zeros((int(nearest.max())+1,3),np.float32);colors[nearest[valid]]=rgb[valid]
        edge=(softened>.02)&(result_alpha>.002)&(dist<8)
        rgb[edge]=colors[nearest[edge]]
    rim=cv2.dilate(remove.astype(np.uint8),np.ones((13,13),np.uint8))>0
    inside=(result_alpha>.99)&(~rim)
    if inside.any():
        _,labels=cv2.distanceTransformWithLabels((~inside).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
        colors=np.zeros((int(labels.max())+1,3),np.float32);colors[labels[inside]]=rgb[inside]
        foreground=colors[labels];white=255-foreground;energy=(white*white).sum(2)
        mix=((rgb-foreground)*white).sum(2)/np.maximum(energy,1)
        residual=np.sqrt(np.mean((rgb-foreground-white*mix[:,:,None])**2,axis=2))
        eligible=rim&(result_alpha>.002)&(energy>1000)&(residual<25)&(mix>.04)
        spill=np.where(eligible,np.clip(mix,0,.90),0)
        rgb=np.clip((rgb-255*spill[:,:,None])/(1-spill[:,:,None]),0,255)
        result_alpha*=1-spill
    result=rgba.copy();result[:,:,:3]=np.uint8(np.clip(rgb,0,255));result[:,:,3]=np.uint8(np.clip(result_alpha*255+.5,0,255));result[result[:,:,3]<1]=0
    return Image.fromarray(result),int(remove.sum())

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
    if not SOURCE.exists():shutil.copytree(OUT,SOURCE)
    m=json.loads((SOURCE/'manifest.json').read_text());samples=[];records=[]
    for key,c in m['clips'].items():
        if key in ['approach','depart','entry-walk','wake-walk']:continue
        w=c.get('width',m['width'])*2;h=c.get('height',m['height'])*2
        worst=(0,None,None,0)
        for page,start in enumerate(range(0,c['frames'],24)):
            name=f'hd-{key}-{page}.png';atlas=Image.open(SOURCE/name).convert('RGBA');output=atlas.copy();removed=0
            for local in range(min(24,c['frames']-start)):
                x,y=local%4*w,local//4*h;frame=atlas.crop((x,y,x+w,y+h));fixed,pixels=clean(frame)
                removed+=pixels;output.paste(fixed,(x,y))
                if pixels>worst[0]:worst=(pixels,frame,fixed,start+local)
                if key=='entry' and start+local in [80,95,115,125,140]:samples.append((f'entry {start+local}',frame,fixed))
            if args.apply:output.save(OUT/name,compress_level=3)
            records.append({'file':name,'removedMaskPixels':removed})
        if worst[1] is not None:samples.append((f'{key} worst frame {worst[3]}',worst[1],worst[2]))
    for path in SOURCE.glob('hd-*.png'):
        if path.stem.rsplit('-',1)[-1].isdigit():continue
        fixed,removed=clean(Image.open(path).convert('RGBA'))
        if args.apply:fixed.save(OUT/path.name)
        records.append({'file':path.name,'removedMaskPixels':removed})
    for page in range(0,len(samples),3):
        sheet=Image.new('RGB',(1024,3*312),'#777777');draw=ImageDraw.Draw(sheet)
        for row,(label,before,after) in enumerate(samples[page:page+3]):
            draw.text((8,row*312+4),label+' | before / after',fill='white')
            for col,im in enumerate([before,after]):
                bg=Image.new('RGBA',im.size,'#172131');bg.alpha_composite(im);sheet.paste(bg.convert('RGB').resize((512,288),Image.Resampling.LANCZOS),(col*512,row*312+24))
        sheet.save(WORK/f'gap-cleanup-{page//3}.png')
    (WORK/'gap-cleanup.json').write_text(json.dumps({'applied':args.apply,'records':records},indent=2),'utf-8')
    print('Processed',len(records),'files; mask pixels',sum(r['removedMaskPixels'] for r in records))

if __name__=='__main__':main()
