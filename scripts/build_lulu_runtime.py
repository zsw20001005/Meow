"""Prepare the reviewed video takes for the Windows preview (originals stay intact)."""
from pathlib import Path
import json, math, hashlib, argparse
from PIL import Image, ImageChops, ImageDraw, ImageFilter
import imageio_ffmpeg

root=Path(__file__).resolve().parents[1]
sources=root/'build/lulu-jimeng'
output=root/'windows/Meow.Windows/Assets/Lulu/Video'
output.mkdir(parents=True,exist_ok=True)
size=256; fps=24; columns=8
parser=argparse.ArgumentParser()
parser.add_argument('--only',default='')
parser.add_argument('--finish-existing',action='store_true')
args=parser.parse_args()
jobs={}
for action,folder in {'idle':'v2-idle','walk':'v2-walk','wave':'v2-wave','nod':'v2-nod','shakeHead':'v2-shakeHead','think':'v2-think','dance':'v2-dance','stretch':'v3-stretch','roll':'v3-roll','spin':'v5-spin','sleep':'v4-sleep','jump':'v2-jump'}.items():
    report=json.loads((sources/folder/'report.json').read_text(encoding='utf-8'))
    jobs[action]=(report['source'],*report['interval_seconds'])
for action,folder in {'eat':'google-r2-eat','play':'google-batch-play','talk':'google-batch-talk','peek':'google-batch-peek','land':'google-batch-fall',**{key:f'google-batch-{key}' for key in ['happy','love','shy','curious','surprised','sad','sleepy','hungry','dizzy']},'angry':'google-r2-angry'}.items():
    report=json.loads((sources/folder/'report.json').read_text(encoding='utf-8'))
    jobs[action]=(report['source'],*report['interval_seconds'])
jobs['drag']=('google-r2-02-motion.mp4',1.5,3.0)

def matte(frame, protect_ball=False):
    # Only remove near-neutral bright regions connected to the outside. White eyes
    # enclosed by dark outlines remain intact; no generated replacement pixels.
    rgb=frame.convert('RGB'); r,g,b=rgb.split()
    low=ImageChops.darker(ImageChops.darker(r,g),b)
    high=ImageChops.lighter(ImageChops.lighter(r,g),b)
    neutral=ImageChops.subtract(high,low).point(lambda n:255 if n<42 else 0)
    bright=low.point(lambda n:255 if n>145 else 0)
    eligible=ImageChops.multiply(neutral,bright)
    padded=Image.new('L',(rgb.width+2,rgb.height+2),255); padded.paste(eligible,(1,1))
    ImageDraw.floodfill(padded,(0,0),128)
    outside=padded.crop((1,1,rgb.width+1,rgb.height+1)).point(lambda n:255 if n==128 else 0)
    alpha=ImageChops.invert(outside)
    if protect_ball:
        blue=ImageChops.multiply(ImageChops.subtract(b,r).point(lambda v:255 if v>35 else 0),b.point(lambda v:255 if v>90 else 0))
        ball=blue.getbbox()
        if ball and ball[1]>rgb.height*.55 and ball[2]-ball[0]>4:
            # Preserve the white rubber panels inside the round blue toy silhouette.
            radius=max(ball[2]-ball[0],ball[3]-ball[1])/2
            cx=(ball[0]+ball[2])/2; cy=ball[1]+radius
            ImageDraw.Draw(alpha).ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=255)
    # Subpixel antialiasing at the white boundary, without blurring body detail.
    alpha=alpha.filter(ImageFilter.GaussianBlur(.35))
    rgba=rgb.convert('RGBA'); rgba.putalpha(alpha)
    return rgba

def finish(cell,key):
    alpha=cell.getchannel('A')
    if key!='play':
        r,g,b=cell.convert('RGB').split()
        low=ImageChops.darker(ImageChops.darker(r,g),b)
        high=ImageChops.lighter(ImageChops.lighter(r,g),b)
        white=ImageChops.multiply(low.point(lambda n:255 if n>180 else 0),ImageChops.subtract(high,low).point(lambda n:255 if n<30 else 0))
        lower=Image.new('L',cell.size); ImageDraw.Draw(lower).rectangle((0,size*.51,size,size),fill=255)
        alpha=ImageChops.subtract(alpha,ImageChops.multiply(white,lower))
    cell.putalpha(alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.3)))
    return cell

