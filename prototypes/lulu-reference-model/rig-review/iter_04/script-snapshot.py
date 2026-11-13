"""First articulated shoulder/elbow/wrist test on the separated source sculpt."""
import bpy,bmesh,math,json,sys,argparse,shutil
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
sys.path.insert(0,r'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--iteration',default='01');parser.add_argument('--animate',action='store_true');parser.add_argument('--source',default='06')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
OUT=ROOT/'rig-review'/('iter_'+args.iteration);OUT.mkdir(parents=True,exist_ok=True)
shutil.copy2(__file__,OUT/'script-snapshot.py')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'articulation'/('iter_'+args.source)/'lulu-articulation.blend'),use_scripts=False)
body=bpy.data.objects['Lulu.Body'];arm=bpy.data.objects['Lulu.Arm.L'];scene=bpy.context.scene
reference=bpy.data.objects.get('_Source reference')
if reference:bpy.data.objects.remove(reference,do_unlink=True)
data=bpy.data.armatures.new('Lulu articulated test');rig=bpy.data.objects.new('Lulu articulated test',data);scene.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
chain=[Vector(p) for p in [(.63,.04,1.25),(.78,-.24,1.23),(.64,-.60,1.50),(.55,-.74,1.64)]]
bones=[('Root',(0,0,0),(0,0,.4),None),('Hips',(0,0,.4),(0,0,.75),'Root'),('Torso',(0,0,.75),(0,0,1.25),'Hips'),('Head',(0,.02,1.45),(-.019,0,2.265),'Torso')]
for i,name in enumerate(['UpperArm.L','LowerArm.L','Hand.L']):bones.append((name,chain[i],chain[i+1],'Torso' if i==0 else ['UpperArm.L','LowerArm.L'][i-1]))
for name,start,end,parent in bones:
    b=data.edit_bones.new(name);b.head=start;b.tail=end
    if parent:b.parent=data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
for b in rig.pose.bones:b.rotation_mode='QUATERNION'

# Retain the sculpted palm/fingers; replace the folded contact cap with a
# rounded shoulder-to-wrist surface having regular longitudinal sections.
bm=bmesh.new();bm.from_mesh(arm.data)
normal=(chain[3]-chain[2]).normalized()
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=chain[2]-normal*.025,plane_no=normal,dist=.00001,clear_inner=True,clear_outer=False)
caps=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces'];bmesh.ops.triangulate(bm,faces=caps)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(arm.data);bm.free()
controls=[(*p,r) for p,r in zip([chain[0],Vector((.72,-.10,1.24)),chain[1],Vector((.72,-.42,1.37)),chain[2],chain[2]+normal*.065],[.13,.145,.145,.13,.115,.11])]
def section(t):
    f=t*(len(controls)-1);i=min(int(f),len(controls)-2);u=f-i
    a,b,c,d=[Vector(controls[max(0,min(k,len(controls)-1))]) for k in (i-1,i,i+1,i+2)]
    return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)
rows=48;cols=40;verts=[];faces=[]
for j in range(rows+1):
    t=j/rows;s=section(t);p=Vector(s[:3]);d=section(min(1,t+.002))-section(max(0,t-.002));tangent=Vector(d[:3]).normalized()
    side=tangent.cross(Vector((0,0,1))).normalized();depth=tangent.cross(side).normalized()
    for i in range(cols):
        a=math.tau*i/cols;verts.append(tuple(p+s[3]*(side*math.cos(a)+depth*math.sin(a))))
    if j:
        for i in range(cols):a=(j-1)*cols+i;b=(j-1)*cols+(i+1)%cols;faces.append((a,b,b+cols,a+cols))
