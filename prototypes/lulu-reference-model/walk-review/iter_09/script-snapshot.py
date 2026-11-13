"""Editable full-body articulation stage derived from the approved sculpt study.
Source files stay read-only. Each iteration writes geometry, motion audits and views.
"""
import bpy,bmesh,math,json,sys,argparse,shutil
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.kdtree import KDTree
sys.path.insert(0,r'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry
ROOT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--iteration',default='01');ap.add_argument('--animate',action='store_true')
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=ROOT/'walk-review'/('iter_'+args.iteration);OUT.mkdir(parents=True,exist_ok=True);shutil.copy2(__file__,OUT/'script-snapshot.py')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'rig-review/iter_05/lulu-wave-test.blend'),use_scripts=False)
scene=bpy.context.scene;oldrig=bpy.data.objects['Lulu articulated test'];oldrig.animation_data_clear()
for pb in oldrig.pose.bones:pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1);pb.location=(0,0,0)
body=bpy.data.objects['Lulu.Body'];original_body=body;oldarm=bpy.data.objects['Lulu.Arm.L']
for o in list(scene.objects):
    if o.parent==oldrig:
        world=o.matrix_world.copy();o.parent=None;o.matrix_world=world
        for m in list(o.modifiers):
            if m.type=='ARMATURE':o.modifiers.remove(m)
        o.vertex_groups.clear()
bpy.data.objects.remove(oldrig,do_unlink=True)
source=body.data.copy();colors=np.array([c.color[:] for c in source.color_attributes['LuluPaint'].data])
# Undo the source statue's permanent head lean, including fitted accessories.
pivot=Vector((-.019,0,2.265));upright=Matrix.Rotation(math.atan2(.108,.704),4,'Y');head_transform=Matrix.Translation(pivot)@upright@Matrix.Translation(-pivot)
for v in source.vertices:
    t=max(0,min(1,(v.co.z-1.25)/.48));t=t*t*(3-2*t);v.co=v.co.lerp(head_transform@v.co,t)
for o in list(scene.objects):
    if o not in (body,oldarm) and o.type in ('MESH','CURVE') and not o.name.startswith('_'):o.matrix_world=head_transform@o.matrix_world
hair_center=Vector((0,0,2.65));hair_fit=Matrix.Translation(hair_center)@Matrix.Diagonal((.90,1,.90,1))@Matrix.Translation(-hair_center)
for o in scene.objects:
    if o.name in ('Hair','HairFlow','Cowlick'):o.matrix_world=hair_fit@o.matrix_world
tree=KDTree(len(source.vertices))
for v in source.vertices:tree.insert(v.co,v.index)
tree.balance()
SKIN=(1,.630757,.039546,1)
def ease(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def activate(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def objmesh(name,verts,faces,materials=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o)
    for m in materials or []:mesh.materials.append(m)
    return o
def cap(bm):
    result=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
    if result['faces']:bmesh.ops.triangulate(bm,faces=result['faces'])
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
def sliced(mesh,name,planes):
    bm=bmesh.new();bm.from_mesh(mesh)
    for co,no,inner in planes:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=co,plane_no=no,dist=1e-6,clear_inner=inner,clear_outer=not inner);cap(bm)
    data=bpy.data.meshes.new(name);bm.to_mesh(data);bm.free();o=bpy.data.objects.new(name,data);scene.collection.objects.link(o)
    for m in mesh.materials:data.materials.append(m)
    return o
def clean(o):
    bm=bmesh.new();bm.from_mesh(o.data);unseen=set(bm.verts);parts=[]
    while unseen:
        v=unseen.pop();part={v};todo=[v]
        while todo:
            for e in todo.pop().link_edges:
                for w in e.verts:
                    if w in unseen:unseen.remove(w);part.add(w);todo.append(w)
        parts.append(part)
    largest=max(parts,key=len);lost=sum(len(p) for p in parts if p is not largest)
    assert lost<len(largest)*.02,(o.name,lost,len(largest))
    if lost:bmesh.ops.delete(bm,geom=[v for p in parts if p is not largest for v in p],context='VERTS')
    bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
def remesh(o,size,smooth=6):
    activate(o);m=o.modifiers.new('Continuous repaired surface','REMESH');m.mode='VOXEL';m.voxel_size=size;m.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=m.name)
    m=o.modifiers.new('Relax surface','SMOOTH');m.factor=.45;m.iterations=smooth;bpy.ops.object.modifier_apply(modifier=m.name);clean(o)
    for p in o.data.polygons:p.use_smooth=True
