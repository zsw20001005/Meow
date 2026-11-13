import bpy, bmesh, json, sys, shutil
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry,render_views
bpy.ops.wm.read_factory_settings(use_empty=True)
result=json.loads((ROOT/'shape-result.json').read_text(encoding='utf-8'))
source=result[0]['value'] if isinstance(result[0],dict) else result[0]
shutil.copy2(source,ROOT/'lulu-tpose-raw.glb')
bpy.ops.import_scene.gltf(filepath=source)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
offset=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));scale=3/(hi.z-lo.z)
report={'source':source,'normalization_height':3,'objects':[]}
for o in meshes:
    o.data.transform(o.matrix_world);o.matrix_world.identity()
    a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a)
    a=(a.reshape(-1,3)-np.array(offset))*scale;o.data.vertices.foreach_set('co',a.ravel());o.data.update()
    before=len(o.data.polygons)
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-6,edges=list(bm.edges))
    bm.to_mesh(o.data);bm.free()
    for p in o.data.polygons:p.use_smooth=True
    report['objects'].append({'name':o.name,'vertices':len(o.data.vertices),'faces_before_cleanup':before,'faces':len(o.data.polygons)})
bpy.context.view_layer.update()
report['geometry']=check_geometry.run(spec={'ground':True,'max_verts':3000000})
(ROOT/'geometry-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'lulu-tpose-source.blend'))
render_views.run(str(ROOT/'review'),mode='clay',res=800,color_by='material',views=[('front',0,0,True),('side',90,0,True),('back',180,0,True),('three_quarter',35,10,True)])
print('REPORT',json.dumps(report['objects']),flush=True)
