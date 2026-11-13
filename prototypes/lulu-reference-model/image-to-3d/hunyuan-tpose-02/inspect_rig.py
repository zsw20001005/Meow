import bpy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import render_views,check_geometry
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'rigged/lulu-tpose-mia-original.glb'))
report={'bones':[],'meshes':[]}
for o in list(bpy.context.scene.objects):
    if o.type=='ARMATURE':
        for b in o.data.bones:report['bones'].append({'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(o.matrix_world@b.head_local),'tail':list(o.matrix_world@b.tail_local)})
    if o.type=='MESH':
        mods=[m for m in o.modifiers if m.type=='ARMATURE']
        if not mods:
            o.hide_render=True;o.hide_set(True);continue
        for p in o.data.polygons:p.use_smooth=True
        sums=[sum(g.weight for g in v.groups) for v in o.data.vertices]
        report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'unweighted':sum(w<1e-6 for w in sums),'weight_range':[min(sums),max(sums)],'shape_keys':list(o.data.shape_keys.key_blocks.keys()) if o.data.shape_keys else []})
bpy.context.view_layer.update()
report['geometry']=check_geometry.run(spec={'ground':False,'max_verts':500000})
(ROOT/'rigged/inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'rigged/lulu-tpose-mia-import.blend'))
render_views.run(str(ROOT/'rigged/review-import'),mode='clay',res=640,color_by='material',views=[('front',0,0,True),('three_quarter',35,10,True)])
print('RIG_INSPECTION',json.dumps({k:v for k,v in report.items() if k!='geometry'}),flush=True)