def join(objects,main):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=main;bpy.ops.object.join();return main
def paint(o,fn):
    for a in list(o.data.color_attributes):o.data.color_attributes.remove(a)
    a=o.data.color_attributes.new(name='LuluPaint',type='FLOAT_COLOR',domain='POINT')
    for v,c in zip(o.data.vertices,a.data):c.color=fn(v.co)
def tube(name,points,radii,cols=40,steps=48,depth=1):
    def point(t):
        f=t*(len(points)-1);i=min(int(f),len(points)-2);u=f-i
        a,b,c,d=[Vector((*points[max(0,min(k,len(points)-1))],radii[max(0,min(k,len(points)-1))])) for k in (i-1,i,i+1,i+2)]
        return .5*(2*b+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)
    verts=[];faces=[]
    for j in range(steps+1):
        t=j/steps;s=point(t);p=Vector(s[:3]);delta=point(min(1,t+.001))-point(max(0,t-.001));direction=Vector(delta[:3]).normalized()
        side=direction.cross(Vector((0,1,0))).normalized();other=direction.cross(side).normalized()
        for i in range(cols):a=math.tau*i/cols;verts.append(tuple(p+s[3]*(side*math.cos(a)+other*math.sin(a)*depth)))
        if j:
            for i in range(cols):a=(j-1)*cols+i;b=(j-1)*cols+(i+1)%cols;faces.append((a,b,b+cols,a+cols))
    faces.extend([tuple(reversed(range(cols))),tuple(steps*cols+i for i in range(cols))]);return objmesh(name,verts,faces,list(source.materials))

# Preserve the source head and one clean half of the shorts/feet. The hanging
# sculpted hand is fused to the other half; remove that contact entirely.
head=sliced(source,'Lulu.HeadBody',[((0,0,1.06),(0,0,1),True)])
lower=sliced(source,'Retained foot',[((0,0,.12),(0,0,1),False),((.10,0,0),(1,0,0),True)])
def lower_height(z):return z+.16*ease(.06,.25,z)*(1-ease(.55,.82,z))
source_z=np.linspace(0,.85,851);target_z=lower_height(source_z)
for v in lower.data.vertices:
    v.co.x=(v.co.x-.10)*.82-.0828;v.co.y=(v.co.y-.08)*.92
    angle=math.atan2((v.co.y-.092)/.95,v.co.x-.36);target=Vector((.36+.17*math.cos(angle),.092+.17*.95*math.sin(angle),v.co.z));v.co=v.co.lerp(target,float(ease(.04,.12,v.co.z)))