faces.extend([tuple(reversed(range(cols))),tuple(rows*cols+i for i in range(cols))])
mesh=bpy.data.meshes.new('Regular arm sections');mesh.from_pydata(verts,[],faces);mesh.update()
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
tube=bpy.data.objects.new('Arm retopology',mesh);scene.collection.objects.link(tube)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);tube.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.join()
remesh=arm.modifiers.new('Fuse retained palm and regular arm','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.006;remesh.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth=arm.modifiers.new('Soften wrist transition','SMOOTH');smooth.factor=.4;smooth.iterations=3;bpy.ops.object.modifier_apply(modifier=smooth.name)
bm=bmesh.new();bm.from_mesh(arm.data);unseen=set(bm.verts);components=[]
while unseen:
    seed=unseen.pop();part={seed};todo=[seed]
    while todo:
        for e in todo.pop().link_edges:
            for v in e.verts:
                if v in unseen:unseen.remove(v);part.add(v);todo.append(v)
    components.append(part)
largest=max(components,key=len);crumbs=[v for c in components if c is not largest for v in c]
assert len(crumbs)<len(largest)*.01,'Do not discard a substantial piece of the original hand'
if crumbs:bmesh.ops.delete(bm,geom=crumbs,context='VERTS')
bm.to_mesh(arm.data);bm.free()
paint=arm.data.color_attributes.get('LuluPaint')
if paint:arm.data.color_attributes.remove(paint)
paint=arm.data.color_attributes.new(name='LuluPaint',type='FLOAT_COLOR',domain='POINT')
for c in paint.data:c.color=(1,.630757,.039546,1)
for p in arm.data.polygons:p.use_smooth=True
geometry=check_geometry.run(names=[arm.name],spec={'ground':False},out_path=str(OUT/'arm-geometry.json'))
assert geometry['summary']['errors']==0,'Arm geometry must pass before binding'
def ease(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def bind(obj,weights):
    obj.vertex_groups.clear();groups={name:obj.vertex_groups.new(name=name) for name in weights}
    for name,values in weights.items():
        for i,w in enumerate(values):
            if w>.000001:groups[name].add([i],float(w),'REPLACE')
    mod=obj.modifiers.new('Lulu skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
    obj.parent=rig
n=len(body.data.vertices);weights={k:np.zeros(n) for k in ['Hips','Torso','Head']}
for v in body.data.vertices:
    h=ease(1.15,1.72,v.co.z);tor=(1-h)*ease(.65,1.05,v.co.z)
    weights['Head'][v.index]=h;weights['Torso'][v.index]=tor;weights['Hips'][v.index]=1-h-tor
bind(body,weights)
lengths=[(b-a).length for a,b in zip(chain,chain[1:])];cumulative=np.r_[0,np.cumsum(lengths)]
weights={k:np.zeros(len(arm.data.vertices)) for k in ['UpperArm.L','LowerArm.L','Hand.L']}
for v in arm.data.vertices:
    samples=[]
    for i,(a,b) in enumerate(zip(chain,chain[1:])):
        d=b-a;t=max(0,min(1,(v.co-a).dot(d)/d.length_squared));samples.append(((v.co-a-d*t).length,cumulative[i]+t*lengths[i]))
    u=min(samples)[1];elbow=ease(cumulative[1]-.095,cumulative[1]+.095,u);wrist=ease(cumulative[2]-.065,cumulative[2]+.065,u)
    for name,w in zip(weights,[1-elbow,elbow*(1-wrist),wrist]):weights[name][v.index]=w
# Diffuse longitudinal weights over the actual mesh to avoid abrupt elbow folds.
edges=np.array([tuple(e.vertices) for e in arm.data.edges]);a,b=edges.T;degree=np.bincount(edges.ravel(),minlength=len(arm.data.vertices))
for name in weights:
    values=weights[name]
    for _ in range(18):
        neighbors=np.bincount(a,weights=values[b],minlength=len(values))+np.bincount(b,weights=values[a],minlength=len(values))
        values=.5*values+.5*neighbors/np.maximum(degree,1)
    weights[name]=values
total=sum(weights.values())
for name in weights:weights[name]/=total
bind(arm,weights)
# All face accessories follow the same head bone with their existing rest transforms.
parts=[o for o in list(scene.objects) if o not in (body,arm,rig) and not o.name.startswith('_') and o.type in ('MESH','CURVE')]
for obj in parts:
    world=obj.matrix_world.copy()
    if obj.type=='CURVE':
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH')
    bind(obj,{'Head':np.ones(len(obj.data.vertices))});obj.matrix_world=world

def reset():
    for b in rig.pose.bones:b.rotation_quaternion=(1,0,0,0);b.scale=(1,1,1);b.location=(0,0,0)
def rotate_world(name,axis,degrees):
    b=rig.pose.bones[name];local=b.bone.matrix_local.to_3x3().inverted()@Vector(axis)
    b.rotation_quaternion=b.rotation_quaternion@Quaternion(local,math.radians(degrees))
def pose(t,arm_only=False):
    reset();envelope=ease(.25,1.15,t)*(1-ease(3.05,3.85,t))
    rotate_world('UpperArm.L',(0,0,1),82*envelope)
    rotate_world('UpperArm.L',(0,1,0),-12*envelope)
    clearance=ease(.10,.35,t)*(1-ease(3.80,4.0,t))
    spread=ease(.65,1.15,t)*(1-ease(3.05,3.55,t))
    rotate_world('LowerArm.L',(1,0,0),28*clearance-43*spread)
    wave=ease(1.1,1.35,t)*(1-ease(2.7,3.0,t))*math.sin((t-1.1)*math.tau*1.65)
    rotate_world('Hand.L',(0,1,0),12*wave)
    rotate_world('Hand.L',(0,0,1),8*wave)
    if not arm_only:
        look=ease(.15,.8,t)*(1-ease(3.0,3.8,t));rotate_world('Head',(0,0,1),4*look);rotate_world('Head',(1,0,0),-2*look)
        rig.pose.bones['Torso'].scale.z=1+.0025*math.sin(math.pi*t/4)**2
    bpy.context.view_layer.update()
def coordinates(obj):
    mesh=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh();a=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',a)
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear();return a.reshape(-1,3)
pose(0,True);baseline=coordinates(body);face_ids=np.array([v.index for v in body.data.vertices if v.co.z>1.75])
audit={'scope':'One separated arm plus head/torso; not a full-body locomotion rig','bones':len(data.bones),'fps':30,'duration_seconds':4,'arm_only_face_max_displacement':0,'hand_samples':[]}
for t in [0,.5,1,1.5,2,2.5,3,3.5,4]:
    pose(t,True);delta=np.linalg.norm(coordinates(body)[face_ids]-baseline[face_ids],axis=1).max()
    audit['arm_only_face_max_displacement']=max(audit['arm_only_face_max_displacement'],float(delta))
assert audit['arm_only_face_max_displacement']<1e-6,'Arm controls must not pull facial vertices'
probe_ids=[v.index for v in arm.data.vertices if v.co.z>1.56][::35]
for t in [.30,.50,.75,1.0,1.3,1.8,2.3,2.8,3.25,3.50,3.75]:
    pose(t);dep=bpy.context.evaluated_depsgraph_get();surface=BVHTree.FromObject(body,dep);p=coordinates(arm)
    distances=[];inside=0
    for i in probe_ids:
        nearest,normal,index,distance=surface.find_nearest(Vector(p[i]));distances.append(distance)
        if (Vector(p[i])-nearest).dot(normal)<0 and distance>.01:inside+=1
    audit['hand_samples'].append({'seconds':t,'min_body_distance':min(distances),'penetrating_sample_count':inside})
(OUT/'motion-checks.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
audit['hand_clearance_pass']=all(x['penetrating_sample_count']==0 for x in audit['hand_samples'])
(OUT/'motion-checks.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
scene.render.fps=30;scene.frame_start=1;scene.frame_end=121
rig.animation_data_create();rig.animation_data.action=bpy.data.actions.new('Lulu source arm greeting')
for f in range(121):
    pose(f/30)
    for b in rig.pose.bones:
        b.keyframe_insert('rotation_quaternion',frame=f+1);b.keyframe_insert('scale',frame=f+1)
for fc in rig.animation_data.action.fcurves:
    for key in fc.keyframe_points:key.interpolation='LINEAR'
scene.frame_set(1);focus=Vector((.15,0,1.6));cam=scene.camera;cam.data.ortho_scale=3.9
cam.location=(0,-10,1.6);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=scene.render.resolution_y=720;scene.cycles.samples=24
for name,f,pos in [('rest',1,(0,-10,1.6)),('wave',61,(0,-10,1.6)),('wave-side',61,(8,-6,2.4))]:
    scene.frame_set(f);cam.location=pos;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(0,-10,1.6);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'lulu-wave-test.blend'))
if args.animate:
    assert audit['hand_clearance_pass'],'Do not publish an animation with detected hand penetration'
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=16
    scene.render.resolution_x=scene.render.resolution_y=600;scene.render.image_settings.file_format='PNG'
    frames=OUT/'frames';frames.mkdir(exist_ok=True);scene.render.filepath=str(frames/'frame-')
    bpy.ops.render.render(animation=True)
print('RIG_REVIEW',str(OUT),audit)