if args.finish_existing:
    for path in output.glob('*.png'):
        if args.only and path.stem not in args.only.split(','): continue
        with Image.open(path) as opened: atlas=opened.convert('RGBA')
        for y in range(0,atlas.height,size):
            for x in range(0,atlas.width,size):
                atlas.paste(finish(atlas.crop((x,y,x+size,y+size)),path.stem),(x,y))
        temporary=path.with_suffix('.tmp.png')
        atlas.save(temporary,compress_level=3)
        temporary.replace(path)
    print('Cleaned white fringe and enclosed floor gaps; toy ball panels preserved.')
    raise SystemExit()

cache={}
def source_frames(name):
    if name not in cache:
        reader=imageio_ffmpeg.read_frames(str(sources/name),pix_fmt='rgb24',output_params=['-vf','fps=24,scale=-2:360'])
        meta=next(reader)
        frames=[Image.frombytes('RGB',meta['size'],data) for data in reader]
        cache.clear()  # source memory is bounded; atlases are generated one at a time.
        cache[name]=frames
    return cache[name]

manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8')) if args.only else {'version':1,'fps':fps,'cellSize':size,'columns':columns,'previewOnly':True,'clips':{}}
previews=[]
for key,(source,start,end) in jobs.items():
    if args.only and key not in args.only.split(','): continue
    frames=source_frames(source)
    neutral=matte(frames[0])
    # Fixed per-source framing: never chase a moving bounding box frame by frame.
    bounds=neutral.getchannel('A').point(lambda a:255 if a>160 else 0).getbbox()
    if not bounds: raise ValueError(f'No character in {source}')
    left,top,right,bottom=bounds
    scale=(size*.77)/(bottom-top)
    center=(left+right)/2
    offset=(round(size/2-center*scale),round(size*.85-bottom*scale))
    selected=frames[round(start*fps):round(end*fps)]
    if not selected: raise ValueError(f'Empty clip {key}')
    atlas=Image.new('RGBA',(columns*size,math.ceil(len(selected)/columns)*size))
    for index,frame in enumerate(selected):
        cut=matte(frame,protect_ball=key=='play')
        resized=cut.resize((round(cut.width*scale),round(cut.height*scale)),Image.Resampling.LANCZOS)
        cell=Image.new('RGBA',(size,size)); cell.alpha_composite(resized,offset)
        cell=finish(cell,key)
        atlas.paste(cell,((index%columns)*size,(index//columns)*size))
        if index==len(selected)//2: previews.append((key,cell.copy()))
    atlas.save(output/f'{key}.png',compress_level=3)
    mode='loop' if key in ('idle','walk','talk') else 'hold'
    manifest['clips'][key]={'file':f'{key}.png','frames':len(selected),'fps':fps,'mode':mode,'source':source,'interval':[start,end],'sourceSha256':hashlib.sha256((sources/source).read_bytes()).hexdigest()}
    print(f'{key}: {len(selected)} frames',flush=True)
manifest['clips']['fall']={**manifest['clips']['drag'],'mode':'still','stillFrame':manifest['clips']['drag']['frames']-1}
(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
sheet=Image.new('RGB',(6*size,math.ceil(len(previews)/6)*(size+25)),'#34475a')
draw=ImageDraw.Draw(sheet)
for index,(key,cell) in enumerate(previews):
    x=(index%6)*size;y=(index//6)*(size+25)
    sheet.paste(cell,(x,y),cell);draw.text((x+10,y+size),key,fill='white')
sheet.save(root/'build/lulu-jimeng/runtime-contact.jpg')
print(f'Prepared {len(manifest["clips"])} runtime states at {output}')