mirror=lower.copy();mirror.data=lower.data.copy();scene.collection.objects.link(mirror)
for v in mirror.data.vertices:v.co.x=-v.co.x
bm=bmesh.new();bm.from_mesh(mirror.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(mirror.data);bm.free()
lower=join([lower,mirror],lower)
# The source shorts are solid sculpture, not anatomy. Replace the hidden volume
# with two deformable legs and a pelvis, while retaining the original foot shape.
leg_parts=[]
for sign in [1,-1]:
    leg_parts.append(tube('Neutral leg surface',[(sign*.36,.092,.72),(sign*.36,.08,.60),(sign*.36,.047,.43),(sign*.36,.075,.27),(sign*.36,.092,.08)],[.22,.218,.19,.178,.17],depth=.95))
bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,location=(0,.035,.735));pelvis=bpy.context.object;pelvis.name='Hidden pelvis';pelvis.scale=(.60,.485,.185);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for m in source.materials:pelvis.data.materials.append(m)
lower=join([lower,pelvis,*leg_parts],lower)
# A measured, smooth torso bridge removes repaired neck dents and old fused arm.
zs=[.72,.82,.94,1.08,1.20,1.30,1.40,1.49,1.57]
rx=[.72,.71,.66,.59,.55,.59,.68,.79,.84];ry=[.55,.54,.52,.49,.47,.49,.55,.60,.63]
for v in head.data.vertices:
    z=v.co.z;w=float(1-ease(1.16,1.67,z))
    if w>0:
        xr=np.interp(z,zs,rx);yr=np.interp(z,zs,ry);cy=.04*(1-ease(1.15,1.57,z));angle=math.atan2((v.co.y-cy)/yr,v.co.x/xr)
        target=Vector((xr*math.cos(angle),cy+yr*math.sin(angle),z));v.co=v.co.lerp(target,w)
verts=[];faces=[];rows=64;cols=96
for j in range(rows+1):
    z=zs[0]+(1.28-zs[0])*j/rows;xrad=np.interp(z,zs,rx);yrad=np.interp(z,zs,ry);cy=.04*(1-ease(1.15,1.57,z))
    for i in range(cols):a=math.tau*i/cols;verts.append((xrad*math.cos(a),cy+yrad*math.sin(a),z))
    if j:
        for i in range(cols):a=(j-1)*cols+i;b=(j-1)*cols+(i+1)%cols;faces.append((a,b,b+cols,a+cols))
faces.extend([tuple(reversed(range(cols))),tuple(rows*cols+i for i in range(cols))])
bridge=objmesh('Torso surface repair',verts,faces,list(source.materials))
body=join([head,lower,bridge],head);body.name='Lulu.Body';remesh(body,.009,10)
# Relax only the rebuilt shoulder/neck band. Face, feet and clothing details stay.
activate(body);g=body.vertex_groups.new(name='Neck surface refinement')
for v in body.data.vertices:
    w=ease(1.05,1.24,v.co.z)*(1-ease(1.58,1.73,v.co.z))
    if w>0:g.add([v.index],float(w),'REPLACE')
m=body.modifiers.new('Smooth neck join','SMOOTH');m.vertex_group=g.name;m.factor=.7;m.iterations=45;bpy.ops.object.modifier_apply(modifier=m.name);body.vertex_groups.clear()
def bodycolor(p):
    if p.z<.87:return SKIN
    q=p.copy()
    if p.z<.85:q.x=abs(p.x)/.82+.10;q.y=p.y/.92+.08;q.z=np.interp(p.z,target_z,source_z)
    c=colors[tree.find(q)[1]].copy();w=float(ease(.74,.78,p.z)*(1-ease(1.40,1.56,p.z)))
    tint=np.array((1,.23,.035,1))*(1-ease(.805,.818,p.z))+np.array(SKIN)*ease(.805,.818,p.z)
    return c*(1-w)+tint*w
paint(body,bodycolor)
bpy.data.objects.remove(original_body,do_unlink=True)
body.name='Lulu.Body'

# Reorient the retained hand, remove its planar wrist cap, soften the knuckles,
# then fuse with a relaxed arm. Both sides share the same neutral proportions.
oldw=Vector((.64,-.60,1.50));oldd=(Vector((.55,-.74,1.64))-oldw).normalized()
newchain=[Vector(p) for p in [(.62,.035,1.30),(.79,-.04,1.08),(.94,-.20,.79),(.96,-.24,.66)]]
arm=sliced(oldarm.data,'Lulu.Arm.L.new',[(oldw-oldd*.005,oldd,True)])
rot=oldd.rotation_difference((newchain[3]-newchain[2]).normalized())
for v in arm.data.vertices:
    p=rot@((v.co-oldw)*.80);d=(newchain[3]-newchain[2]).normalized();u=p.dot(d);radial=p-d*u
    v.co=newchain[2]+d*u+radial*(.66+.34*ease(0,.09,u))
