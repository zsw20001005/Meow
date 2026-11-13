"""Check source preservation and report mesh health using blender-modeler."""
import bpy,sys,json,hashlib,array
from pathlib import Path
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry
def signature(mesh):
    coords=array.array('f',[0])*(len(mesh.vertices)*3)
    mesh.vertices.foreach_get('co',coords)
    indices=array.array('i',[0])*(len(mesh.loops))
    mesh.loops.foreach_get('vertex_index',indices)
    return {'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'positions_sha256':hashlib.sha256(coords.tobytes()).hexdigest(),'indices_sha256':hashlib.sha256(indices.tobytes()).hexdigest()}
bpy.ops.wm.open_mainfile(filepath=str(root/'source-normalized.blend'))
original=signature(next(o.data for o in bpy.context.scene.objects if o.type=='MESH'))
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-colored.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
painted=signature(obj.data)
assert original==painted,'Source geometry changed'
health=check_geometry.run(names=[obj.name])
report={'source_geometry_unchanged':True,'geometry':original,'health':health,'visual_approval':False}
(root/'colored-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps({'source_geometry_unchanged':True,'health':health.get('summary'),'errors':health.get('errors'),'warnings':health.get('warnings')},ensure_ascii=False))
