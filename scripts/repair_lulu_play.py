"""Separate the existing play character from its damaged ball matte.

The ball reuses the approved frame's colours, projected onto a round surface.
Only play atlases are staged. No timing or runtime code changes are made.
"""
from pathlib import Path
import json, shutil, hashlib, math
import numpy as np
import cv2
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'windows/Meow.Windows/Assets/Lulu/Video'
WORK=ROOT/'build/lulu-play-repair'
SOURCE=WORK/'original'
OUT=WORK/'fixed'

def frame(index):
    a=Image.open(SOURCE/f'hd-play-{index//24}.png').convert('RGBA')
    local=index%24;x=local%4*512;y=local//4*512
    return a.crop((x,y,x+512,y+512))

def character(im,index,reference,native):
    a=np.array(im);rgb=a[:,:,:3].astype(np.float32);alpha=a[:,:,3]/255.
    yy,xx=np.indices(alpha.shape)
    lower=yy>=355
    # Yellow/orange character and neutral/blue prop are separate materials.
    # Remove the complete old prop, enclosed white backdrop and floor debris.
    # Use the actual source colour for segmentation: previous decontamination
    # had painted some prop-edge pixels yellow, making them look like toes.
    warmth=native[:,:,0].astype(float)-native[:,:,2].astype(float)
    keep=np.clip((warmth-75)/40,0,1)
    keep=keep*keep*(3-2*keep)
    alpha[lower]*=keep[lower]
    clean=a.copy();clean[:,:,3]=np.uint8(alpha*255+.5)
    clean[lower,:3]=native[lower]
    rim=lower&(keep>0)&(keep<1)&(alpha>0)
    inside=lower&(warmth>110)&(alpha>.99)
    _,labels=cv2.distanceTransformWithLabels((~inside).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    colors=np.zeros((int(labels.max())+1,3),np.float32);colors[labels[inside]]=native[inside]
    clean[rim,:3]=np.uint8(colors[labels[rim]])
    # Restore only previously ball-occluded toes, behind the new ball. During
    # the kick the lifted left foot is retained from the current original pose.
    if 0<index<88:
        ref=np.array(reference).astype(np.float32)/255
        restore=(xx>185)&(xx<330)
        if 48<=index<=71:restore&=xx>270
        weight=np.clip((yy-389)/12,0,1)*restore
        weight=weight*weight*(3-2*weight)
        current=clean.astype(np.float32)/255
        blended_alpha=current[:,:,3]*(1-weight)+ref[:,:,3]*weight
        premul=current[:,:,:3]*current[:,:,3:]*(1-weight[:,:,None])+ref[:,:,:3]*ref[:,:,3:]*weight[:,:,None]
        clean=np.uint8(np.clip(np.dstack((premul/np.maximum(blended_alpha[:,:,None],.0001),blended_alpha))*255+.5,0,255))
    return Image.fromarray(clean)

def pose(index):
    if index<=30:
        t=max(0,1-index/30);cy=404+166*t**3;r=38+16*t**3;cx=259
        angle=(cy-404)/43
    elif index<=54:cx,cy,r,angle=259,404,38,0
    else:
        t=(index-54)/36;cx=259+12*t*t;cy=404+172*t*t;r=38+16*t
        angle=-(cy-404)/43
    return cx,cy,r,angle

def ball(texture,index):
    cx,cy,r,angle=pose(index)
    if cy-r>=512:return None,None
    left=math.floor(cx-r-2);top=math.floor(cy-r-2);size=math.ceil(2*r+5);scale=3
    yy,xx=np.mgrid[:size*scale,:size*scale].astype(np.float32)
    nx=(left+(xx+.5)/scale-cx)/r;ny=(top+(yy+.5)/scale-cy)/r
    squared=nx*nx+ny*ny;nz=np.sqrt(np.maximum(0,1-squared))
    sy=ny*math.cos(angle)+nz*math.sin(angle)
    sz=np.sqrt(np.maximum(0,1-nx*nx-sy*sy))
    # Symmetric back hemisphere extends the original beach-ball panel pattern.
    colors=cv2.remap(texture,259+nx*35.5,404+sy*35.5,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    light=lambda x,y,z: .72+.28*np.maximum(0,(-.25*x-.4*y+.88*z)/1.0)
    colors=colors/light(nx,sy,sz)[:,:,None]*light(nx,ny,nz)[:,:,None]
    rgba=np.dstack((np.clip(colors,0,255),np.where(squared<=1,255,0))).astype(np.uint8)
    im=Image.fromarray(rgba).resize((size,size),Image.Resampling.LANCZOS)
    return im,(left,top)

def main():
    WORK.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    if not SOURCE.exists():
        SOURCE.mkdir()
        for p in [ASSETS/'manifest.json',*ASSETS.glob('hd-play-*.png')]:shutil.copyfile(p,SOURCE/p.name)
    m=json.loads((SOURCE/'manifest.json').read_text('utf-8-sig'));c=m['clips']['play']
    assert m['cellSize']==512 and c['frames']==125 and c['fps']==24
    from build_lulu_hires import native_frames
    native=native_frames(ROOT/'build/lulu-jimeng'/c['source'],'Video','play')
    source_start=round(c['interval'][0]*24)
    texture=native[source_start+40].astype(np.float32)
    Image.fromarray(np.uint8(texture)).save(WORK/'native-reference.png')
    early=frame(0);late=frame(90);frames=[];records=[]
    for i in range(c['frames']):
        original=frame(i);reference=early if i<48 else late
        f=character(original,i,reference,native[source_start+i])
        if i in [10,55,75]:f.save(WORK/f'character-{i}.png')
        prop,position=ball(texture,i)
        if prop is not None:f.alpha_composite(prop,position)
        a=np.array(original);b=np.array(f)
        assert np.array_equal(a[:355],b[:355]),('upper character changed',i)
        yy,xx=np.indices(b.shape[:2]);cx,cy,r,_=pose(i)
        distance=np.hypot(xx+.5-cx,yy+.5-cy)
        white=(b[:,:,:3].min(2)>225)&(b[:,:,:3].max(2)-b[:,:,:3].min(2)<35)&(b[:,:,3]>80)
        assert not np.any(white&(yy>=355)&(distance>r+3)),('backdrop outside ball',i)
        if prop is not None:
            assert np.all(b[:,:,3][distance<r-2]>250),('hole in ball',i)
        records.append({'frame':i,'changedPixels':int(np.any(a!=b,axis=2).sum()),'ball':pose(i)})
        frames.append(f)
    for start in range(0,c['frames'],24):
        name=f'hd-play-{start//24}.png';a=Image.open(SOURCE/name).convert('RGBA')
        for local,f in enumerate(frames[start:start+24]):a.paste(f,(local%4*512,local//4*512))
        a.save(OUT/name,compress_level=3)
    # Native detail review plus a compact real-time motion preview.
    sheet=Image.new('RGB',(1200,650),'#172131');draw=ImageDraw.Draw(sheet)
    for j,i in enumerate(range(0,125,5)):
        f=frames[i].crop((155,345,355,455));bg=Image.new('RGBA',f.size,'#172131');bg.alpha_composite(f)
        x=j%6*200;y=j//6*130;sheet.paste(bg.convert('RGB'),(x,y+20));draw.text((x+3,y+3),str(i),fill='white')
    sheet.save(WORK/'fixed-contact.png')
    preview=[]
    for i,f in enumerate(frames):
        bg=Image.new('RGBA',(512,512),'#172131');bg.alpha_composite(f)
        preview.append(bg.convert('RGB').resize((320,320),Image.Resampling.LANCZOS))
    preview[0].save(WORK/'play-preview.webp',save_all=True,append_images=preview[1:],duration=[42,42,41]*(len(preview)//3)+[42]*(len(preview)%3),loop=0,lossless=True)
    (WORK/'repair.json').write_text(json.dumps({'frames':records,'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.png')}},indent=2),'utf-8')
    print('PASS',len(frames),'frames: upper character unchanged, ball interior opaque, no lower white backdrop outside ball.')

if __name__=='__main__':main()