forearm=tube('Relaxed arm surface',[tuple(p) for p in [newchain[0],Vector((.72,.0,1.19)),newchain[1],Vector((.88,-.12,.94)),newchain[2],newchain[2]+(newchain[3]-newchain[2])*.35]],[.15,.15,.132,.117,.100,.09],depth=.91)
arm=join([arm,forearm],arm);remesh(arm,.006,10);paint(arm,lambda p:SKIN);arm.name='Lulu.Arm.L'
bpy.data.objects.remove(oldarm,do_unlink=True);arm.name='Lulu.Arm.L'
other=arm.copy();other.data=arm.data.copy();scene.collection.objects.link(other);other.name='Lulu.Arm.R'
for v in other.data.vertices:v.co.x=-v.co.x
bm=bmesh.new();bm.from_mesh(other.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(other.data);bm.free()
meshes=[body,arm,other]
geometry=check_geometry.run(names=[o.name for o in meshes],spec={'ground':False},max_verts=500000,out_path=str(OUT/'geometry.json'))
assert geometry['summary']['errors']==0,'Geometry errors must be fixed before animation'

# Full deformation hierarchy; analytic two-bone IK bakes deterministic poses.
data=bpy.data.armatures.new('Lulu full-body skeleton');rig=bpy.data.objects.new('Lulu full-body skeleton',data);scene.collection.objects.link(rig);activate(rig);bpy.ops.object.mode_set(mode='EDIT')
bones=[('Root',(0,0,0),(0,0,.3),None),('Hips',(0,.02,.74),(0,.02,.90),'Root'),('Torso',(0,.02,.90),(0,.02,1.30),'Hips'),('Head',(0,.02,1.42),(-.019,0,2.265),'Torso')]
chains={}
for side,sign in [('L',1),('R',-1)]:
    ch=[Vector((sign*p.x,p.y,p.z)) for p in newchain];chains[side]=ch
    for i,n in enumerate(['UpperArm','LowerArm','Hand']):bones.append((n+'.'+side,ch[i],ch[i+1],'Torso' if i==0 else ['UpperArm','LowerArm'][i-1]+'.'+side))
    hip=(sign*.36,.092,.72);knee=(sign*.36,.047,.43);ankle=(sign*.36,.092,.115);toe=(sign*.36,-.10,.08);tip=(sign*.36,-.22,.08)
    for n,a,b,p in [('Thigh',hip,knee,'Hips'),('Shin',knee,ankle,'Thigh.'+side),('Foot',ankle,toe,'Shin.'+side),('Toe',toe,tip,'Foot.'+side)]:bones.append((n+'.'+side,a,b,p))
for n,a,b,p in bones:
    eb=data.edit_bones.new(n);eb.head=a;eb.tail=b
    if p:eb.parent=data.edit_bones[p]
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
def bind(obj,weights):
    obj.vertex_groups.clear()
    for n,values in weights.items():
        g=obj.vertex_groups.new(name=n)
        for i,w in enumerate(values):
            if w>1e-6:g.add([i],float(w),'REPLACE')
    m=obj.modifiers.new('Full body skin','ARMATURE');m.object=rig;m.use_deform_preserve_volume=True;world=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=world
coords=np.array([v.co[:] for v in body.data.vertices]);z=coords[:,2];x=coords[:,0];N=len(z)
h=ease(1.12,1.72,z);torso=(1-h)*ease(.72,1.05,z);hip=1-h-torso
weights={'Hips':hip.copy(),'Torso':torso,'Head':h}
vertex_colors=np.array([c.color[:] for c in body.data.color_attributes['LuluPaint'].data]);cloth=(vertex_colors[:,1]<.46)&(z>.25)&(z<.84)
for side,sgn in [('L',1),('R',-1)]:
    lateral=ease(-.10,.10,sgn*x);leg=(1-ease(.50,.80,z))*lateral
    leg=np.where(cloth,np.minimum(leg,.27*(1-ease(.50,.79,z))*lateral),leg)
    knee=1-ease(.31,.51,z);knee=np.where(cloth,0,knee);foot=1-ease(.13,.24,z)
    weights['Thigh.'+side]=leg*(1-knee);weights['Shin.'+side]=leg*knee*(1-foot);weights['Foot.'+side]=leg*foot
    weights['Hips']-=leg
weights['Hips']=np.maximum(0,weights['Hips']);total=sum(weights.values())
for n in weights:weights[n]/=total
bind(body,weights)
for side,o in [('L',arm),('R',other)]:
    ch=chains[side];length=[(b-a).length for a,b in zip(ch,ch[1:])];cumulative=np.r_[0,np.cumsum(length)];weights={n+'.'+side:np.zeros(len(o.data.vertices)) for n in ['UpperArm','LowerArm','Hand']};weights['Torso']=np.zeros(len(o.data.vertices))
    for v in o.data.vertices:
        samples=[]
        for i,(a,b) in enumerate(zip(ch,ch[1:])):
            d=b-a;t=max(0,min(1,(v.co-a).dot(d)/d.length_squared));samples.append(((v.co-a-d*t).length,cumulative[i]+t*length[i]))
        u=min(samples)[1];el=ease(cumulative[1]-.10,cumulative[1]+.10,u);wr=ease(cumulative[2]-.055,cumulative[2]+.055,u);shoulder=1-ease(.015,.13,u)
        for n,w in zip(['UpperArm','LowerArm','Hand'],[(1-el)*(1-shoulder),el*(1-wr)*(1-shoulder),wr*(1-shoulder)]):weights[n+'.'+side][v.index]=w
        weights['Torso'][v.index]=shoulder
    # Diffuse influences over the actual skin so the elbow does not form a cuff.
    edges=np.array([tuple(e.vertices) for e in o.data.edges]);a,b=edges.T;degree=np.bincount(edges.ravel(),minlength=len(o.data.vertices))
    for n,values in weights.items():
        for _ in range(35):values=.5*values+.5*(np.bincount(a,weights=values[b],minlength=len(values))+np.bincount(b,weights=values[a],minlength=len(values)))/np.maximum(degree,1)
        weights[n]=values
    total=sum(weights.values())
    for n in weights:weights[n]/=total
    bind(o,weights)
parts=[o for o in scene.objects if o not in (*meshes,rig) and o.type in ('MESH','CURVE') and not o.name.startswith('_')]
for o in parts:
    if o.type=='CURVE':activate(o);bpy.ops.object.convert(target='MESH')
    bind(o,{'Head':np.ones(len(o.data.vertices))})

# Join the shoulder surface, retaining a hidden skinned torso for contact tests.
collision=body.copy();collision.data=body.data.copy();collision.name='_Torso collision reference';scene.collection.objects.link(collision);collision.hide_render=True;collision.hide_set(True)
names=list(data.bones.keys());sample_positions=[];sample_weights=[];sample_colors=[]
for o in meshes:
    index={g.index:names.index(g.name) for g in o.vertex_groups if g.name in names}
    for v,c in zip(o.data.vertices,o.data.color_attributes['LuluPaint'].data):
        w=np.zeros(len(names))
        for g in v.groups:
            if g.group in index:w[index[g.group]]=g.weight
        sample_positions.append(v.co.copy());sample_weights.append(w);sample_colors.append(c.color[:])
    for m in list(o.modifiers):
        if m.type=='ARMATURE':o.modifiers.remove(m)
    o.parent=None
transfer=KDTree(len(sample_positions))
for i,p in enumerate(sample_positions):transfer.insert(p,i)
transfer.balance();sample_weights=np.array(sample_weights);sample_colors=np.array(sample_colors)
body=join(meshes,body);body.name='Lulu.Body';remesh(body,.008,8)
activate(body);g=body.vertex_groups.new(name='Wrist and shoulder refinement')
for v in body.data.vertices:
    x,y,z=v.co;w=max(float(ease(.45,.64,abs(x))*ease(1.04,1.12,z)*(1-ease(1.28,1.42,z))),float(ease(.80,.90,abs(x))*ease(.65,.70,z)*(1-ease(.80,.87,z))))
    if w>0:g.add([v.index],w,'REPLACE')
m=body.modifiers.new('Organic joint surface','SMOOTH');m.vertex_group=g.name;m.factor=.5;m.iterations=60;bpy.ops.object.modifier_apply(modifier=m.name)
newweights=np.zeros((len(body.data.vertices),len(names)));newcolors=[]
for v in body.data.vertices:
    found=transfer.find_n(v.co,4);ids=[i for p,i,d in found];w=np.array([1/max(d,.0005)**2 for p,i,d in found]);w/=w.sum();newweights[v.index]=w@sample_weights[ids];newcolors.append(w@sample_colors[ids])
paint(body,lambda p:SKIN)
for c,value in zip(body.data.color_attributes['LuluPaint'].data,newcolors):c.color=value
positions=np.array([v.co[:] for v in body.data.vertices]);ax=np.abs(positions[:,0]);zz=positions[:,2]
jointmask=ease(.42,.66,ax)*ease(.82,1.01,zz)*(1-ease(1.27,1.48,zz))
edges=np.array([tuple(e.vertices) for e in body.data.edges]);a,b=edges.T;degree=np.bincount(edges.ravel(),minlength=len(positions))
for i,n in enumerate(names):
    values=newweights[:,i]
    if values.max()==0:continue
    for _ in range(60):
        neighbors=(np.bincount(a,weights=values[b],minlength=len(values))+np.bincount(b,weights=values[a],minlength=len(values)))/np.maximum(degree,1)
        values+=.5*jointmask*(neighbors-values)
    newweights[:,i]=values
newweights/=newweights.sum(axis=1)[:,None]
bind(body,{n:newweights[:,i] for i,n in enumerate(names) if newweights[:,i].max()>0})
g=body.vertex_groups.new(name='Joint corrective region')
for i,w in enumerate(jointmask):
    if w>0:g.add([i],float(w),'REPLACE')
m=body.modifiers.new('Preserve smooth shoulder bending','CORRECTIVE_SMOOTH');m.vertex_group=g.name;m.factor=.8;m.iterations=18;m.smooth_type='LENGTH_WEIGHTED';m.use_only_smooth=False
geometry=check_geometry.run(names=[body.name],spec={'ground':False},max_verts=600000,out_path=str(OUT/'fused-geometry.json'))
assert geometry['summary']['errors']==0,'Fused skin geometry must pass'
# A real separate garment: one waist opening and two leg openings. A central
# crotch bridge splits the lower boundary; solidify makes a closed cloth shell.
verts=[];faces=[];cols=64;levels=[0,.025,.09,.20,.34,.50,.66,.80,.91,.975,1]
for row,t in enumerate(levels):
    rx=.76+.060*math.sin(math.pi*t)-.070*t;ry=.59+.025*math.sin(math.pi*t)-.080*t
    for i in range(cols):
        angle=math.tau*(i+.5)/cols;x=rx*math.cos(angle);y=.035+ry*math.sin(angle)
        hem=.37+.075*math.exp(-(x/.115)**2);waist=.835-.015*max(0,-math.sin(angle))**2;z=waist*(1-t)+hem*t;verts.append((x,y,z))
    if row:
        for i in range(cols):a=(row-1)*cols+i;b=(row-1)*cols+(i+1)%cols;faces.append((a,b,b+cols,a+cols))
last=(len(levels)-1)*cols;faces.append(tuple(last+i for i in [15,16,47,48]))
shorts=objmesh('Lulu.Shorts',verts,faces,list(source.materials));activate(shorts)
sub=shorts.modifiers.new('Rounded tailored shorts','SUBSURF');sub.levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
solid=shorts.modifiers.new('Cloth thickness','SOLIDIFY');solid.thickness=.014;solid.offset=0;bpy.ops.object.modifier_apply(modifier=solid.name)
for p in shorts.data.polygons:p.use_smooth=True
paint(shorts,lambda p:(1,.23,.025,1))
cloth=shorts.data.materials[0].copy();cloth.name='Lulu orange fabric';shorts.data.materials.clear();shorts.data.materials.append(cloth)
nodes=cloth.node_tree.nodes;shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');shader.inputs['Roughness'].default_value=.9
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=110;noise.inputs['Detail'].default_value=2
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.10;bump.inputs['Distance'].default_value=.0018;cloth.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);cloth.node_tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])
def garment_bind(o):
    p=np.array([v.co[:] for v in o.data.vertices]);leg=.20*(1-ease(.47,.77,p[:,2]));left=ease(-.12,.12,p[:,0]);bind(o,{'Hips':1-leg,'Thigh.L':leg*left,'Thigh.R':leg*(1-left)})
