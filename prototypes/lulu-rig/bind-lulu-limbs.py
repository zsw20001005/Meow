"""Add editable limb chains to the existing performance model, without replacing it.

This is a bounded deformation rig for the posed sculpt, not neutral-pose
retopology. Raised-arm range stays small because its surface joins the cheek.
"""
from pathlib import Path
import bpy, math, json, sys
import numpy as np
from mathutils import Vector, Quaternion
from mathutils.kdtree import KDTree
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-performance-v1.blend'))
sc=bpy.context.scene;rig=bpy.data.objects['Lulu Motion Rig']
body=max((o for o in sc.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
inherited={};durations={'Idle':6.,'Greeting':6.,'Smile':4.,'Curious':4.}
source_actions={t.name:t.strips[0].action for t in rig.animation_data.nla_tracks}
rig.animation_data_clear()
for name,duration in durations.items():
    frames=[]
    for f in range(round(duration*30)+1):
        for curve in source_actions[name].fcurves:
            rig.path_resolve(curve.data_path)[curve.array_index]=curve.evaluate(f)
        frames.append({b.name:(b.rotation_euler.to_quaternion().copy(),b.location.copy(),b.scale.copy()) for b in rig.pose.bones})
    inherited[name]=frames
assert max(frame['Chest'][2].y for frame in inherited['Idle'])>1.001,'Inherited breathing did not evaluate'
for o in sc.objects:
    if o.type=='MESH' and o.data.shape_keys:
        keys=o.data.shape_keys
        if keys.animation_data:
            for track in keys.animation_data.nla_tracks:track.mute=True
        for k in list(keys.key_blocks)[1:]:k.value=0
for b in rig.pose.bones:b.rotation_euler=(0,0,0);b.location=(0,0,0);b.scale=(1,1,1)

# Coordinates measured on the normalized sculpt (height 3, Z up, front -Y).
# L/R are the character's sides, not the viewer's.
chains={
 'Arm.L':[(.63,.04,1.25),(.78,-.24,1.23),(.64,-.60,1.50),(.55,-.74,1.64)],
 'Arm.R':[(-.60,.19,1.24),(-.76,.19,.98),(-.74,.18,.73),(-.70,.18,.61)],
 'Leg.L':[(.39,.04,.64),(.39,.01,.36),(.40,-.04,.16),(.40,-.27,.10)],
 'Leg.R':[(-.36,.04,.64),(-.36,.01,.36),(-.37,-.04,.16),(-.37,-.27,.10)]}
joint_names={side:[prefix+'.'+side.split('.')[1] for prefix in (['UpperArm','Forearm','Hand'] if side.startswith('Arm') else ['Thigh','Shin','Foot'])] for side in chains}
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT');eb=rig.data.edit_bones
if 'Wave' in eb:eb.remove(eb['Wave'])
p=eb.new('Pelvis');p.head=(0,0,.40);p.tail=(0,0,.65);p.parent=eb['Root'];eb['Chest'].parent=p
for side,points in chains.items():
    parent='Chest' if side.startswith('Arm') else 'Pelvis'
    for i,name in enumerate(joint_names[side]):
        b=eb.new(name);b.head=points[i];b.tail=points[i+1];b.parent=eb[parent];b.use_connect=i>0;parent=name
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig.data.display_type='OCTAHEDRAL'
for p in rig.pose.bones:p.rotation_mode='QUATERNION'

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

n=len(body.data.vertices);pos=np.empty(n*3);body.data.vertices.foreach_get('co',pos);pos=pos.reshape(-1,3);x,y,z=pos.T
edges=np.empty(len(body.data.edges)*2,dtype=np.int32);body.data.edges.foreach_get('vertices',edges);a,b=edges.reshape(-1,2).T
degree=np.bincount(np.r_[a,b],minlength=n)
def relax(values,steps):
    for _ in range(steps):
        average=(np.bincount(a,weights=values[b],minlength=n)+np.bincount(b,weights=values[a],minlength=n))/np.maximum(degree,1)
        values=.45*values+.55*average
    return values

# Reuse the curvature-segmented raised hand rather than a box cutting into face.
with bpy.data.libraries.load(str(root/'source-normalized.blend'),link=False) as (src,dst):dst.meshes=list(src.meshes)
source=max(dst.meshes,key=lambda m:len(m.vertices))
with np.load(root/'surface-regions.npz') as masks:hand=masks['hand'].copy()
tree=KDTree(int(np.count_nonzero(hand)))
for i in np.flatnonzero(hand):tree.insert(source.vertices[int(i)].co,int(i))
tree.balance()
raised=np.zeros(n)
for v in body.data.vertices:
    if v.co.x>.15 and 1.02<v.co.z<1.88 and v.co.y<.15:
        # Undo the maximum forward adjustment only for region classification.
        q=v.co.copy();q.y+=.12*float(smooth(1.1,1.5,q.z))
        distance=tree.find(q)[2];raised[v.index]=1-float(smooth(.018,.13,distance))
raised=relax(raised,180)
# The hanging arm is behind the side seam; keep the orange shorts out of it.
paint=np.empty(n*4);body.data.color_attributes['LuluPaint'].data.foreach_get('color',paint);paint=paint.reshape(-1,4)
yellow=smooth(.25,.42,paint[:,1])
lower=smooth(.51,.71,-x)*(1-smooth(1.12,1.40,z))*smooth(.49,.63,z)*smooth(-.12,.08,y)*yellow
lower=relax(lower,100)
legs=(1-smooth(.38,.78,z))
side_left=smooth(-.10,.10,x)
region={'Arm.L':raised,'Arm.R':lower,'Leg.L':legs*side_left,'Leg.R':legs*(1-side_left)}
names=['Root','Pelvis','Chest','Head']+[name for chain in joint_names.values() for name in chain]
w={name:np.zeros(n) for name in names}
remaining=np.ones(n)
for side,mask in region.items():
    mask=np.minimum(mask,remaining);remaining-=mask
    points=np.asarray(chains[side]);distances=[];along=[]
    for start,end in zip(points,points[1:]):
        delta=end-start;t=np.clip((pos-start)@delta/np.dot(delta,delta),0,1)
        distances.append(np.linalg.norm(pos-(start+t[:,None]*delta),axis=1));along.append(t)
    # Nearest position along the bent chain defines the longitudinal weights.
    closest=np.argmin(np.stack(distances,axis=1),axis=1)
    lengths=np.linalg.norm(np.diff(points,axis=0),axis=1);cumulative=np.r_[0,np.cumsum(lengths)]
    u=np.choose(closest,[cumulative[i]+along[i]*lengths[i] for i in range(3)])
    width=.085 if side.startswith('Arm') else .065
    elbow=smooth(cumulative[1]-width,cumulative[1]+width,u)
    wrist=smooth(cumulative[2]-width,cumulative[2]+width,u)
    if side.startswith('Leg'):
        elbow=1-smooth(.23,.43,z);wrist=1-smooth(.10,.22,z)
    for name,value in zip(joint_names[side],[1-elbow,elbow*(1-wrist),wrist]):w[name]=mask*value
h=smooth(1.12,1.76,z);c=(1-h)*smooth(.60,1.0,z)
w['Head']=remaining*h;w['Chest']=remaining*c;w['Pelvis']=remaining*(1-h-c)
# Smooth final weights over connected edges, then normalize and prune to four
# influences so Blender and glTF use the same skinning weights.
matrix=np.column_stack([relax(w[name],70) for name in names]);top=np.argsort(matrix,axis=1)[:,-4:]
pruned=np.zeros_like(matrix);np.put_along_axis(pruned,top,np.take_along_axis(matrix,top,axis=1),axis=1)
pruned/=pruned.sum(axis=1,keepdims=True)
body.vertex_groups.clear()
for i,name in enumerate(names):
    g=body.vertex_groups.new(name=name)
    for idx in np.flatnonzero(pruned[:,i]>1e-8):g.add([int(idx)],float(pruned[idx,i]),'REPLACE')
for mod in body.modifiers:
    if mod.type=='ARMATURE':mod.use_deform_preserve_volume=False

# Store the intended limited first-pass ranges for the interactive controls.
controls=[]
for side in chains:
    for i,name in enumerate(joint_names[side]):
        limit=([8,10,10] if side=='Arm.L' else [18,22,15] if side=='Arm.R' else [15,22,15])[i]
        controls.append({'name':name,'limit':limit,'axis':'X','vertices':int(np.count_nonzero(pruned[:,names.index(name)]>.05))})

def rotate(name,axis,degrees):
    bone=rig.pose.bones[name];local=bone.bone.matrix_local.to_3x3().inverted()@Vector(axis)
    bone.rotation_quaternion=Quaternion(local,math.radians(degrees))
def reset():
    for bone in rig.pose.bones:bone.rotation_quaternion=(1,0,0,0);bone.location=(0,0,0);bone.scale=(1,1,1)
def beat(t,start,end):return math.sin(math.pi*(t-start)/(end-start))**2 if start<t<end else 0
clips={**durations,'Arms':5.,'Legs':5.,'Steps':6.}
for name,duration in clips.items():
    rig.animation_data_create();action=bpy.data.actions.new(name+' Limb skeleton');rig.animation_data.action=action
    for f in range(round(duration*30)+1):
        t=f/30;reset()
        rig.pose.bones['Chest'].scale.y=1+.003*(1-math.cos(2*math.pi*t/duration))
        if name in inherited:
            for bone_name,(rotation,location,scale) in inherited[name][f].items():
                if bone_name=='Wave':
                    rotate('Hand.L',(0,0,1),math.degrees(rotation.to_euler().z))
                else:
                    bone=rig.pose.bones[bone_name];bone.rotation_quaternion=rotation;bone.location=location;bone.scale=scale
        if name=='Arms':
            u=beat(t,.3,4.7)
            rotate('UpperArm.R',(0,1,0),16*u);rotate('Forearm.R',(1,0,0),-20*u);rotate('Hand.R',(0,0,1),10*u)
            rotate('UpperArm.L',(0,0,1),5*u);rotate('Forearm.L',(1,0,0),-7*u);rotate('Hand.L',(0,1,0),8*u)
        if name in ['Legs','Steps']:
            for side,start,end in [('L',.3,2.4),('R',2.6,4.7)]:
                u=beat(t,start,end)
                rotate('Thigh.'+side,(1,0,0),-12*u);rotate('Shin.'+side,(1,0,0),20*u);rotate('Foot.'+side,(1,0,0),-8*u)
                if name=='Steps':rotate('UpperArm.R',(1,0,0),(10 if side=='L' else -10)*u)
        for bone in rig.pose.bones:
            for prop in ['rotation_quaternion','location','scale']:bone.keyframe_insert(prop,frame=f)
    track=rig.animation_data.nla_tracks.new();track.name=name;track.mute=True
    strip=track.strips.new(name,0,action);strip.extrapolation='NOTHING';rig.animation_data.action=None
reset();sc.frame_start=0;sc.frame_end=180;sc.frame_set(0)
rig['limb_scope']='12 limb joints + pelvis, bounded FK deformation study. Raised hand still fused to cheek; no full walking/contact solver.'
report={'height':3,'joint_chains':chains,'controls':controls,'clips':clips,'weights_max_error':float(np.max(np.abs(pruned.sum(axis=1)-1))),'unweighted_vertices':int(np.sum(pruned.sum(axis=1)==0)),'scope':rig['limb_scope']}
assert all(c['vertices']>20 for c in controls),controls
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts');import check_geometry
health=check_geometry.run(names=[body.name,'Lulu rounded muzzle','Eye L sclera','Eye R sclera'],spec={'expect_embedded':[['Eye * sclera',body.name],['Lulu rounded muzzle',body.name]]})
report['health']=health;assert not health['errors'],health['errors']
bpy.ops.wm.save_as_mainfile(filepath=str(root/'lulu-limbs-v1.blend'))
bpy.ops.export_scene.gltf(filepath=str(root/'lulu-limbs-v1.glb'),export_format='GLB',export_extras=True,export_animation_mode='NLA_TRACKS',export_animations=True,export_skins=True,export_morph=True)
(root/'limbs-v1-spec.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print('LIMBS_EXPORTED',json.dumps({k:v for k,v in report.items() if k!='health'},ensure_ascii=False))
