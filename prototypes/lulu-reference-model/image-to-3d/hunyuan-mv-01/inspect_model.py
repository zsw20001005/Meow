import bpy, json, sys
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, r'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry, render_views
bpy.ops.wm.read_factory_settings(use_empty=True)
result = json.loads((ROOT / 'shape-result.json').read_text(encoding='utf-8'))
source = result[0]['value']
bpy.ops.import_scene.gltf(filepath=source)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(p[i] for p in points) for i in range(3)])
hi = Vector([max(p[i] for p in points) for i in range(3)])
offset = Vector(((lo.x+hi.x)/2, (lo.y+hi.y)/2, lo.z))
scale = 3.0 / (hi.z-lo.z)
report = {'source': source, 'objects': []}
for o in meshes:
    o.data.transform(o.matrix_world)
    o.matrix_world.identity()
    a = np.empty(len(o.data.vertices)*3, dtype=np.float32)
    o.data.vertices.foreach_get('co', a)
    a = (a.reshape(-1,3)-np.array(offset))*scale
    o.data.vertices.foreach_set('co', a.ravel())
    o.data.update()
    facekeys = np.array([tuple(sorted(p.vertices)) for p in o.data.polygons],dtype=np.int32)
    duplicate = len(facekeys)-len(np.unique(facekeys,axis=0))
    report['objects'].append({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'duplicate_faces':int(duplicate),'finite':bool(np.isfinite(a).all()),'dimensions':list(o.dimensions)})
    for p in o.data.polygons: p.use_smooth = True
    o.color = (0.65, 0.68, 0.73, 1)
report['geometry_checks'] = check_geometry.run(spec={'ground':True,'max_verts':2000000})
(ROOT/'geometry-report.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'lulu-hunyuan-source.blend'))
render_views.run(str(ROOT/'review'),mode='clay',res=640,color_by='material',views=[('front',0,0,True),('side',90,0,True),('back',180,0,True),('three_quarter',35,10,True)])
print('MODEL_REPORT',json.dumps({k:v for k,v in report.items() if k!='geometry_checks'}),flush=True)
