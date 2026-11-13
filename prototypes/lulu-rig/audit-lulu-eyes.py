"""Verify eye-local edits, closed eyeballs and their attachment to the face."""
from pathlib import Path
import bpy,sys,json,numpy as np
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
def vertices(mesh):
    p=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',p);return p.reshape(-1,3)
bpy.ops.wm.open_mainfile(filepath=str(root/'source-normalized.blend'))
source=vertices(next(o.data for o in bpy.context.scene.objects if o.type=='MESH'))
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-eyes-v1.blend'))
body=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
edited=vertices(body.data)
def outside(points):
    allowed=np.zeros(len(points),dtype=bool)
    for ex,ez in [(-.371,2.211),(.333,2.319)]:
        dx=points[:,0]-ex;dz=points[:,2]-ez
        u=dx*.986+dz*.167;v=-dx*.167+dz*.986
        allowed|=((u/.154)**2+(v/.164)**2<2.12**2)&(points[:,1]<.02)
    return {tuple(p) for p in points[~allowed]}
if outside(source)!=outside(edited):
    missing=outside(source)-outside(edited);added=outside(edited)-outside(source)
    print('OUTSIDE_DIFF',len(missing),len(added),'missing',list(missing)[:4],'added',list(added)[:8])
assert outside(source)==outside(edited),'Modified geometry outside the eye patches'
names=[body.name,'Eye L sclera','Eye R sclera']
health=check_geometry.run(names=names,spec={'expect_embedded':[['Eye * sclera',body.name]]})
report={'body_outside_eyes_unchanged':True,'source_vertices':len(source),'repaired_body_vertices':len(edited),'health':health,'note':'Iris, pupil and catchlight are intentionally open surface layers; the closed sclera and body are checked.'}
(root/'eyes-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps({'body_outside_eyes_unchanged':True,'summary':health['summary'],'errors':health['errors'],'warnings':health['warnings']},ensure_ascii=False))
