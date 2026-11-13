import bpy, bmesh, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'lulu-hunyuan-source.blend'),use_scripts=False)
before = after = 0
for o in [x for x in bpy.context.scene.objects if x.type == 'MESH']:
    before += len(o.data.polygons)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.dissolve_degenerate(bm,dist=0.000001,edges=list(bm.edges))
    bm.to_mesh(o.data); bm.free()
    bpy.context.view_layer.objects.active = o
    mod = o.modifiers.new('Rigging preview mesh reduction','DECIMATE')
    mod.ratio = min(1.0,120000/len(o.data.polygons))
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in o.data.polygons: p.use_smooth=True
    after += len(o.data.polygons)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'lulu-rig-input.glb'),export_format='GLB')
(ROOT/'rig-input-report.json').write_text(json.dumps({'faces_before':before,'faces_after':after,'purpose':'Reduced static mesh for automatic rigging trial; original download unchanged.'},indent=2),encoding='utf-8')
print('RIG_INPUT',before,after,flush=True)
