import bpy,numpy as np,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parent/'walk-review/iter_10'
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-walk.blend'),use_scripts=False)
report=json.loads((root/'motion-checks.json').read_text());item=report['sampled_hand_penetrations'][0];bpy.context.scene.frame_set(item['frame'])
body=bpy.data.objects['Lulu.Body'];group=body.vertex_groups['Hand.'+item['side']].index;ids=[v.index for v in body.data.vertices if any(g.group==group and g.weight>.35 for g in v.groups)];ids=ids[::max(1,len(ids)//220)]
dep=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dep);mesh=ev.to_mesh();hits=[]
for name,limit in [('_Torso collision reference',.008),('Lulu.Shorts',.001)]:
    surface=BVHTree.FromObject(bpy.data.objects[name],dep)
    for i in ids:
        p=mesh.vertices[i].co;near,normal,index,d=surface.find_nearest(p)
        if (p-near).dot(normal)<0 and d>limit:hits.append({'surface':name,'vertex':i,'point':list(p),'nearest':list(near),'normal':list(normal),'distance':d,'rest':list(body.data.vertices[i].co)})
print('CONTACT_DETAIL',json.dumps({'frame':item['frame'],'hits':hits}))
ev.to_mesh_clear()
