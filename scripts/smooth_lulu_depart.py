"""Resample the reviewed left walk to 60 fps using motion compensation, not fades.

Run after build_lulu_bed_walk.py. Original atlas frames are preserved at shared
timestamps, and the exact first/terminal poses remain unchanged.
"""
from pathlib import Path
import argparse,json,math,subprocess
from PIL import Image,ImageChops,ImageDraw,ImageFilter
import imageio_ffmpeg

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,default=root/'windows/Meow.Windows/Assets/Lulu/Bed')
parser.add_argument('--work-dir',type=Path,default=root/'build/lulu-jimeng/s5-floor-bed/depart-60fps')
args=parser.parse_args();out=args.output_dir
m=json.loads((out/'manifest.json').read_text());clip=m['clips']['depart']
if clip.get('fps',24)!=24:raise SystemExit('Rebuild original 24 fps walking atlases before resampling.')
work=args.work_dir;work.mkdir(parents=True,exist_ok=True)
cols=m['columns'];page_frames=m['pageFrames'];size=256;original=[]
count=clip['frames'];target_count=round(count*60/24)
for n in range(clip['frames']):
    if n%page_frames==0:a=Image.open(out/f'depart-{n//page_frames}.png').convert('RGBA')
    i=n%page_frames;f=a.crop((i%cols*size,i//cols*size,i%cols*size+size,i//cols*size+size));original.append(f)
    rgb=Image.new('RGB',(size,size),'white');rgb.paste(f,(0,0),f);rgb.save(work/f'input-{n:04}.png')
for n in range(count,count+4):rgb.save(work/f'input-{n:04}.png')
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','24','-i',str(work/'input-%04d.png'),'-vf','minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none','-frames:v',str(target_count),str(work/'frame-%04d.png')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def matte(im):
    r,g,b=im.split();low=ImageChops.darker(ImageChops.darker(r,g),b);high=ImageChops.lighter(ImageChops.lighter(r,g),b)
    neutral=ImageChops.multiply(low.point(lambda n:255 if n>165 else 0),ImageChops.subtract(high,low).point(lambda n:255 if n<35 else 0))
    padded=Image.new('L',(258,258),255);padded.paste(neutral,(1,1));ImageDraw.floodfill(padded,(0,0),128)
    alpha=ImageChops.invert(padded.crop((1,1,257,257)).point(lambda n:255 if n==128 else 0))
    lower=Image.new('L',im.size);ImageDraw.Draw(lower).rectangle((0,size*.62,size,size),fill=255)
    alpha=ImageChops.subtract(alpha,ImageChops.multiply(neutral,lower))
    rgba=im.convert('RGBA');rgba.putalpha(alpha.filter(ImageFilter.GaussianBlur(.3)));return rgba

frames=[]
for n in range(target_count):
    source=n*24/60
    if n%5==0 or source>=count-1:frame=original[min(count-1,round(source))]
    else:frame=matte(Image.open(work/f'frame-{n+1:04}.png').convert('RGB'))
    frames.append(frame)
for page,start in enumerate(range(0,target_count,page_frames)):
    group=frames[start:start+page_frames];atlas=Image.new('RGBA',(size*cols,size*math.ceil(len(group)/cols)))
    for i,f in enumerate(group):atlas.paste(f,(i%cols*size,i//cols*size))
    atlas.save(out/f'depart-{page}.png',compress_level=3)
clip.update(frames=target_count,fps=60,sourceFps=24,resampling='FFmpeg bidirectional motion compensation; no alpha crossfade; exact shared-time original frames',durationSeconds=count/24)
(out/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
sheet=Image.new('RGB',(8*256,4*280),'#34475a');d=ImageDraw.Draw(sheet)
for j,n in enumerate([*range(52,68),*range(175,191)]):
    xy=(j%8*256,j//8*280);sheet.paste(frames[n],xy,frames[n]);d.text((xy[0],xy[1]+260),f'{n/60:.3f}s [{n}]',fill='white')
sheet.save(work/'foot-contact-review.jpg')
print(f'Packed {target_count} motion-compensated frames, 60 fps, {count/24} seconds. Original endpoints retained.')
