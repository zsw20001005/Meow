"""Audit white regions in all video actions; apply only reviewed background regions."""
from pathlib import Path
import argparse,json,shutil,hashlib
import numpy as np,cv2
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'windows/Meow.Windows/Assets/Lulu/Video';WORK=ROOT/'build/lulu-action-gaps';SOURCE=WORK/'original'

def clean(frame,key,index):
    """Reviewed empty spaces only; preserve eyes, props and the outer silhouette."""
    a=np.array(frame);rgb=a[:,:,:3].astype(np.float32);alpha=a[:,:,3]/255.
    lo=rgb.min(2);span=rgb.max(2)-lo;roi=np.zeros(alpha.shape,bool)
    if key=='happy':roi[205:285,305:380]=True
    elif key=='wave':roi[190:285,135:215]=True
    elif key=='play':
        roi[275:340,150:190]=True
        roi[285:345,335:370]=True
        # Reviewed ball silhouettes, including white panels above blue stripes.
        # Colour-only ball detection cuts holes in those white panels. A slightly
        # conservative crown envelope preserves the complete prop in every frame.
        ball_tops={69:385,70:389,71:392,72:396,73:399,74:403,75:407,
                   76:411,79:420,80:426,81:431,82:439}
        if index in ball_tops:
            for x in range(220,290):
                bottom=ball_tops[index]-2+(x-263)**2/120
                roi[380:min(438,int(bottom)),x]=True
    else:return frame.copy(),0
    seed=roi&(lo>230)&(span<24)&(alpha>.1)
    candidate=roi&(lo>145)&(span<55)&(alpha>.002)
    n,labels,stats,_=cv2.connectedComponentsWithStats(candidate.astype(np.uint8))
    remove=np.zeros_like(roi)
    for label in np.unique(labels[seed]):
        if label and stats[label,4]>=3:remove|=labels==label
    if not remove.any():return frame.copy(),0
    soft=cv2.GaussianBlur(remove.astype(np.float32),(0,0),.85)
    soft[cv2.erode(remove.astype(np.uint8),np.ones((3,3),np.uint8))>0]=1
    result_alpha=alpha*(1-soft)
    rim=cv2.dilate(remove.astype(np.uint8),np.ones((9,9),np.uint8))>0
    inside=(alpha>.99)&(~rim)&(span>55)
    _,nearest=cv2.distanceTransformWithLabels((~inside).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    colors=np.zeros((int(nearest.max())+1,3),np.float32);colors[nearest[inside]]=rgb[inside];foreground=colors[nearest]
    edge=(soft>.01)&(result_alpha>.001)
    rgb[edge]=foreground[edge]
    white=255-foreground;energy=(white*white).sum(2)
    mix=((rgb-foreground)*white).sum(2)/np.maximum(energy,1)
    residual=np.sqrt(np.mean((rgb-foreground-white*mix[:,:,None])**2,axis=2))
    eligible=rim&(~remove)&roi&(result_alpha>.001)&(energy>1000)&(residual<22)&(mix>.04)
    spill=np.where(eligible,np.clip(mix,0,.9),0)
    rgb=np.clip((rgb-255*spill[:,:,None])/(1-spill[:,:,None]),0,255);result_alpha*=1-spill
    # The anti-alias kernel must not modify a prop just below the reviewed ROI.
    changed=roi&rim
    result=a.copy();result[changed,:3]=np.uint8(rgb[changed]);result[changed,3]=np.uint8(np.clip(result_alpha[changed]*255+.5,0,255));result[result[:,:,3]==0]=0
    return Image.fromarray(result),int(np.any(result!=a,axis=2).sum())

def apply_cleanup(manifest):
    out=WORK/'fixed';out.mkdir(exist_ok=True);records=[];samples=[]
    for key in ['happy','wave','play']:
        c=manifest['clips'][key]
        for start in range(0,c['frames'],24):
            name=c['file'].replace('{page}',str(start//24));atlas=Image.open(SOURCE/name).convert('RGBA');output=atlas.copy();total=0
            for local in range(min(24,c['frames']-start)):
                x=local%4*512;y=local//4*512;f=atlas.crop((x,y,x+512,y+512));fixed,count=clean(f,key,start+local);output.paste(fixed,(x,y));total+=count
                records.append({'clip':key,'frame':start+local,'changedPixels':count})
                if (key,start+local) in [('happy',45),('wave',37),('play',79)]:samples.append((key,f,fixed))
            if total:output.save(out/name,compress_level=3)
    sheet=Image.new('RGB',(1024,3*532),'#172131');draw=ImageDraw.Draw(sheet)
    for row,(key,before,after) in enumerate(samples):
        draw.text((8,row*532+4),key+' | before / after',fill='white')
        for col,f in enumerate([before,after]):
            bg=Image.new('RGBA',f.size,'#172131');bg.alpha_composite(f);sheet.paste(bg.convert('RGB'),(col*512,row*532+20))
    sheet.save(WORK/'before-after.png')
    (WORK/'cleanup.json').write_text(json.dumps(records,indent=2),'utf-8')
    print('Staged corrected pages:',len(list(out.glob('*.png'))),'changed frames:',sum(r['changedPixels']>0 for r in records),flush=True)

def regions(im):
    a=np.array(im);rgb=a[:,:,:3].astype(np.float32)
    mask=(rgb.min(2)>230)&(rgb.max(2)-rgb.min(2)<24)&(a[:,:,3]>100)
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    found=[(i,[int(v) for v in stats[i]]) for i in range(1,n) if stats[i,4]>=12]
    return labels,found

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
    if not SOURCE.exists():
        SOURCE.mkdir(parents=True)
        for path in [ASSETS/'manifest.json',*ASSETS.glob('hd-*.png')]:shutil.copyfile(path,SOURCE/path.name)
    manifest=json.loads((SOURCE/'manifest.json').read_text('utf-8-sig'));records=[];examples=[]
    if args.apply:
        apply_cleanup(manifest)
        return
    for key,clip in manifest['clips'].items():
        if key=='fall':continue
        best=(0,None,0,[]);detected=[]
        for index in range(clip['frames']):
            local=index%24
            if local==0:atlas=Image.open(SOURCE/clip['file'].replace('{page}',str(index//24))).convert('RGBA')
            x,y=local%4*512,local//4*512;frame=atlas.crop((x,y,x+512,y+512))
            labels,found=regions(frame)
            if found:detected.append({'frame':index,'regions':[box for _,box in found]})
            score=sum(box[4] for _,box in found if box[1]>200)
            if score>best[0]:best=(score,frame,index,found)
        records.append({'clip':key,'frames':clip['frames'],'detected':detected})
        if best[1] is not None:examples.append((key,best[1],best[2],best[3]))
        print(key,len(detected),'frames with white',best[0],flush=True)
    for page in range(0,len(examples),9):
        sheet=Image.new('RGB',(900,3*320),'#172131');draw=ImageDraw.Draw(sheet)
        for j,(key,im,index,found) in enumerate(examples[page:page+9]):
            bg=Image.new('RGBA',im.size,'#172131');bg.alpha_composite(im);bg=bg.convert('RGB');d=ImageDraw.Draw(bg)
            for _,(x,y,w,h,area) in found:
                if y>200:d.rectangle((x,y,x+w,y+h),outline='red',width=2)
            px,py=j%3*300,j//3*320;sheet.paste(bg.resize((300,300)),(px,py+20));draw.text((px+4,py+3),f'{key} frame {index}',fill='white')
        sheet.save(WORK/f'audit-{page//9}.png')
    (WORK/'audit.json').write_text(json.dumps(records,indent=2),'utf-8')

if __name__=='__main__':main()
