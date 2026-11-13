"""Measure every frame of the first wave test without changing the saved model."""
import bpy,json,sys,argparse
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
parser=argparse.ArgumentParser();parser.add_argument('--iteration',default='05')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root=Path(__file__).resolve().parent/'rig-review'/('iter_'+args.iteration)
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-wave-test.blend'),use_scripts=False)
scene=bpy.context.scene;arm=bpy.data.objects['Lulu.Arm.L'];body=bpy.data.objects['Lulu.Body']
foot_ids=np.array([v.index for v in body.data.vertices if v.co.z<.20])
hand_ids=np.array([v.index for v in arm.data.vertices if v.co.z>1.56][::50])
def sample(obj,triangles=False):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=evaluated.to_mesh();coords=np.empty(len(m.vertices)*3);m.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
    tri=None
    if triangles:
        m.calc_loop_triangles();tri=np.array([tuple(t.vertices) for t in m.loop_triangles])
    evaluated.to_mesh_clear();return coords,tri
report={'frames':121,'fps':30,'max_foot_drift':0,'max_arm_step_per_frame':0,'hand_penetration_frames':[],'arm_volume_ratio_min':1,'arm_volume_ratio_max':1}
previous=None
for frame in range(1,122):
    scene.frame_set(frame);p,tri=sample(arm,True);b,_=sample(body)
    volume=abs(np.einsum('ij,ij->i',p[tri[:,0]],np.cross(p[tri[:,1]],p[tri[:,2]])).sum()/6)
    if frame==1:first=p.copy();feet=b[foot_ids].copy();rest_volume=volume
    report['arm_volume_ratio_min']=min(report['arm_volume_ratio_min'],float(volume/rest_volume));report['arm_volume_ratio_max']=max(report['arm_volume_ratio_max'],float(volume/rest_volume))
    report['max_foot_drift']=max(report['max_foot_drift'],float(np.linalg.norm(b[foot_ids]-feet,axis=1).max()))
    if previous is not None:report['max_arm_step_per_frame']=max(report['max_arm_step_per_frame'],float(np.linalg.norm(p-previous,axis=1).max()))
    previous=p
    tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get());inside=0
    for i in hand_ids:
        nearest,normal,_,distance=tree.find_nearest(Vector(p[i]))
        if (Vector(p[i])-nearest).dot(normal)<0 and distance>.01:inside+=1
    if inside:report['hand_penetration_frames'].append({'frame':frame,'samples':inside})
report['loop_position_error']=float(np.linalg.norm(p-first,axis=1).max())
report['pass']=report['max_foot_drift']<1e-6 and report['loop_position_error']<1e-5 and not report['hand_penetration_frames'] and report['arm_volume_ratio_min']>.9
(root/'all-frame-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('ALL_FRAME_CHECKS',json.dumps(report),flush=True)