garment_bind(shorts)
verts=[];faces=[];n=96;m=10
for i in range(n):
    a=math.tau*(i+.5)/n;p=Vector((.76*math.cos(a),.035+.59*math.sin(a),.835-.015*max(0,-math.sin(a))**2));normal=Vector((math.cos(a)/.76,math.sin(a)/.59,0)).normalized()
    for j in range(m):b=math.tau*j/m;verts.append(tuple(p+.014*(normal*math.cos(b)+Vector((0,0,1))*math.sin(b))))
for i in range(n):
    for j in range(m):faces.append((i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m))
band=objmesh('Lulu.Waistband',verts,faces,list(shorts.data.materials));paint(band,lambda p:(1,.205,.021,1))
for p in band.data.polygons:p.use_smooth=True
garment_bind(band)
clothing=check_geometry.run(names=[shorts.name,band.name],spec={'ground':False},max_verts=600000,out_path=str(OUT/'clothing-geometry.json'))
assert clothing['summary']['errors']==0,'Garment shell must pass geometry checks'
PERIOD=1.3;SPEED=.40;STANCE=.60;STRIDE=SPEED*PERIOD*STANCE;FPS=60;FRAME_COUNT=157
def set_world_rot(name,axis,angle):
    pb=rig.pose.bones[name];a=pb.bone.matrix_local.to_3x3().inverted()@Vector(axis);pb.rotation_quaternion=Quaternion(a,angle)
