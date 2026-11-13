"""A six-second greeting study with gaze, surface eyelids and a closed smile.

Keeps the original motion prototype intact. This is a performance study, not
a replacement for the later neutral-pose/retopology and full hand rig work.
"""
from pathlib import Path
import bpy,math,json
from mathutils import Vector
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-motion-v1.blend'))
scene=bpy.context.scene;scene.render.fps=30
rig=bpy.data.objects['Lulu Motion Rig']
body=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
for o in list(scene.objects):
    o.animation_data_clear()
    if o.type=='MESH' and o.data.shape_keys:o.shape_key_clear()
for b in rig.pose.bones:b.rotation_euler=(0,0,0);b.scale=(1,1,1);b.location=(0,0,0)
scene.frame_set(0)
X=Vector((.986,0,.167)).normalized();Z=Vector((-.167,0,.986)).normalized()
def xyz(ex,ez,a,b):return ex+X.x*a+Z.x*b,ez+X.z*a+Z.z*b
def uv(ex,ez,p):
    d=Vector((p.x-ex,0,p.z-ez));return d.dot(X),d.dot(Z)
def front(obj,x,z):
    hit,p,n,f=obj.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
    if not hit:
        hit,p,n,f=body.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
    assert hit,'Surface attachment failed'
    return p.y
def skin(obj):
    group=obj.vertex_groups.new(name='Head');group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Face follows head','ARMATURE');mod.object=rig;obj.parent=rig
def mesh(name,verts,faces,mat):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);d.materials.append(mat)
    for p in d.polygons:p.use_smooth=True
    skin(o);return o
