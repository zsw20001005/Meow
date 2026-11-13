"""Make the successful automatic rig editable; retain source shape and skin weights.
World-space bones have useful lengths and symmetric pivots. No procedural character rebuild.
"""
import bpy,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'rigged'
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import render_views,check_geometry
bpy.ops.wm.open_mainfile(filepath=str(OUT/'lulu-tpose-mia-import.blend'),use_scripts=False)
old=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers))
def world_vertices(obj):
    bpy.context.view_layer.update()
    e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return np.array([e.matrix_world@v.co for v in e.data.vertices])
original=world_vertices(mesh)
bones={b.name:{'head':old.matrix_world@b.head_local,'parent':b.parent.name if b.parent else None} for b in old.data.bones}
prefix='mixamorig:'
# Average the corresponding pivots, avoiding the noticeably different auto-estimated knee heights.
for suffix in ['Shoulder','Arm','ForeArm','Hand','UpLeg','Leg','Foot','ToeBase']:
    l=bones[prefix+'Left'+suffix]['head'];r=bones[prefix+'Right'+suffix]['head']
    x=(abs(l.x)+abs(r.x))/2;y=(l.y+r.y)/2;z=(l.z+r.z)/2
    bones[prefix+'Left'+suffix]['head']=Vector((x,y,z))
    bones[prefix+'Right'+suffix]['head']=Vector((-x,y,z))
for name,b in bones.items():
    if not ('Left' in name or 'Right' in name):b['head'].x=0
# Bake object coordinates, never bake deformed poses into the rest mesh.
mat=mesh.matrix_world.copy()
mesh.parent=None;mesh.matrix_world=Matrix.Identity(4);mesh.data.transform(mat)
for mod in list(mesh.modifiers):
    if mod.type=='ARMATURE':mesh.modifiers.remove(mod)
for obj in list(bpy.context.scene.objects):
    if obj!=mesh:bpy.data.objects.remove(obj,do_unlink=True)
mesh.name='Lulu_Body'
# Smooth only skin influence transitions; do not move vertices or soften the sculpture.
nv=len(mesh.data.vertices);ng=len(mesh.vertex_groups)
weights=np.zeros((nv,ng),dtype=np.float32)
for v in mesh.data.vertices:
    for g in v.groups:weights[v.index,g.group]=g.weight
weight_before=weights.copy()
edge_pairs=np.array([e.vertices[:] for e in mesh.data.edges],dtype=np.int32)
ei=np.concatenate([edge_pairs[:,0],edge_pairs[:,1]])
ej=np.concatenate([edge_pairs[:,1],edge_pairs[:,0]])
degree=np.bincount(ei,minlength=nv).astype(np.float32)
zone=(original[:,2]<1.60).astype(np.float32)
# Feather off smoothing near the head so the facial/glasses shape stays rigid.
zone*=np.clip((1.60-original[:,2])/.15,0,1)
blend=zone[:,None]*.65
for _ in range(36):
    avg=np.stack([np.bincount(ei,weights=weights[ej,j],minlength=nv)/np.maximum(degree,1) for j in range(ng)],axis=1)
    weights=(weights*(1-blend)+avg*blend).astype(np.float32)
weights[weights<1e-6]=0
weights/=np.maximum(weights.sum(axis=1,keepdims=True),1e-12)
for vg in mesh.vertex_groups:vg.remove(list(range(nv)))
for j,vg in enumerate(mesh.vertex_groups):
    for i in np.flatnonzero(weights[:,j]>0):vg.add([int(i)],float(weights[i,j]),'REPLACE')
data=bpy.data.armatures.new('Lulu_Skeleton')
rig=bpy.data.objects.new('Lulu_Rig',data);bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);mesh.select_set(False)
bpy.ops.object.mode_set(mode='EDIT')
nexts={'Hips':'Spine','Spine':'Spine1','Spine1':'Spine2','Spine2':'Neck','Neck':'Head'}
for side in ['Left','Right']:
    for a,b in [('Shoulder','Arm'),('Arm','ForeArm'),('ForeArm','Hand'),('UpLeg','Leg'),('Leg','Foot'),('Foot','ToeBase')]:nexts[side+a]=side+b
for name,b in bones.items():
    eb=data.edit_bones.new(name);eb.head=b['head'];short=name.removeprefix(prefix)
    if short in nexts:eb.tail=bones[prefix+nexts[short]]['head']
    elif short=='Head':eb.tail=eb.head+Vector((0,0,0.85))
    elif 'Hand' in short:eb.tail=eb.head+Vector((0.20 if 'Left' in short else -0.20,0,0))
    else:eb.tail=eb.head+Vector((0,-0.13,0))
