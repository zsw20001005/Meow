"""Package continuous walking takes at their original speed; never repeat a stride."""
from pathlib import Path
import argparse, hashlib, json, math, sys, subprocess
from PIL import Image, ImageChops, ImageDraw, ImageFilter
import imageio_ffmpeg

root=Path(__file__).resolve().parents[1]
source=root/'build/lulu-jimeng/s5-floor-bed'
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,default=root/'windows/Meow.Windows/Assets/Lulu/Bed')
parser.add_argument('--depart-source',type=Path,default=source/'depart-r6.mp4')
parser.add_argument('--depart-trim-frames',type=int,default=0)
parser.add_argument('--depart-only',action='store_true')
parser.add_argument('--repair-existing',action='store_true')
parser.add_argument('--clean-existing',action='store_true')
args=parser.parse_args()
out=args.output_dir
manifest=json.loads((out/'manifest.json').read_text())
size=256; fps=24; columns=manifest['columns']; page_frames=manifest['pageFrames']
render=manifest['render']; factor=render['scale']*size/200
offset=(round(size/2-256*factor),round(render['y']*size/200))

def matte(im):
    r,g,b=im.split();low=ImageChops.darker(ImageChops.darker(r,g),b);high=ImageChops.lighter(ImageChops.lighter(r,g),b)
    neutral=ImageChops.multiply(low.point(lambda n:255 if n>165 else 0),ImageChops.subtract(high,low).point(lambda n:255 if n<35 else 0))
    padded=Image.new('L',(size+2,size+2),255);padded.paste(neutral,(1,1));ImageDraw.floodfill(padded,(0,0),128)
    alpha=ImageChops.invert(padded.crop((1,1,size+1,size+1)).point(lambda n:255 if n==128 else 0))
    # Closed white gaps between planted feet are floor, even when the flood fill
    # cannot reach them. Restrict this cleanup below the torso to preserve eyes.
    lower=Image.new('L',im.size);ImageDraw.Draw(lower).rectangle((0,size*.62,size,size),fill=255)
    alpha=ImageChops.subtract(alpha,ImageChops.multiply(neutral,lower))
    rgba=im.convert('RGBA');rgba.putalpha(alpha.filter(ImageFilter.GaussianBlur(.3)));return rgba

def repair_depart_contact(frames):
    # Frame 24 has a one-frame planted-foot reset. Reconstruct only that missing
    # instant from adjacent original frames; preserve timing and every other frame.
    work=source/'depart-contact-repair';work.mkdir(exist_ok=True)
    for i,n in enumerate([23,23,25,25,25]):
        rgb=Image.new('RGB',(size,size),'white');rgb.paste(frames[n],(0,0),frames[n]);rgb.save(work/f'input-{i:02}.png')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','12','-i',str(work/'input-%02d.png'),'-vf','minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none','-frames:v','5',str(work/'output-%02d.png')],check=True,capture_output=True)
    frames[24].save(work/'before.png')
    frames[24]=matte(Image.open(work/'output-04.png').convert('RGB'))
    frames[24].save(work/'after.png')

if '--repair-existing' in sys.argv:
    if manifest['clips']['depart']['source'] != 'depart-r2.mp4' or manifest['clips']['depart'].get('fps',24) != 24:
        raise SystemExit('This repair applies only to original S8 depart-r2 frames, not regenerated or resampled walks.')
    path=out/'depart-0.png';atlas=Image.open(path).convert('RGBA')
    frames=[atlas.crop((i%columns*size,i//columns*size,i%columns*size+size,i//columns*size+size)) for i in range(48)]
    repair_depart_contact(frames)
    atlas.paste(frames[24],(0,6*size));atlas.save(path,compress_level=3)
    manifest['clips']['depart']['repairedFrames']=[24]
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    raise SystemExit()

if '--clean-existing' in sys.argv:
    for clip in ['approach','depart']:
        for path in sorted(out.glob(f'{clip}-[0-9]*.png')):
            atlas=Image.open(path).convert('RGBA')
            for yy in range(0,atlas.height,size):
                for xx in range(0,atlas.width,size):
                    cell=atlas.crop((xx,yy,xx+size,yy+size));r,g,b,a=cell.split()
                    low=ImageChops.darker(ImageChops.darker(r,g),b);high=ImageChops.lighter(ImageChops.lighter(r,g),b)
                    neutral=ImageChops.multiply(low.point(lambda n:255 if n>165 else 0),ImageChops.subtract(high,low).point(lambda n:255 if n<35 else 0))
                    lower=Image.new('L',cell.size);ImageDraw.Draw(lower).rectangle((0,size*.62,size,size),fill=255)
                    cell.putalpha(ImageChops.subtract(a,ImageChops.multiply(neutral,lower)));atlas.paste(cell,(xx,yy))
            atlas.save(path,compress_level=3)
    print('Removed enclosed white floor gaps from existing walking frames.')
    raise SystemExit()

for clip in (['depart'] if '--depart-only' in sys.argv else ['approach','depart']):
    path=args.depart_source if clip == 'depart' else source/'approach.mp4'
    reader=imageio_ffmpeg.read_frames(str(path),pix_fmt='rgb24',output_params=['-vf','fps=24,scale=512:288'])
    next(reader);frames=[]
    for i,raw in enumerate(reader):
        if i>=240:break
        if clip == 'depart' and i < args.depart_trim_frames: continue
        im=Image.frombytes('RGB',(512,288),raw).resize((round(512*factor),round(288*factor)),Image.Resampling.LANCZOS)
        cell=Image.new('RGB',(size,size),'white');cell.paste(im,offset);frames.append(matte(cell))
    reader.close()
    for page,start in enumerate(range(0,len(frames),page_frames)):
        group=frames[start:start+page_frames];atlas=Image.new('RGBA',(size*columns,size*math.ceil(len(group)/columns)))
        for i,frame in enumerate(group):atlas.paste(frame,(i%columns*size,i//columns*size))
        atlas.save(out/f'{clip}-{page}.png',compress_level=3)
    manifest['clips'][clip]={'frames':len(frames),'width':size,'height':size,'source':path.name,'mode':'once','playbackRate':1,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    if clip == 'depart': manifest['clips'][clip].update(fps=24,sourceStart=args.depart_trim_frames/24,sourceEnd=(args.depart_trim_frames+len(frames))/24)
    sheet=Image.new('RGB',(size*5,size*2),'#34475a')
    for i in range(10):sheet.paste(frames[min(i*24,len(frames)-1)],(i%5*size,i//5*size),frames[min(i*24,len(frames)-1)])
    sheet.save(out/f'{clip}-packaged.jpg')
    print(f'{clip}: {len(frames)} continuous frames at original 24 fps',flush=True)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