def linear(h):
    v=[int(h[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in v)+(1,)
lidmat=bpy.data.materials.new('Lulu soft yellow eyelids');lidmat.use_nodes=True
bs=lidmat.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=linear('#FFD038');bs.inputs['Roughness'].default_value=.75
owners=[];gaze_owners=[];lids=[];creases=[];recess_owners=[]
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for side,(ex,ez) in {'L':(-.371,2.211),'R':(.333,2.319)}.items():
    sclera=bpy.data.objects['Eye '+side+' sclera']
    # Preserve the eyeballs. Move the iris over their curved front surface.
    for part,lift in [('iris',.0007),('pupil',.0014),('catchlight',.0021)]:
        o=bpy.data.objects['Eye '+side+' '+part]
        for v in o.data.vertices:
            a,b=uv(ex,ez,v.co);a*=.88;b*=.9;x,z=xyz(ex,ez,a,b)
            v.co=(x,front(sclera,x,z)-lift,z)
        o.data.update();o.shape_key_add(name='Basis')
        for name,da,db in [('GazeRight',.012,0),('GazeLeft',-.012,0),('GazeUp',0,.008),('GazeDown',0,-.008)]:
            key=o.shape_key_add(name=name)
            for v,dst in zip(o.data.vertices,key.data):
                a,b=uv(ex,ez,v.co);x,z=xyz(ex,ez,a+da,b+db)
                dst.co=(x,front(sclera,x,z)-lift,z)
        gaze_owners.append(o.data.shape_keys);owners.append(o.data.shape_keys)
    for part in ['sclera','iris','pupil','catchlight']:
        o=bpy.data.objects['Eye '+side+' '+part]
        if not o.data.shape_keys:o.shape_key_add(name='Basis');owners.append(o.data.shape_keys)
        key=o.shape_key_add(name='Recess')
        for v,dst in zip(o.data.vertices,key.data):dst.co=v.co+Vector((0,.040,0))
        recess_owners.append(o.data.shape_keys)
    # Upper/lower shutters follow the eyeball surface. Eight intermediate
    # shapes keep interpolation in front of the eye instead of cutting into it.
    for upper in [True,False]:
        cols,rows=48,14
        def lid_position(col,row,closure):
            a=.098*(-.998+1.996*col/cols)
            edge=.112*math.sqrt(max(0,1-(a/.098)**2))
            meeting=.012*(1-(a/.098)**2)
            border=edge if upper else -edge
            inner=border*(1-closure)+meeting*closure
            # A thin open rim lies on the eyeball edge; it is never a thick ring.
            r=row/rows;b=border*(1-r)+inner*r
            x,z=xyz(ex,ez,a,b)
            face_y=front(body,x,z)-.0005;eye_y=front(sclera,x,z)-.004
            y=face_y+(eye_y-face_y)*smooth(0,.20,r)*(1-smooth(.70,1.,closure))
            return (x,y,z)
        verts=[lid_position(c,r,.004) for r in range(rows+1) for c in range(cols+1)]
        faces=[]
        for r in range(rows):
            for c in range(cols):
                a=r*(cols+1)+c;face=(a,a+1,a+cols+2,a+cols+1)
                faces.append(face if upper else tuple(reversed(face)))
        o=mesh('Lid '+side+(' upper' if upper else ' lower'),verts,faces,lidmat)
        # Recalculate normals toward the viewing side for both lid surfaces.
        if o.data.polygons[len(faces)//2].normal.y>0:
            import bmesh
            bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
        o.shape_key_add(name='Basis')
        for step in range(1,9):
            key=o.shape_key_add(name='Close'+str(step))
            for i,dst in enumerate(key.data):dst.co=lid_position(i%(cols+1),i//(cols+1),step/8)
        lids.append((o.data.shape_keys,side,upper));owners.append(o.data.shape_keys)
    # A crease becomes visible only at full closure, on top of the closed lids.
    curve=bpy.data.curves.new('Closed lid crease '+side,'CURVE');curve.dimensions='3D';curve.bevel_depth=.002;curve.bevel_resolution=2;curve.use_fill_caps=True
    spl=curve.splines.new('POLY');spl.points.add(40)
    for i,p in enumerate(spl.points):
        a=-.094+.188*i/40;b=.012*(1-(a/.098)**2);x,z=xyz(ex,ez,a,b)
        p.co=(x,front(body,x,z)-.002,z,1);p.radius=.25+.75*math.sin(math.pi*i/40)**.5
    ob=bpy.data.objects.new('Closed crease '+side,curve);scene.collection.objects.link(ob)
    curve.materials.append(bpy.data.materials['Soft dark orange smile'])
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.convert(target='MESH');ob=bpy.context.object
    skin(ob)
    visible=[v.co.copy() for v in ob.data.vertices]
    for v in ob.data.vertices:v.co.y+=.10
    ob.shape_key_add(name='Basis');key=ob.shape_key_add(name='Visible')
    for dst,p in zip(key.data,visible):dst.co=p
    creases.append(ob.data.shape_keys);owners.append(ob.data.shape_keys)
# Closed-mouth smile: corners widen/lift while the centre stays relaxed.
mouth=bpy.data.objects['Small closed smile'];muzzle=bpy.data.objects['Lulu rounded muzzle']
mouth.shape_key_add(name='Basis');key=mouth.shape_key_add(name='Smile')
for v,dst in zip(mouth.data.vertices,key.data):
    a,b=uv(0,1.76,v.co);old_y=front(muzzle,v.co.x,v.co.z)
    x,z=xyz(0,1.76,a*1.38,b+.030*min(1.2,(a/.065)**2)+.004)
    dst.co=(x,front(muzzle,x,z)+(v.co.y-old_y),z)
owners.append(mouth.data.shape_keys)
key=mouth.shape_key_add(name='Doubt')
for v,dst in zip(mouth.data.vertices,key.data):
    a,b=uv(0,1.76,v.co);old_y=front(muzzle,v.co.x,v.co.z)
    x,z=xyz(0,1.76,a*.9,b-.014*min(1.2,(a/.065)**2)+.009*(a/.065))
    dst.co=(x,front(muzzle,x,z)+(v.co.y-old_y),z)
def curve(t,points):
    if t<=points[0][0]:return points[0][1]
    for (a,x),(b,y) in zip(points,points[1:]):
        if t<=b:
            u=(t-a)/(b-a);u=u*u*(3-2*u);return x+(y-x)*u
    return points[-1][1]
def pulse(t,center):
    d=(t-center)/(.09 if t<center else .15)
    return (.5+.5*math.cos(math.pi*d)) if abs(d)<1 else 0
def lid_weights(keys,c):
    q=max(0,min(1,c))*8
    for i in range(1,9):keys.key_blocks['Close'+str(i)].value=max(0,1-abs(q-i))
def stash(owner,name,action,end):
    track=owner.animation_data.nla_tracks.new();track.name=name;track.mute=True
    strip=track.strips.new(name,0,action);strip.frame_end=end;strip.extrapolation='NOTHING';owner.animation_data.action=None
clips={'Idle':6.,'Greeting':6.,'Smile':4.,'Curious':4.}
for name,duration in clips.items():
    end=round(duration*30)
    all_owners=[rig]+owners
    for owner in all_owners:
        owner.animation_data_create();owner.animation_data.action=bpy.data.actions.new(name+' '+owner.name)
    for f in range(end+1):
        t=f/30
        for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.scale=(1,1,1);p.location=(0,0,0)
        head=rig.pose.bones['Head'];chest=rig.pose.bones['Chest'];wave=rig.pose.bones['Wave']
        chest.scale.y=1+.004*(1-math.cos(2*math.pi*t/duration))
        smile=gx=gy=tilt=0.;blink=pulse(t,2.8) if name=='Idle' else 0.
        curious=0.
        if name=='Greeting':
            gx=curve(t,[(0,0),(.28,0),(.48,1),(.76,.65),(1.15,0),(6,0)])
            head.rotation_euler.y=math.radians(curve(t,[(0,0),(.5,0),(.92,7),(1.45,0),(6,0)]))
            head.rotation_euler.x=math.radians(curve(t,[(0,0),(.55,-1),(1.05,2.5),(1.6,-1),(2.25,0),(4.0,0),(4.5,1),(5.2,0),(6,0)]))
            tilt=curve(t,[(0,0),(1,0),(1.8,-3),(3.5,-2),(5.2,0),(6,0)])
            smile=curve(t,[(0,0),(.85,0),(1.65,1),(3.65,1),(5.25,0),(6,0)])
            chest.rotation_euler.x=math.radians(curve(t,[(0,0),(.95,0),(1.8,1.6),(3.2,1.2),(5.3,0),(6,0)]))
            wave.rotation_euler.z=math.radians(curve(t,[(0,0),(1.25,0),(1.6,-3),(2.05,8),(2.4,-6),(2.78,7),(3.12,-4),(3.46,4),(4.15,0),(6,0)]))
            blink=max(pulse(t,1.12),pulse(t,4.4))
        elif name=='Smile':
            smile=curve(t,[(0,0),(.35,0),(1.25,1),(2.65,1),(3.7,0),(4,0)]);tilt=-2*smile
        elif name=='Curious':
            curious=curve(t,[(0,0),(.35,0),(1.2,1),(2.6,1),(3.7,0),(4,0)]);tilt=6*curious;gx=-.65*curious;gy=.3*curious
        head.rotation_euler.z=math.radians(tilt)
        for keys in gaze_owners:
            for k,value in [('GazeRight',max(0,gx)),('GazeLeft',max(0,-gx)),('GazeUp',max(0,gy)),('GazeDown',max(0,-gy))]:keys.key_blocks[k].value=value
        for keys,side,upper in lids:
            emotion=(.25 if upper else .68)*smile
            if upper:emotion+=(.27 if side=='L' else .03)*curious
            lid_weights(keys,blink+(1-blink)*emotion)
        for keys in creases:keys.key_blocks['Visible'].value=curve(blink,[(0,0),(.75,0),(.9,1),(1,1)])
        for keys in recess_owners:keys.key_blocks['Recess'].value=smooth(.7,1.,blink)
        mouth.data.shape_keys.key_blocks['Smile'].value=smile
        mouth.data.shape_keys.key_blocks['Doubt'].value=curious
        for p in rig.pose.bones:
            for prop in ['rotation_euler','scale','location']:p.keyframe_insert(prop,frame=f)
        for owner in owners:
            for k in list(owner.key_blocks)[1:]:k.keyframe_insert('value',frame=f)
    for owner in all_owners:stash(owner,name,owner.animation_data.action,end)
for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.scale=(1,1,1);p.location=(0,0,0)
for owner in owners:
    for k in list(owner.key_blocks)[1:]:k.value=0
scene.frame_start=0;scene.frame_end=180;scene.frame_set(0)
rig['motion_scope']='Greeting performance study: independently authored gaze, surface lids, closed smile and offset body/hand timing; original fused hand remains limited.'
bpy.ops.wm.save_as_mainfile(filepath=str(root/'lulu-performance-v1.blend'))
bpy.ops.export_scene.gltf(filepath=str(root/'lulu-performance-v1.glb'),export_format='GLB',export_extras=True,export_animation_mode='NLA_TRACKS',export_animations=True,export_skins=True,export_morph=True)
(root/'performance-v1-spec.json').write_text(json.dumps({'clips':clips,'fps':30,'source':'lulu-motion-v1.blend','scope':rig['motion_scope']},indent=2),encoding='utf-8')
print('PERFORMANCE_EXPORTED')
