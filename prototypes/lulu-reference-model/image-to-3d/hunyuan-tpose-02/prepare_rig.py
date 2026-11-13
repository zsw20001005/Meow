import bpy,bmesh,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry,render_views
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'lulu-tpose-source.blend'),use_scripts=False)
report={'target_faces':200000,'objects':[]}
for o in [x for x in bpy.context.scene.objects if x.type=='MESH']:
    before=len(o.data.polygons)
    bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Rig mesh simplification','DECIMATE');mod.ratio=min(1,200000/before);mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-5,edges=list(bm.edges))
    bm.to_mesh(o.data);bm.free()
    for p in o.data.polygons:p.use_smooth=True
    report['objects'].append({'name':o.name,'faces_before':before,'faces_after':len(o.data.polygons)})
bpy.context.view_layer.update()
report['geometry']=check_geometry.run(spec={'ground':True,'max_verts':500000})
(ROOT/'rig-input-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'lulu-tpose-rig-input.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'lulu-tpose-rig-input.glb'),export_format='GLB')
render_views.run(str(ROOT/'review-rig-input'),mode='clay',res=640,color_by='material',views=[('front',0,0,True),('three_quarter',35,10,True)])
