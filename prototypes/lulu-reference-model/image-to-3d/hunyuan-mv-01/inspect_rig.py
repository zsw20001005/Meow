import bpy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, 'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import render_views, check_geometry
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'rigged/lulu-mia-rigged.glb'))
report = {'armatures': [], 'meshes': []}
for o in bpy.context.scene.objects:
    if o.type == 'ARMATURE':
        report['armatures'].append({'name':o.name,'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in o.data.bones]})
    elif o.type == 'MESH':
        weights=[sum(g.weight for g in v.groups) for v in o.data.vertices]
        report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'unweighted':sum(w<1e-6 for w in weights),'min_sum':min(weights),'max_sum':max(weights),'shape_keys':list(o.data.shape_keys.key_blocks.keys()) if o.data.shape_keys else [],'armature_modifiers':[m.object.name for m in o.modifiers if m.type=='ARMATURE' and m.object]})
        for p in o.data.polygons: p.use_smooth=True
report['geometry'] = check_geometry.run(spec={'ground':False,'max_verts':2000000})
(ROOT/'rigged/rig-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'rigged/lulu-mia-rigged.blend'))
render_views.run(str(ROOT/'rigged/review'),mode='clay',res=640,color_by='material',views=[('front',0,0,True),('side',90,0,True),('back',180,0,True),('three_quarter',35,10,True)])
print('RIG_REPORT',json.dumps(report),flush=True)
