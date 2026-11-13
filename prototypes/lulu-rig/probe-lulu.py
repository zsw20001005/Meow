import bpy
from pathlib import Path
from mathutils import Vector
p=Path(__file__).resolve().parent/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(p/'source-normalized.blend'))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
for px,py in [(405,375),(414,368),(584,345),(582,336),(500,470),(470,570),(335,740),(325,780),(350,865),(367,895),(670,865),(700,770),(450,270),(500,222),(461,193),(480,286),(600,500)]:
    hit,co,no,i=o.ray_cast(Vector(((px-500)*.00395,-5,1.72+(500-py)*.00395)),Vector((0,1,0)))
    print((px,py),hit,tuple(round(x,4) for x in co),tuple(round(x,4) for x in no))
