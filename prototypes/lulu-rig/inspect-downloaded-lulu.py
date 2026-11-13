"""Inspect the downloaded STL and render its actual geometry."""
import bpy, json
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parent
out=root/'review'/'sketchfab-lulu'
out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.stl_import(filepath=str(root/'assets/sketchfab-lulu/original/水豚噜噜.stl'))
obj=bpy.context.object
# Connected islands retain useful original part boundaries in this STL.
mesh=obj.data
parent=list(range(len(mesh.vertices)))
def find(a):
    while parent[a]!=a:
        parent[a]=parent[parent[a]];a=parent[a]
    return a
for e in mesh.edges:
    a,b=map(find,e.vertices)
    if a!=b:parent[b]=a
groups={}
for v in mesh.vertices:groups.setdefault(find(v.index),[]).append(v.index)
parts=[]
for ids in groups.values():
    pts=[mesh.vertices[i].co for i in ids]
    parts.append({'count':len(ids),'min':[min(v[k] for v in pts) for k in range(3)],'max':[max(v[k] for v in pts) for k in range(3)],'root':find(ids[0])})
parts.sort(key=lambda x:-x['count'])
(out/'original-inspection.json').write_text(json.dumps({'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'parts':parts},indent=2),encoding='utf-8')
print('INSPECTION',json.dumps(parts[:30]))
# Normalize only scale and origin for the studio preview.
for v in mesh.vertices:
    x,y,z=v.co;v.co=(x,-z,y)
lo=Vector([min(v.co[k] for v in mesh.vertices) for k in range(3)])
hi=Vector([max(v.co[k] for v in mesh.vertices) for k in range(3)])
center=(lo+hi)/2;center.z=lo.z
scale=3/(hi.z-lo.z)
for v in mesh.vertices:v.co=(v.co-center)*scale
for p in mesh.polygons:p.use_smooth=True
bpy.ops.wm.save_as_mainfile(filepath=str(out/'source-normalized.blend'))
