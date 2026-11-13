from pathlib import Path
import bpy,json
from mathutils import Vector
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-eyes-v1.blend'))
body=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
samples=[]
for v in [-.4,-.3,0,.3,.4]:
    for u in [-.75,-.5,0,.5,.75]:
        x=.986*u-.167*v;z=1.79+.167*u+.986*v
        hit,p,n,f=body.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
        if hit:samples.append({'u':u,'v':v,'y':round(p.y,4)})
print('MUZZLE_MEASURE',json.dumps(samples))
import numpy as np
with bpy.data.libraries.load(str(root/'source-normalized.blend'),link=False) as (src,dst):dst.meshes=list(src.meshes)
mesh=max(dst.meshes,key=lambda m:len(m.vertices))
with np.load(root/'surface-regions.npz') as mask:ids=np.flatnonzero(mask['hand']>.5)
p=np.array([mesh.vertices[int(i)].co[:] for i in ids])
print('HAND_BOUNDS',p.min(axis=0),p.max(axis=0))
