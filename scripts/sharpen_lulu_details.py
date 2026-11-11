"""Restore modest interior contrast while preserving the reviewed RGBA silhouette.

Reads one immutable EdgeClean snapshot; repeated runs never stack sharpening.
Includes the existing bed joins without changing their geometry or alpha.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'windows/Meow.Windows/Assets/Lulu'
WORK = ROOT/'build/lulu-detail-clarity'
SOURCE = WORK/'original'

def sharpen(image):
    old = np.array(image.convert('RGBA'))
    rgb = old[:, :, :3].astype(np.float32)
    alpha = old[:, :, 3].astype(np.float32)/255
    distance = cv2.distanceTransform((alpha == 1).astype(np.uint8), cv2.DIST_L2, 5)
    weight = np.clip((distance-1.5)/2.5, 0, 1)
    luma = rgb @ np.array([.2126, .7152, .0722], np.float32)
    def blur(sigma):
        return cv2.GaussianBlur(luma*alpha, (0, 0), sigma)/np.maximum(cv2.GaussianBlur(alpha, (0, 0), sigma), .001)
    fine = luma-blur(.7)
    detail = .85*fine + .25*(luma-blur(1.4))
    # Avoid boosting sub-code-value noise or creating white/black ringing.
    detail = np.sign(detail)*np.maximum(np.abs(detail)-.4, 0)
    detail = np.clip(detail, -9, 9)*weight
    low = cv2.erode(luma, np.ones((3, 3), np.uint8))
    high = cv2.dilate(luma, np.ones((3, 3), np.uint8))
    target = np.clip(luma+detail, low-1, high+1)
    result = old.copy()
    result[:, :, :3] = np.rint(np.clip(rgb+(target-luma)[:, :, None], 0, 255)).astype(np.uint8)
    assert np.array_equal(old[:, :, 3], result[:, :, 3])
    assert np.array_equal(old[weight == 0], result[weight == 0])
    return Image.fromarray(result)

def jobs():
    for group in ['Video', 'Bed']:
        manifest = json.loads((SOURCE/group/'manifest.json').read_text('utf-8-sig'))
        seen = set()
        for key, clip in manifest['clips'].items():
            w = clip.get('width', manifest.get('cellSize', manifest.get('width')))
            h = clip.get('height', manifest.get('cellSize', manifest.get('height')))
            page = manifest.get('pageFrames', clip['frames'])
            for start in range(0, clip['frames'], page):
                name = clip.get('file', f'{key}-{start//page}.png')
                if name in seen: continue
                seen.add(name)
                yield group, name, w, h, manifest['columns'], min(page,clip['frames']-start)
        for path in sorted((SOURCE/group).glob('*.png')):
            if path.name not in seen and not re.search(r'-\d+\.png$', path.name):
                with Image.open(path) as image: w,h=image.size
                yield group,path.name,w,h,1,1

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    WORK.mkdir(parents=True,exist_ok=True)
    for group in ['Video','Bed']:
        if not (SOURCE/group).exists(): shutil.copytree(ASSETS/group,SOURCE/group)
    records=[]; examples=[]
    for group,name,w,h,columns,count in jobs():
        if not args.apply and name not in ['idle.png','eat.png','play.png','spin.png','depart-2.png','loop-1.png']: continue
        atlas=Image.open(SOURCE/group/name).convert('RGBA')
        output=atlas.copy()
        for i in range(count):
            x,y=i%columns*w,i//columns*h
            frame=atlas.crop((x,y,x+w,y+h))
            output.paste(sharpen(frame),(x,y))
        if args.apply:
            dest=WORK/'processed'/group/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            output.save(dest)
        if group=='Video' or name in ['depart-2.png','loop-1.png','wake-5.png','join-return-0.png']:
            i=count//3; x,y=i%columns*w,i//columns*h
            examples.append((group+'/'+name,atlas.crop((x,y,x+w,y+h)),output.crop((x,y,x+w,y+h))))
        records.append({'group':group,'file':name,'frames':count,'sourceSha256':hashlib.sha256((SOURCE/group/name).read_bytes()).hexdigest()})
        print(group,name,count,flush=True)
    for page in range(0,len(examples),4):
        sheet=Image.new('RGB',(1024,4*280),'#777777'); draw=ImageDraw.Draw(sheet)
        for row,(name,before,after) in enumerate(examples[page:page+4]):
            draw.text((6,row*280+5),name+' | before / after (dark) | before / after (light)',fill='white')
            for col,(im,color) in enumerate([(before,'#172131'),(after,'#172131'),(before,'#eeeeee'),(after,'#eeeeee')]):
                bg=Image.new('RGBA',im.size,color); bg.alpha_composite(im); bg.thumbnail((256,256),Image.Resampling.LANCZOS)
                sheet.paste(bg.convert('RGB'),(col*256,row*280+24))
        sheet.save(WORK/f'comparison-{page//4}.png')
    (WORK/'processing.json').write_text(json.dumps({'applied':args.apply,'files':len(records),'frames':sum(r['frames'] for r in records),'alphaAndBoundaryUnchanged':True,'records':records},indent=2),'utf-8')
    if args.apply:
        for r in records:
            dest=ASSETS/r['group']/r['file']; temp=dest.with_suffix('.tmp')
            shutil.copyfile(WORK/'processed'/r['group']/r['file'],temp); temp.replace(dest)

if __name__=='__main__': main()
