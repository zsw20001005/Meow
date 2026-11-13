import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-set-01'
FFMPEG='D:/coding/Meow/.build-tools/uv-cache/archive-v0/yy1jWl_8h8kbVTMv/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v9.0.2.exe'
labels={'idle':'待机呼吸','look':'左右张望','wave':'挥手招呼','walk':'起步 · 行走 · 停下','turn':'交替踏步 · 转身一圈'}
manifest=json.loads((OUT/'manifest.json').read_text())
for clip in manifest['clips']:
    slug=clip['slug'];files=list((OUT/'frames'/slug).glob('*.png'))
    assert len(files)==clip['frames'],(slug,len(files),clip['frames'])
    font="C\\:/Windows/Fonts/msyh.ttc"
    vf=f"drawtext=fontfile='{font}':text='{labels[slug]}':x=22:y=20:fontsize=25:fontcolor=white:shadowcolor=black@0.5:shadowx=1:shadowy=1"
    subprocess.run([FFMPEG,'-y','-v','error','-framerate','30','-i',str(OUT/'frames'/slug/'%04d.png'),'-vf',vf,'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/f'lulu-{slug}.mp4')],check=True)
    print('ENCODED',slug,flush=True)
concat=OUT/'concat.txt'
concat.write_text(''.join("file 'lulu-"+c['slug']+".mp4'\n" for c in manifest['clips']),encoding='utf-8')
subprocess.run([FFMPEG,'-y','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(OUT/'lulu-five-motions.mp4')],check=True)
subprocess.run([FFMPEG,'-v','error','-i',str(OUT/'lulu-five-motions.mp4'),'-f','null','-'],check=True)
print('OVERVIEW_VERIFIED',flush=True)
