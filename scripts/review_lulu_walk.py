"""Create time-labelled full-body and foot-contact sheets without changing video."""
from pathlib import Path
import argparse,json
from PIL import Image,ImageDraw,ImageChops,ImageStat
import imageio_ffmpeg

parser=argparse.ArgumentParser()
parser.add_argument('video',type=Path)
parser.add_argument('output',type=Path)
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
reader=imageio_ffmpeg.read_frames(str(args.video),pix_fmt='rgb24',output_params=['-vf','fps=24,scale=512:288'])
meta=next(reader);frames=[Image.frombytes('RGB',(512,288),v) for v in reader];reader.close()
samples=[round(i*(len(frames)-1)/9) for i in range(10)]
sheet=Image.new('RGB',(512*5,312*2),'#eee');d=ImageDraw.Draw(sheet)
for j,n in enumerate(samples):
    xy=(j%5*512,j//5*312);sheet.paste(frames[n],xy);d.text((xy[0]+4,xy[1]+292),f'{n/24:.3f}s [{n}]',fill='black')
sheet.save(args.output/'overview.jpg')
for start in range(0,len(frames),96):
    sheet=Image.new('RGB',(8*260,4*200),'#eee');d=ImageDraw.Draw(sheet)
    for j,n in enumerate(range(start,min(start+96,len(frames)),3)):
        xy=(j%8*260,j//8*200);sheet.paste(frames[n].crop((190,170,320,260)).resize((260,180)),xy);d.text((xy[0]+4,xy[1]+183),f'{n/24:.3f}s [{n}]',fill='black')
    sheet.save(args.output/f'feet-{start:03d}.jpg')
deltas=[]
for i in range(1,len(frames)):
    a=frames[i-1].crop((190,170,320,260));b=frames[i].crop((190,170,320,260))
    deltas.append(sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3)
report={'source':str(args.video),'sourceMetadata':meta,'reviewFps':24,'frames':len(frames),'footCrop':[190,170,320,260],'footFrameDifferences':deltas,'note':'Image differences and contact sheets are diagnostic evidence, not a natural-motion acceptance score.'}
(args.output/'review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'frames':len(frames),'duration':len(frames)/24,'output':str(args.output)}))