for name,b in bones.items():
    if b['parent']:
        eb=data.edit_bones[name];parent=data.edit_bones[b['parent']];eb.parent=parent
        eb.use_connect=(eb.head-parent.tail).length<1e-5
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front=True;data.display_type='OCTAHEDRAL'
mod=mesh.modifiers.new('Lulu skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
mesh.parent=rig
correction=mesh.modifiers.new('Joint surface correction (Blender)','CORRECTIVE_SMOOTH')
correction.factor=.6;correction.iterations=12;correction.smooth_type='LENGTH_WEIGHTED'
for p in mesh.data.polygons:p.use_smooth=True
# Recompute normals from the deformed surface instead of preserving the GLB's
# per-corner normals, which produced false dark wrinkles after skinning.
bpy.context.view_layer.objects.active=mesh
if mesh.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.context.view_layer.objects.active=rig
rest=world_vertices(mesh)
report={'bone_count':len(data.bones),'rest_shape_max_delta':float(np.linalg.norm(rest-original,axis=1).max()),'bone_names':list(data.bones.keys()),'weight_source':'MIA v2 with 36 graph-Laplacian smoothing passes below neck, normalized','weight_changed_vertices':int(np.sum(np.abs(weights-weight_before).max(axis=1)>1e-4)),'coordinate_height':3.0,'tail':'Geometry retained, follows pelvis; no independent tail control','facial_rig':False}
assert report['rest_shape_max_delta']<1e-4,report
report['deformation']='Blender preserve-volume skinning + 12-iteration corrective smooth; GLB compatibility export does not support these runtime corrections.'
def clear_pose():
    for pb in rig.pose.bones:pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion();pb.location=(0,0,0);pb.scale=(1,1,1)
def rotate(name,axis,degrees):
    pb=rig.pose.bones[prefix+name]
    axis_local=pb.bone.matrix_local.to_3x3().inverted()@Vector(axis)
    pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(axis_local,math.radians(degrees))
def pose(kind,strength=1):
    clear_pose()
    if kind=='rest':return
    for side,sign in [('Left',1),('Right',-1)]:rotate(side+'Arm',(0,1,0),sign*45)
    if kind=='wave':
        rotate('LeftArm',(0,1,0),15)
        rotate('LeftForeArm',(0,1,0),-65*strength)
    if kind=='elbows':
        rotate('LeftForeArm',(0,0,1),-55*strength)
        rotate('RightForeArm',(0,0,1),55*strength)
    if kind in ('left_step','right_step'):
        side='Left' if kind=='left_step' else 'Right'
        rotate(side+'UpLeg',(1,0,0),-22*strength)
        rotate(side+'Leg',(1,0,0),35*strength)
        rotate(side+'Foot',(1,0,0),-13*strength)
report['poses']={}
edges=np.array([e.vertices[:] for e in mesh.data.edges])
base_len=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
valid=base_len>0.001
for kind in ['rest','relaxed','wave','elbows','left_step','right_step']:
    pose(kind)
    deformed=world_vertices(mesh)
    ratio=np.linalg.norm(deformed[edges[:,0]]-deformed[edges[:,1]],axis=1)[valid]/base_len[valid]
    report['poses'][kind]={'finite':bool(np.isfinite(deformed).all()),'max_motion':float(np.linalg.norm(deformed-rest,axis=1).max()),'edge_stretch_p99':float(np.quantile(ratio,.99)),'edges_over_3x':int(sum(ratio>3))}
    render_views.run(str(OUT/'poses-v5'/kind),mode='clay',res=640,color_by='material',views=[('front',0,0,True),('three_quarter',35,10,True)])
clear_pose();bpy.context.view_layer.update()
report['geometry']=check_geometry.run(spec={'ground':True,'max_verts':500000},names=[mesh.name])
(OUT/'rig-quality-report-v5.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=240;scene.render.fps=30
# A diagnostic action: relaxing arms, elbow flexion, greeting and alternate leg lifts.
# It is deliberately labelled a joint test, not a finished locomotion clip.
keys=[(1,'rest',1),(31,'relaxed',1),(61,'elbows',1),(81,'relaxed',1),(111,'wave',1),(131,'wave',.65),(151,'wave',1),(171,'relaxed',1),(191,'left_step',1),(211,'relaxed',1),(231,'right_step',1),(240,'relaxed',1)]
for frame,kind,strength in keys:
    pose(kind,strength)
    for pb in rig.pose.bones:pb.keyframe_insert('rotation_quaternion',frame=frame)
rig.animation_data.action.name='Lulu_Joint_Check'
scene.frame_set(31)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'lulu-tpose-rigged-v5.blend'))
# Deliver a neutral-rest GLB with the same diagnostic action embedded.
scene.frame_set(1)
correction.show_viewport=False;correction.show_render=False;mod.use_deform_preserve_volume=False
bpy.ops.export_scene.gltf(filepath=str(OUT/'lulu-tpose-rigged-lbs.glb'),export_format='GLB',export_animations=True,export_all_influences=True)
print('RIG_QUALITY',json.dumps({k:v for k,v in report.items() if k!='geometry'}),flush=True)
