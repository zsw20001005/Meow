"""Bind the approved v4 model and author gentle, repeatable first motion clips."""
from pathlib import Path
import bpy,math,json
from mathutils import Vector
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-face-v4.blend'))
scene=bpy.context.scene;scene.render.fps=30
body=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
for obj in list(scene.objects):
    if obj.type=='CURVE':
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target='MESH')
meshes=[o for o in scene.objects if o.type=='MESH']
data=bpy.data.armatures.new('Lulu gentle motion skeleton')
rig=bpy.data.objects.new('Lulu Motion Rig',data);scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,head,tail,parent in [('Root',(0,0,0),(0,0,.6),None),('Chest',(0,0,.6),(0,0,1.4),'Root'),('Head',(0,0,1.4),(0,0,2.5),'Chest'),('Wave',(.60,-.22,1.28),(.60,-.22,1.65),'Head')]:
    b=data.edit_bones.new(name);b.head=head;b.tail=tail
    if parent:b.parent=data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
for p in rig.pose.bones:p.rotation_mode='XYZ'
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for obj in meshes:
    groups={name:obj.vertex_groups.new(name=name) for name in ['Root','Chest','Head','Wave']}
    if obj is body:
        for v in obj.data.vertices:
            x,y,z=v.co
            h=smooth(1.12,1.76,z);c=(1-h)*smooth(.25,.70,z)
            w=.8*smooth(.33,.48,x)*(1-smooth(.83,.98,x))*smooth(1.30,1.53,z)*(1-smooth(1.72,1.88,z))*(1-smooth(-.24,-.04,y))
            weights={'Root':(1-h-c)*(1-w),'Chest':c*(1-w),'Head':h*(1-w),'Wave':w}
            for name,value in weights.items():
                if value>0:groups[name].add([v.index],value,'REPLACE')
    else:groups['Head'].add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Lulu skin','ARMATURE');mod.object=rig;obj.parent=rig
# Cartoon blink: compress the visible eye into a thin line while recessing it
# onto the forehead. Catchlights disappear inside the surface when closed.
eye_keys=[];X=Vector((.986,0,.167)).normalized();Z=Vector((-.167,0,.986)).normalized()
for obj in meshes:
    if not obj.name.startswith('Eye '):continue
    side=obj.name.split()[1];ex,ez={'L':(-.371,2.211),'R':(.333,2.319)}[side]
    obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='Blink')
    for original,dst in zip(obj.data.vertices,key.data):
        delta=Vector((original.co.x-ex,0,original.co.z-ez));a=delta.dot(X)
        b=delta.dot(Z)*.025+.016*max(0,1-(a/.098)**2)
        x=ex+X.x*a+Z.x*b;z=ez+X.z*a+Z.z*b
        hit,pos,normal,face=body.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
        assert hit,'Blink must land on the forehead'
        layer=-.005 if 'sclera' in obj.name else .0035
        if 'catchlight' in obj.name:layer=-.004
        dst.co=(x,pos.y-layer,z)
    eye_keys.append(obj.data.shape_keys)
clips={'Idle':4.,'Blink':2.,'Nod':3.2,'Look':4.8,'Wave':4.}
def stash(owner,name,action,end):
    track=owner.animation_data.nla_tracks.new();track.name=name
    strip=track.strips.new(name,0,action);strip.frame_start=0;strip.frame_end=end;strip.extrapolation='NOTHING'
    track.mute=True;owner.animation_data.action=None
for name,duration in clips.items():
    end=round(duration*30)
    rig.animation_data_create();action=bpy.data.actions.new(name+' Skeleton');rig.animation_data.action=action
    for f in range(end+1):
        t=f/30;phase=t/duration;envelope=math.sin(math.pi*phase)**2
        for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.scale=(1,1,1);p.location=(0,0,0)
        # Bone local Y follows Blender Z. Feet keep full root weight.
        rig.pose.bones['Chest'].scale.y=1+.006*(1-math.cos(2*math.pi*phase))
        head=rig.pose.bones['Head'];wave=rig.pose.bones['Wave']
        if name=='Nod':head.rotation_euler.x=math.radians(4)*envelope*math.sin(4*math.pi*phase)
        if name=='Look':head.rotation_euler.y=math.radians(9)*envelope*math.sin(2*math.pi*phase)
        if name=='Wave':
            wave.rotation_euler.z=math.radians(5)*envelope*math.sin(6*math.pi*phase)
            head.rotation_euler.z=math.radians(1.4)*envelope
        for p in rig.pose.bones:
            p.keyframe_insert('rotation_euler',frame=f);p.keyframe_insert('scale',frame=f);p.keyframe_insert('location',frame=f)
    stash(rig,name,action,end)
    for keys in eye_keys:
        keys.animation_data_create();action=bpy.data.actions.new(name+' '+keys.name);keys.animation_data.action=action
        blink=keys.key_blocks['Blink']
        center=.8 if name=='Blink' else duration*.58
        for f in range(end+1):
            t=f/30;d=(t-center)/(.10 if t<center else .15)
            blink.value=(.5+.5*math.cos(math.pi*d)) if abs(d)<1 else 0
            blink.keyframe_insert('value',frame=f)
        stash(keys,name,action,end);blink.value=0
for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.scale=(1,1,1);p.location=(0,0,0)
scene.frame_start=0;scene.frame_end=120;scene.frame_set(0)
rig['motion_scope']='Gentle prototype: breathing, stylized blink, nod, look, small raised-hand wave. No walking or full limb rig.'
bpy.ops.wm.save_as_mainfile(filepath=str(root/'lulu-motion-v1.blend'))
props=bpy.ops.export_scene.gltf.get_rna_type().properties
args=dict(filepath=str(root/'lulu-motion-v1.glb'),export_format='GLB',export_extras=True,export_animations=True,export_skins=True,export_morph=True)
if 'export_animation_mode' in props:args['export_animation_mode']='NLA_TRACKS'
bpy.ops.export_scene.gltf(**args)
(root/'motion-v1-spec.json').write_text(json.dumps({'clips':clips,'fps':30,'source':'lulu-face-v4.blend','scope':rig['motion_scope']},indent=2),encoding='utf-8')
print('MOTION_EXPORTED',json.dumps(clips))
