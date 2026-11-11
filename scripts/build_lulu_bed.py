"""Package reviewed video segments with a shared camera transform; keep originals."""
from pathlib import Path
import json, math, hashlib, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter
import imageio_ffmpeg

root=Path(__file__).resolve().parents[1]
source=root/'build/lulu-jimeng/s5-floor-bed'
out=root/'windows/Meow.Windows/Assets/Lulu/Bed'
out.mkdir(parents=True,exist_ok=True)
w,h,cols,page_frames=512,288,4,48
def matte(im):
    r,g,b=im.split(); low=ImageChops.darker(ImageChops.darker(r,g),b); high=ImageChops.lighter(ImageChops.lighter(r,g),b)
    bg=ImageChops.multiply(low.point(lambda v:255 if v>230 else 0),ImageChops.subtract(high,low).point(lambda v:255 if v<23 else 0))
    padded=Image.new('L',(w+2,h+2),255);padded.paste(bg,(1,1));ImageDraw.floodfill(padded,(0,0),128)
    outside=padded.crop((1,1,w+1,h+1)).point(lambda v:255 if v==128 else 0)
    alpha=ImageChops.invert(outside)
    # Remove the neutral contact-shadow carpet under standing feet without erasing
    # the cream mattress. Its fixed lower edge is above row 227 in these takes.
    shadow=ImageChops.multiply(low.point(lambda v:255 if v>160 else 0),ImageChops.subtract(high,low).point(lambda v:255 if v<32 else 0))
    floor=Image.new('L',(w,h));fd=ImageDraw.Draw(floor)
    fd.rectangle((0,227,w,h),fill=255)
    fd.rectangle((0,150,209,h),fill=255) # standing/walking lane, separate from the cream mattress
    alpha=ImageChops.subtract(alpha,ImageChops.multiply(shadow,floor)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.35))
    rgba=im.convert('RGBA');rgba.putalpha(alpha);return rgba

