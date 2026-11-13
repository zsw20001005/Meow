"""Checks the saved evaluated mesh, not merely intended bone target curves."""
import bpy,numpy as np,json,sys,argparse,bmesh
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser();ap.add_argument('--iteration',default='03');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root=Path(__file__).resolve().parent/'walk-review'/('iter_'+args.iteration)
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-walk.blend'),use_scripts=False)
sc=bpy.context.scene;rig=bpy.data.objects['Lulu full-body skeleton'];body=bpy.data.objects['Lulu.Body'];collision=bpy.data.objects.get('_Torso collision reference');meta=json.loads((root/'motion-targets.json').read_text());fps=meta['fps'];period=meta['period_seconds'];speed_units=meta['speed_units_per_second'];count=sc.frame_end;cycle=round(fps*period)
def coords(o):
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();a=np.empty(len(m.vertices)*3);m.vertices.foreach_get('co',a);ev.to_mesh_clear();return a.reshape(-1,3)
directions=[Vector(d).normalized() for d in [(1,.371,.173),(.219,1,.457),(.413,.197,1)]]
def inside_surface(surface,point):
    votes=0
    for direction in directions:
        origin=point+direction*1e-7;hits=0
        for _ in range(64):
            hit,normal,index,distance=surface.ray_cast(origin,direction)
            if hit is None:break
            hits+=1;origin=hit+direction*1e-5
        votes+=hits%2
    return votes>=2
rest=np.array([v.co[:] for v in body.data.vertices]);feet=[np.where((rest[:,0]*sgn>0)&(rest[:,2]<.035))[0][::8] for sgn in [1,-1]]
handids=[]
for side in ['L','R']:
    group=body.vertex_groups['Hand.'+side].index
    ids=[v.index for v in body.data.vertices if any(g.group==group and g.weight>.35 for g in v.groups)]
    handids.append(ids[::max(1,len(ids)//220)])
baseline=None;prevfeet=[None,None];prevstance=[False,False];skid=[];floors=[];maxankle=0;penetrations=[];samples=[];poses=[];ground_min=[]
shorts=bpy.data.objects.get('Lulu.Shorts');cloth_protrusions=[]
arm_groups={g.index for g in body.vertex_groups if any(tag in g.name for tag in ['Arm.','Hand.'])}
covered=[v.index for v in body.data.vertices if .53<v.co.z<.79 and not any(g.group in arm_groups and g.weight>.05 for g in v.groups)]
covered=covered[::max(1,len(covered)//300)]
for f in range(1,count+1):
    sc.frame_set(f);a=coords(body);pose=[a];dep=bpy.context.evaluated_depsgraph_get();surface=BVHTree.FromObject(collision,dep);t=(f-1)/fps
    ground_min.append(float(a[:,2].min()))
    cloth_surface=BVHTree.FromObject(shorts,dep) if shorts else None
    for i in range(2):
        p=a;bad=0
        for idx in handids[i]:
            near,norm,_,distance=surface.find_nearest(Vector(p[idx]))
            if distance>.008 and inside_surface(surface,Vector(p[idx])):bad+=1
            if cloth_surface:
                near,norm,_,distance=cloth_surface.find_nearest(Vector(p[idx]))
                if distance>.001 and inside_surface(cloth_surface,Vector(p[idx])):bad+=1
        if bad:penetrations.append({'frame':f,'side':['L','R'][i],'count':bad})
    poses.append(np.concatenate([p[::20] for p in pose]))
    if cloth_surface:
        bad=0;maximum=0
        for idx in covered:
            p=Vector(a[idx])
            if not .53<p.z<.76:continue
            origin=Vector((0,.035,p.z));d=p-origin;radius=d.length
            hit,normal,face,distance=cloth_surface.ray_cast(origin,d.normalized())
            if hit and radius>distance+.022:bad+=1;maximum=max(maximum,radius-distance)
        if bad:cloth_protrusions.append({'frame':f,'sample_count':bad,'max_excess':maximum})
    for i,side in enumerate(['L','R']):
        u=((t/period)+i*.5)%1;stance=u<.60
        p=a[feet[i]].copy();p[:,1]-=speed_units*t
        if stance:
            floors.extend(p[:,2].tolist())
            if prevstance[i]:skid.append(float(np.linalg.norm((p-prevfeet[i])[:,:2],axis=1).max()))
        prevstance[i]=stance;prevfeet[i]=p
    if (f-1) % (cycle//4)==0:samples.append({'frame':f,'body_min_z':float(a[:,2].min())})
poses=np.array(poses);speed=np.linalg.norm(np.diff(poses,axis=0),axis=2);acc=np.linalg.norm(np.diff(poses,n=2,axis=0),axis=2)
report={'frames':count,'bone_count':len(rig.data.bones),'foot_plant_max_step_drift':max(skid),'stance_sole_min_z':min(floors),'stance_sole_max_z':max(floors),'sampled_hand_penetrations':penetrations,'cycle_position_error':float(np.linalg.norm(poses[cycle]-poses[0],axis=1).max()),'end_position_error':float(np.linalg.norm(poses[-1]-poses[0],axis=1).max()),'cycle_velocity_jump':float(np.linalg.norm((poses[1]-poses[0])-(poses[cycle+1]-poses[cycle]),axis=1).max()),'max_sample_vertex_step':float(speed.max()),'max_sample_acceleration':float(acc.max()),'samples':samples}
report['loop_wrap_velocity_delta']=float(np.linalg.norm((poses[1]-poses[0])-(poses[cycle]-poses[cycle-1]),axis=1).max())
report['hand_sample_count']=[len(ids) for ids in handids]
report['clothing_protrusion_samples']=cloth_protrusions
report['point_inside_method']='Majority ray parity in three non-axis-aligned directions; nearest-face normal is not used as an inside test.'
report['all_frame_min_ground_clearance']=min(ground_min)
report['pass']=report['foot_plant_max_step_drift']<.002 and report['cycle_position_error']<1e-5 and report['end_position_error']<1e-5 and min(ground_min)>-.004 and not penetrations and not cloth_protrusions
(root/'motion-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('WALK_CHECKS',json.dumps(report))