def position_bone(name,start,end):
    pb=rig.pose.bones[name];rest=pb.bone;rot=(rest.tail_local-rest.head_local).rotation_difference(end-start)@rest.matrix_local.to_quaternion()
    pb.matrix=Matrix.LocRotScale(start,rot,Vector((1,1,1)));bpy.context.view_layer.update()
def foot_path(u):
    if u<STANCE:return .092+STRIDE*(u/STANCE-.5),0.,True
    s=(u-STANCE)/(1-STANCE);a=STRIDE*.5;b=-a;m=SPEED*PERIOD*(1-STANCE)
    y=a+m*s+(b-a-m)*(10*s**3-15*s**4+6*s**5)
    return .092+y,.085*math.sin(math.pi*s)**3,False
def pose(t):
    for pb in rig.pose.bones:pb.rotation_quaternion=(1,0,0,0);pb.location=(0,0,0);pb.scale=(1,1,1)
    u=(t/PERIOD)%1;phase=math.tau*u
    # Short-legged gait: small body bob and contralateral arm swing.
    rig.pose.bones['Hips'].location=(.020*math.sin(phase),-.025-.010*math.cos(phase*2),0)
    set_world_rot('Hips',(0,0,1),.025*math.sin(phase));set_world_rot('Torso',(0,0,1),-.040*math.sin(phase));set_world_rot('Head',(0,0,1),.015*math.sin(phase))
    bpy.context.view_layer.update();audit=[]
    for side,offset in [('L',0),('R',.5)]:
        pu=(u+offset)%1;y,lift,stance=foot_path(pu);target=Vector((.36 if side=='L' else -.36,y,.115+lift))
        thigh=rig.pose.bones['Thigh.'+side];hip=thigh.head.copy();l1=thigh.bone.length;l2=data.bones['Shin.'+side].length;d=(target-hip).length;direction=(target-hip).normalized()
        assert d<l1+l2-.0001,('Unreachable foot',side,t,d,l1+l2)
        along=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-along*along));forward=Vector((0,-1,0));pole=(forward-direction*forward.dot(direction)).normalized();knee=hip+direction*along+pole*height
        position_bone('Thigh.'+side,hip,knee);position_bone('Shin.'+side,knee,target)
        foot=rig.pose.bones['Foot.'+side];foot.matrix=Matrix.LocRotScale(target,foot.bone.matrix_local.to_quaternion(),Vector((1,1,1)));bpy.context.view_layer.update()
        swing=math.cos(math.tau*pu);set_world_rot('UpperArm.'+side,(1,0,0),math.radians(18)*swing);set_world_rot('LowerArm.'+side,(1,0,0),math.radians(-4-4*(1-swing)*.5));set_world_rot('Hand.'+side,(1,0,0),math.radians(3)*math.sin(math.tau*pu-.35))
        audit.append({'side':side,'stance':stance,'target':list(target),'ankle_error':(foot.head-target).length})
    bpy.context.view_layer.update();return audit
scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=FRAME_COUNT
rig.animation_data_create();rig.animation_data.action=bpy.data.actions.new('Lulu walk • 2 cycles • 60 fps')
audit={'bones':len(data.bones),'fps':FPS,'period_seconds':PERIOD,'speed_units_per_second':SPEED,'foot_targets':[]}
# Only the skeleton needs evaluation while baking curves; restore skin for review.
disabled=[]
for o in scene.objects:
    for mod in o.modifiers:
        if mod.type in ('ARMATURE','CORRECTIVE_SMOOTH') and mod.show_viewport:mod.show_viewport=False;disabled.append(mod)
for f in range(FRAME_COUNT):
    audit['foot_targets'].append({'frame':f+1,'feet':pose(f/FPS)})
    for pb in rig.pose.bones:
        for prop in ['location','rotation_quaternion','scale']:pb.keyframe_insert(prop,frame=f+1)
for fc in rig.animation_data.action.fcurves:
    for key in fc.keyframe_points:key.interpolation='LINEAR'
for mod in disabled:mod.show_viewport=True
(OUT/'motion-targets.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=64;scene.render.resolution_x=scene.render.resolution_y=720;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=-.4
focus=Vector((0,0,1.55));cam=scene.camera;cam.data.ortho_scale=3.65
light=bpy.data.lights.new('Walk front fill','AREA');light.energy=120;light.shape='DISK';light.size=5;o=bpy.data.objects.new('Walk front fill',light);scene.collection.objects.link(o);o.location=(0,-4,1.7);o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
for name,frame,pos in [('front',1,(0,-10,1.8)),('passing',21,(0,-10,1.8)),('side',21,(8,-2,1.8)),('back',1,(0,10,1.8)),('three-quarter',40,(6,-9,2.5))]:
    scene.frame_set(frame);cam.location=pos;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(4,-10,2.2);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'lulu-walk.blend'))
if args.animate:
    scene.render.resolution_x=scene.render.resolution_y=600;frames=OUT/'frames';frames.mkdir(exist_ok=True);scene.render.filepath=str(frames/'frame-');bpy.ops.render.render(animation=True)
print('WALK_READY',OUT)