previous=json.loads((out/'manifest.json').read_text()) if (out/'manifest.json').exists() else {'clips':{}}
manifest={'fps':24,'width':w,'height':h,'columns':cols,'pageFrames':page_frames,'clips':{k:v for k,v in previous['clips'].items() if k in ('approach','depart')},'previewOnly':True}
seams={}
all_frames={}
for key,name,end in [('entry','entry-r3.mp4',10),('loop','loop.mp4',139/24),('wake','wake.mp4',7.25)]:
    frames=[]
    if '--tracks-only' in sys.argv or ('--loop-only' in sys.argv and key != 'loop'):
        if previous['clips'].get(key,{}).get('fps',24)!=24:
            raise ValueError('Rebuild original 24 fps base clips before refreshing tracks; do not reinterpret resampled frames as 24 fps.')
        for i in range(round(end*24)):
            if i%page_frames==0: atlas=Image.open(out/f'{key}-{i//page_frames}.png').convert('RGBA')
            local=i%page_frames; xx=local%cols*w; yy=local//cols*h
            frames.append(atlas.crop((xx,yy,xx+w,yy+h)))
    else:
        r=imageio_ffmpeg.read_frames(str(source/name),pix_fmt='rgb24',output_params=['-vf',f'fps=24,scale={w}:{h}'])
        meta=next(r)
        for i,raw in enumerate(r):
            if i>=round(end*24):break
            frames.append(matte(Image.frombytes('RGB',(w,h),raw)))
        r.close()
    all_frames[key]=frames
    for page,start in enumerate(range(0,len(frames),page_frames)):
        group=frames[start:start+page_frames]
        atlas=Image.new('RGBA',(w*cols,h*math.ceil(len(group)/cols)))
        for i,frame in enumerate(group):atlas.paste(frame,(i%cols*w,i//cols*h))
        atlas.save(out/f'{key}-{page}.png',compress_level=3)
    manifest['clips'][key]={'frames':len(frames),'source':name,'endSeconds':end,'sha256':hashlib.sha256((source/name).read_bytes()).hexdigest()}
    seams[key]=(frames[0],frames[-1])
    for suffix,frame in [('first',frames[0]),('last',frames[-1])]:frame.save(out/f'{key}-{suffix}.png')

# Track the upper haircut, avoiding the muzzle, moving feet and bed outline.
# These roots describe world travel; the renderer derives its camera from them.
def root_x(frame):
    r,g,b,a=frame.split()
    mask=ImageChops.multiply(r.point(lambda v:255 if v<140 else 0),g.point(lambda v:255 if v<110 else 0))
    mask=ImageChops.multiply(mask,b.point(lambda v:255 if v<100 else 0))
    mask=ImageChops.multiply(mask,a.point(lambda v:255 if v>200 else 0))
    box=mask.crop((0,0,350,90)).getbbox()
    if box is None: raise ValueError('Missing standing root')
    return (box[0]+box[2])/2

def connected_layer(frame,seed):
    alpha=frame.getchannel('A'); component=alpha.point(lambda v:255 if v>64 else 0)
    if component.getpixel(seed)!=255: raise ValueError('Layer seed outside opaque foreground')
    ImageDraw.floodfill(component,seed,128)
    component=component.point(lambda v:255 if v==128 else 0).filter(ImageFilter.MaxFilter(3))
    result=frame.copy(); result.putalpha(ImageChops.multiply(alpha,component)); return result

def character(frame):
    # Only called while the walking character is spatially separate from the mat.
    # Connected alpha retains the actual moving limbs and discards the whole bed.
    component=frame.getchannel('A').point(lambda v:255 if v>64 else 0)
    top=component.crop((20,0,300,130)).getbbox()
    if top is None: raise ValueError('Missing character seed')
    seed=next((xx,top[1]) for xx in range(top[0]+20,top[2]+20) if component.getpixel((xx,top[1]))==255)
    return connected_layer(frame,seed)

for key,start,end in [('entry',0,2),('wake',4.5,7.25)]:
    source_frames=all_frames[key]
    indices=range(round(start*24),round(end*24))
    roots=[root_x(frame) for frame in source_frames[:73]] if key=='entry' else [root_x(frame) for frame in source_frames[60:]]
    roots=[sum(roots[max(0,i-2):i+3])/len(roots[max(0,i-2):i+3]) for i in range(len(roots))]
    manifest['clips'][key]['rootStart']=0 if key=='entry' else 2.5
    manifest['clips'][key]['rootX']=roots
    chars=[character(source_frames[i]) for i in indices]
    for page,offset in enumerate(range(0,len(chars),page_frames)):
        group=chars[offset:offset+page_frames];atlas=Image.new('RGBA',(w*cols,h*math.ceil(len(group)/cols)))
        for i,frame in enumerate(group):atlas.paste(frame,(i%cols*w,i//cols*h))
        atlas.save(out/f'{key}-walk-{page}.png',compress_level=3)
    manifest['clips'][key+'-walk']={'frames':len(chars),'sourceStart':start}

# Fixed scene transform from the actual standing character in the first decoded frame.
first=seams['entry'][0]; char=first.crop((0,0,210,h))
bounds=char.getchannel('A').point(lambda a:255 if a>220 else 0).getbbox()
l,t,r,b=bounds; scale=154/(b-t)
manifest['render']={'scale':scale,'x':100-(l+r)/2*scale,'y':170-b*scale,'splitX':210,'sceneWidth':400}
# Prop movement uses crops of the exact decoded boundary frames, avoiding re-rendered keyframe jumps.
for key,frame in [('arrive',seams['entry'][0]),('leave',all_frames['wake'][112])]:
    character(frame).save(out/f'{key}-character.png')
    # A vertical split can include Lulu's muzzle/hair above the pillow. Select
    # the mat's connected alpha component instead of including those fragments.
    connected_layer(frame,(400,200)).save(out/f'{key}-bed.png')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
sheet=Image.new('RGB',(w*3,h*2),(52,71,90))
for i,frame in enumerate([seams['entry'][0],seams['entry'][1],seams['loop'][0],seams['loop'][1],seams['wake'][0],seams['wake'][1]]):sheet.paste(frame,(i%3*w,i//3*h),frame)
sheet.save(source/'packaged-seams.jpg')
print(json.dumps(manifest,indent=2))
