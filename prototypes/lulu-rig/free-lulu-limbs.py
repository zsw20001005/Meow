"""Separate the sculpt's contact-fused limbs and author a visible acting test."""
from pathlib import Path
import bpy,bmesh,math,json,sys
from mathutils import Vector,Quaternion
from mathutils.kdtree import KDTree
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-limbs-v1.blend'))
sc=bpy.context.scene;rig=bpy.data.objects['Lulu Motion Rig']
body=max((o for o in sc.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
rig.animation_data_clear()
for b in rig.pose.bones:b.rotation_quaternion=(1,0,0,0);b.location=(0,0,0);b.scale=(1,1,1)
sc.frame_set(0)
groups={g.index:g.name for g in body.vertex_groups}
paint=body.data.color_attributes['LuluPaint']
original_colors=[tuple(c.color) for c in paint.data]
color_tree=KDTree(len(body.data.vertices))
for v in body.data.vertices:color_tree.insert(v.co,v.index)
color_tree.balance()
regions={name:set() for name in ['Arm.L','Arm.R']}
for v in body.data.vertices:
    weights={groups[g.group]:g.weight for g in v.groups}
    for side in ['L','R']:
        if sum(weights.get(n+'.'+side,0) for n in ['UpperArm','Forearm','Hand'])>.40:regions['Arm.'+side].add(v.index)
all_removed=set.union(regions['Arm.L'],regions['Arm.R'],{v.index for v in body.data.vertices if v.co.z<1.78})
source=body.data.copy()
parts=[]
def extract(obj,keep):
    bm=bmesh.new();bm.from_mesh(source);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS')
    # Close only the freshly separated boundaries; the source surface is kept.
    boundary=[e for e in bm.edges if e.is_boundary]
    boundary_verts=list({v for e in boundary for v in e.verts})
    for _ in range(3):bmesh.ops.smooth_vert(bm,verts=boundary_verts,factor=.25,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    caps=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces']
    bmesh.ops.triangulate(bm,faces=caps)
    for _ in range(2):
        remaining=[e for e in bm.edges if e.is_boundary]
        if remaining:bmesh.ops.holes_fill(bm,edges=remaining,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    for p in obj.data.polygons:p.use_smooth=True
    return len(boundary)
# Neutral arm chains replace the contact-fused rest pose. Upper head, eyes and
# the separate muzzle are retained; lower head/torso/limbs are rebuilt volumes.
new_chains={side:[Vector((s*.62,.02,1.30)),Vector((s*.82,-.01,1.02)),Vector((s*.88,-.05,.77)),Vector((s*.89,-.08,.64))] for side,s in [('L',1),('R',-1)]}
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for side,points in new_chains.items():
    for i,prefix in enumerate(['UpperArm','Forearm','Hand']):
        b=rig.data.edit_bones[prefix+'.'+side];b.head=points[i];b.tail=points[i+1]
bpy.ops.object.mode_set(mode='OBJECT')
yellow=bpy.data.materials.new('Independent limb yellow');yellow.use_nodes=True
bs=yellow.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(1,.6308,.0395,1);bs.inputs['Roughness'].default_value=.78
def skinned_mesh(name,vertices,faces,weights):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(yellow)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);sc.collection.objects.link(o);o.parent=rig
    for f in mesh.polygons:f.use_smooth=True
    for bone,values in weights.items():
        g=o.vertex_groups.new(name=bone)
        for i,w in enumerate(values):
            if w>0:g.add([i],w,'REPLACE')
    m=o.modifiers.new('Independent limb skin','ARMATURE');m.object=rig;parts.append(o);return o
for side,points in new_chains.items():
    shoulder,elbow,wrist,palm=points
    verts=[];faces=[];upper=[];fore=[];rows=28;cols=32
    for j in range(rows+1):
        t=j/rows
        center=(1-t)**2*shoulder+2*(1-t)*t*elbow+t*t*wrist
        tangent=(2*(1-t)*(elbow-shoulder)+2*t*(wrist-elbow)).normalized()
        axis=tangent.cross(Vector((0,1,0))).normalized();axis2=tangent.cross(axis).normalized()
        radius=.155*(1-t)+.105*t
        w=max(0,min(1,(t-.35)/.30));w=w*w*(3-2*w)
        for k in range(cols):
            a=2*math.pi*k/cols;verts.append(center+radius*(axis*math.cos(a)+axis2*math.sin(a)));upper.append(1-w);fore.append(w)
    for j in range(rows):
        for k in range(cols):
            a=j*cols+k;b=j*cols+(k+1)%cols;faces.append((a,b,b+cols,a+cols))
    faces.extend([tuple(reversed(range(cols))),tuple(rows*cols+k for k in range(cols))])
    skinned_mesh('Independent Arm.'+side,verts,faces,{'UpperArm.'+side:upper,'Forearm.'+side:fore})
extract(body,set(range(len(source.vertices)))-all_removed)
# Repair the missing torso/contact patches as volume, rather than leaving
# the triangulated cut planes visible. Remesh only this body copy, then
# transfer its original paint back; eyes and separate muzzle stay untouched.
for mod in list(body.modifiers):body.modifiers.remove(mod)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,location=(0,.05,1.04));fill=bpy.context.object;fill.scale=(.70,.54,.59)
fills=[fill]
for center,radii in [((0,.04,1.85),(.98,.73,.57)),((0,.07,.59),(.77,.54,.28)),((.39,.06,.40),(.29,.38,.17)),((-.36,.06,.40),(.29,.38,.17)),((.62,.02,1.30),(.19,.19,.19)),((-.62,.02,1.30),(.19,.19,.19))]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=28,location=center);o=bpy.context.object;o.scale=radii;fills.append(o)
for o in fills:o.select_set(True)
body.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
remesh=body.modifiers.new('Repair contact surfaces','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.012;remesh.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=remesh.name)
relax=body.modifiers.new('Soften repaired contact surfaces','SMOOTH');relax.factor=.65;relax.iterations=5;bpy.ops.object.modifier_apply(modifier=relax.name)
# Remove disconnected voxel crumbs, never leave detached slivers in the model.
def clean_components(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);unseen=set(bm.verts);components=[]
    while unseen:
        seed=unseen.pop();component={seed};stack=[seed]
        while stack:
            v=stack.pop()
            for edge in v.link_edges:
                w=edge.other_vert(v)
                if w in unseen:unseen.remove(w);component.add(w);stack.append(w)
        components.append(component)
    largest=max(components,key=len)
    bmesh.ops.delete(bm,geom=[v for component in components if component is not largest for v in component],context='VERTS')
    bmesh.ops.dissolve_degenerate(bm,dist=1e-6,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
clean_components(body)
attr=body.data.color_attributes.get('LuluPaint')
if attr:body.data.color_attributes.remove(attr)
attr=body.data.color_attributes.new(name='LuluPaint',type='FLOAT_COLOR',domain='POINT')
for v,c in zip(body.data.vertices,attr.data):c.color=(1,.3095,.010,1) if v.co.z<.81 else original_colors[color_tree.find(v.co)[1]]
for poly in body.data.polygons:poly.use_smooth=True
modifier=body.modifiers.new('Body skin','ARMATURE');modifier.object=rig
body.vertex_groups.clear();gs={name:body.vertex_groups.new(name=name) for name in ['Pelvis','Chest','Head']}
for v in body.data.vertices:
    h=smooth(1.12,1.76,v.co.z);c=(1-h)*smooth(.65,1.05,v.co.z)
    for name,w in [('Head',h),('Chest',c),('Pelvis',1-h-c)]:
        if w>0:gs[name].add([v.index],w,'REPLACE')

# The sculpt has no usable backs on the contact-cut palms and ankles. Replace
# those hidden surfaces with rounded, closed volumes instead of stretched caps.
def solid_part(name,ellipsoids,weight_at):
    solids=[]
    for center,radii in ellipsoids:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=24,location=center)
        o=bpy.context.object;o.scale=radii;solids.append(o)
    for o in solids:o.select_set(True)
    bpy.context.view_layer.objects.active=solids[0];bpy.ops.object.join();o=solids[0];o.name=name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    remesh=o.modifiers.new('Continuous volume','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.008;remesh.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=remesh.name)
    soft=o.modifiers.new('Soft joins','SMOOTH');soft.factor=.5;soft.iterations=3;bpy.ops.object.modifier_apply(modifier=soft.name)
    clean_components(o);o.data.materials.clear();o.data.materials.append(yellow);o.parent=rig
    if name.startswith('Independent Leg.'):
        # The upper moving section is the shorts leg, not exposed yellow skin.
        mat=yellow.copy();mat.name='Moving shorts and leg '+name[-1]
        colors=o.data.color_attributes.new(name='LimbPaint',type='FLOAT_COLOR',domain='POINT')
        for v,c in zip(o.data.vertices,colors.data):
            t=smooth(.33,.36,v.co.z);c.color=(1,.6308*(1-t)+.3095*t,.0395*(1-t)+.010*t,1)
        node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='LimbPaint';mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']);o.data.materials[0]=mat
    gs={}
    for v in o.data.vertices:
        for name,w in weight_at(v.co).items():
            if name not in gs:gs[name]=o.vertex_groups.new(name=name)
            if w>0:gs[name].add([v.index],w,'REPLACE')
    skin=o.modifiers.new('Independent skin','ARMATURE');skin.object=rig
    for p in o.data.polygons:p.use_smooth=True
    parts.append(o)
for side,s in [('L',1),('R',-1)]:
    wrist=new_chains[side][2];palm=new_chains[side][3]
    ellipsoids=[(wrist,(.108,.108,.108)),((palm.x,palm.y,.67),(.112,.095,.13)),((palm.x+s*.12,palm.y-.015,.69),(.065,.073,.085))]
    for dx in [-.065,0,.065]:ellipsoids.append(((palm.x+dx,palm.y-.015,.575),(.045,.075,.07)))
    solid_part('Independent Hand.'+side,ellipsoids,lambda p,side=side:{'Hand.'+side:1})
    x=.39 if side=='L' else -.36
    def leg_weights(p,side=side):
        knee=1-smooth(.24,.44,p.z);ankle=1-smooth(.12,.23,p.z)
        return {'Thigh.'+side:1-knee,'Shin.'+side:knee*(1-ankle),'Foot.'+side:knee*ankle}
    solid_part('Independent Leg.'+side,[((x,.03,.49),(.185,.205,.26)),((x,0,.29),(.165,.185,.17)),((x,-.13,.115),(.225,.30,.115))],leg_weights)

def reset():
    for b in rig.pose.bones:b.rotation_quaternion=(1,0,0,0);b.location=(0,0,0);b.scale=(1,1,1)
def rot(name,axis,degrees):
    b=rig.pose.bones[name];local=b.bone.matrix_local.to_3x3().inverted()@Vector(axis)
    b.rotation_quaternion=Quaternion(local,math.radians(degrees))
def curve(t,points):
    for (a,x),(b,y) in zip(points,points[1:]):
        if t<=b:return x+(y-x)*smooth(a,b,t)
    return points[-1][1]
def up(t,a,b):return math.sin(math.pi*(t-a)/(b-a))**2 if a<t<b else 0
for o in sc.objects:
    keys=o.data.shape_keys if o.type=='MESH' else None
    if keys and keys.animation_data:
        idle=None
        for track in list(keys.animation_data.nla_tracks):
            if track.name=='Greeting':track.name='HumanWave';track.strips[0].name='HumanWave'
            elif track.name=='Idle':idle=track.strips[0].action
            else:keys.animation_data.nla_tracks.remove(track)
        if idle:
            track=keys.animation_data.nla_tracks.new();track.name='HumanSteps';track.mute=True;track.strips.new('HumanSteps',0,idle)
clips={'Idle':6.,'HumanWave':6.,'HumanSteps':6.}
for name,duration in clips.items():
    rig.animation_data_create();action=bpy.data.actions.new(name+' separated skeleton');rig.animation_data.action=action
    for f in range(int(duration*30)+1):
        t=f/30;reset()
        rig.pose.bones['Chest'].scale.y=1+.006*(1-math.cos(2*math.pi*t/duration))
        if name=='HumanWave':
            a=curve(t,[(0,0),(.3,0),(1.2,1),(4.1,1),(5.6,0),(6,0)])
            rot('UpperArm.L',(0,1,0),-70*a);rot('Forearm.L',(0,1,0),-35*a)
            rot('Hand.L',(1,0,0),18*a*math.sin(2*math.pi*(t-1.2)/.85))
            rot('UpperArm.R',(0,1,0),10*a);rot('Forearm.R',(1,0,0),-12*a)
            rot('Chest',(0,1,0),-3*a);rot('Head',(0,1,0),4*a)
        if name=='HumanSteps':
            for side,a,b in [('L',.4,2.6),('R',3.1,5.3)]:
                u=up(t,a,b);sign=1 if side=='L' else -1
                if u<=0:continue
                rot('Thigh.'+side,(1,0,0),-45*u);rot('Shin.'+side,(1,0,0),62*u);rot('Foot.'+side,(1,0,0),-17*u)
                rig.pose.bones['Pelvis'].location.x=-.07*sign*u
                support=rig.pose.bones['Thigh.'+('R' if side=='L' else 'L')]
                support.location=support.bone.matrix_local.to_3x3().inverted()@Vector((.07*sign*u,0,0))
                rot('Chest',(0,1,0),3*sign*u);rot('Head',(0,1,0),-2*sign*u)
                rot('UpperArm.R',(1,0,0),-22*sign*u);rot('UpperArm.L',(0,1,0),-10*u)
        for b in rig.pose.bones:
            for prop in ['rotation_quaternion','location','scale']:b.keyframe_insert(prop,frame=f)
    track=rig.animation_data.nla_tracks.new();track.name=name;track.mute=True
    strip=track.strips.new(name,0,action);strip.extrapolation='NOTHING';rig.animation_data.action=None
reset();sc.frame_set(0)
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts');import check_geometry
names=[body.name]+[o.name for o in parts]
health=check_geometry.run(names=names,spec={'expect_embedded':[[a,b] for i,a in enumerate(names) for b in names[i+1:]]})
(root/'limbs-v2-audit.json').write_text(json.dumps(health,ensure_ascii=False,indent=2,default=str),encoding='utf8')
assert not health['errors'],health['errors']
bpy.ops.wm.save_as_mainfile(filepath=str(root/'lulu-limbs-v2.blend'))
bpy.ops.export_scene.gltf(filepath=str(root/'lulu-limbs-v2.glb'),export_format='GLB',export_extras=True,export_animation_mode='NLA_TRACKS',export_animations=True,export_skins=True,export_morph=True)
print('SEPARATED_LIMBS_DONE')
