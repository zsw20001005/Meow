"""Keep original waking poses; motion-compensate the walking tail to 60 fps."""
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageFilter
import json,math,subprocess
import imageio_ffmpeg
root=Path(__file__).resolve().parents[1];out=root/'windows/Meow.Windows/Assets/Lulu/Bed';m=json.loads((out/'manifest.json').read_text());clip=m['clips']['wake']
if clip.get('fps',24)!=24:raise SystemExit('Rebuild original 24 fps wake atlases before resampling.')
work=root/'build/lulu-jimeng/s5-floor-bed/wake-60fps';work.mkdir(parents=True,exist_ok=True)
w,h,cols,page_frames=512,288,m['columns'],m['pageFrames'];original=[]
for n in range(174):
    if n%page_frames==0:a=Image.open(out/f'wake-{n//page_frames}.png').convert('RGBA')
    i=n%page_frames;f=a.crop((i%cols*w,i//cols*h,i%cols*w+w,i//cols*h+h));original.append(f)
    rgb=Image.new('RGB',(w,h),'white');rgb.paste(f,(0,0),f);rgb.save(work/f'input-{n:04}.png')
for n in range(174,178):rgb.save(work/f'input-{n:04}.png')
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','24','-i',str(work/'input-%04d.png'),'-vf','minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none','-frames:v','435',str(work/'frame-%04d.png')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def matte(im):
    r,g,b=im.split();low=ImageChops.darker(ImageChops.darker(r,g),b);high=ImageChops.lighter(ImageChops.lighter(r,g),b)
    bg=ImageChops.multiply(low.point(lambda n:255 if n>230 else 0),ImageChops.subtract(high,low).point(lambda n:255 if n<23 else 0))
    padded=Image.new('L',(w+2,h+2),255);padded.paste(bg,(1,1));ImageDraw.floodfill(padded,(0,0),128)
    alpha=ImageChops.invert(padded.crop((1,1,w+1,h+1)).point(lambda n:255 if n==128 else 0))
    neutral=ImageChops.multiply(low.point(lambda n:255 if n>160 else 0),ImageChops.subtract(high,low).point(lambda n:255 if n<32 else 0))
    floor=Image.new('L',(w,h));d=ImageDraw.Draw(floor);d.rectangle((0,227,w,h),fill=255);d.rectangle((0,150,209,h),fill=255)
    rgba=im.convert('RGBA');rgba.putalpha(ImageChops.subtract(alpha,ImageChops.multiply(neutral,floor)).filter(ImageFilter.GaussianBlur(.3)));return rgba
frames=[]
for n in range(435):
    t=n/60;source=t*24
    if t<3.5:frame=original[int(source+1e-7)]
    elif n%5==0 or source>=173:frame=original[min(173,round(source))]
    else:frame=matte(Image.open(work/f'frame-{n+1:04}.png').convert('RGB'))
    frames.append(frame)
for page,start in enumerate(range(0,435,page_frames)):
    group=frames[start:start+page_frames];atlas=Image.new('RGBA',(w*cols,h*math.ceil(len(group)/cols)))
    for i,f in enumerate(group):atlas.paste(f,(i%cols*w,i//cols*h))
    atlas.save(out/f'wake-{page}.png',compress_level=3)
clip.update(frames=435,fps=60,sourceFps=24,resampling='Original poses until 3.5 s, then bidirectional motion compensation for walking; root track remains 24 fps',durationSeconds=7.25)
(out/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print('Wake walking tail packed at 60 fps; original earlier poses and duration retained.')
