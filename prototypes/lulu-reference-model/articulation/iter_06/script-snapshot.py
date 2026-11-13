"""Articulation study of the retained source sculpt; never writes its master."""
import bpy,bmesh,math,json,sys,argparse,shutil
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.kdtree import KDTree
from mathutils.geometry import delaunay_2d_cdt,barycentric_transform
sys.path.insert(0,r'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--iteration',default='01');parser.add_argument('--inspect',action='store_true');parser.add_argument('--animate',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
OUT=ROOT/'articulation'/('iter_'+args.iteration);OUT.mkdir(parents=True,exist_ok=True)
shutil.copy2(__file__,OUT/'script-snapshot.py')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'renders/iter_10/lulu-proportions.blend'),use_scripts=False)
body=bpy.data.objects['ReusedLulu'];source_mesh=body.data.copy()
archive=ROOT.parent/'lulu-rig/review/sketchfab-lulu'
with bpy.data.libraries.load(str(archive/'source-normalized.blend'),link=False) as (src,dst):dst.meshes=list(src.meshes)
original=max(dst.meshes,key=lambda m:len(m.vertices))
with np.load(archive/'surface-regions.npz') as masks:hand_mask=masks['hand'].copy()
tree=KDTree(len(original.vertices))
for v in original.vertices:tree.insert(v.co,v.index)
tree.balance()
body_cut={v.index for v in source_mesh.vertices if hand_mask[tree.find(v.co)[1]]}
ARM_CHAIN=[Vector(p) for p in [(.63,.04,1.25),(.78,-.24,1.23),(.64,-.60,1.50),(.55,-.74,1.64)]]
def chain_distance(p):
    distances=[]
    for (a,b),radius in zip(zip(ARM_CHAIN,ARM_CHAIN[1:]),[.175,.187,.245]):
        d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));distances.append((p-a-d*t).length/radius)
    return min(distances)
selected={i for i in body_cut if chain_distance(source_mesh.vertices[i].co)<1 and source_mesh.vertices[i].co.z>1.115}
bm=bmesh.new();bm.from_mesh(source_mesh);bm.verts.ensure_lookup_table()
boundary=[e for e in bm.edges if (e.verts[0].index in selected)!=(e.verts[1].index in selected)]
points=[(e.verts[0].co+e.verts[1].co)*.5 for e in boundary]
report={'arm_vertices':len(selected),'crossing_edges':len(boundary),'boundary_min':[min(p[k] for p in points) for k in range(3)],'boundary_max':[max(p[k] for p in points) for k in range(3)]}
(OUT/'segmentation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bm.free()
if args.inspect:
    colors=body.data.color_attributes['LuluPaint']
    for i in selected:colors.data[i].color=(.05,.25,.9,1)
    sc=bpy.context.scene;sc.render.resolution_x=sc.render.resolution_y=720;sc.cycles.samples=24
    focus=Vector((.15,-.1,1.65));cam=sc.camera
    for name,pos in [('front',(0,-10,1.65)),('side',(10,-3,2.0))]:
        cam.location=pos;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('SEGMENTATION',report);sys.exit(0)

def clean_mesh(bm):
    wire=[e for e in bm.edges if not e.link_faces]
    if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
    loose=[v for v in bm.verts if not v.link_edges]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    unseen=set(bm.verts);parts=[]
    while unseen:
        seed=unseen.pop();component={seed};todo=[seed]
        while todo:
            for e in todo.pop().link_edges:
                for v in e.verts:
                    if v in unseen:unseen.remove(v);component.add(v);todo.append(v)
        parts.append(component)
    keep=max(parts,key=len)
    if len(parts)>1:bmesh.ops.delete(bm,geom=[v for p in parts if p is not keep for v in p],context='VERTS')

reference=bpy.data.objects.new('_Source reference',source_mesh);bpy.context.scene.collection.objects.link(reference);reference.hide_render=True
reference.hide_set(True);bpy.context.view_layer.update()
pivot=Vector((-.019,0,2.265));upright=Matrix.Rotation(math.atan2(.108,.704),3,'Y');tilt=upright.inverted()
def counterpart(p):
    q=upright@(p-pivot);q.x=-abs(q.x);q=pivot+tilt@q
    t=max(0,min(1,(p.z-1.25)/.40));t=t*t*(3-2*t)
    return Vector((-abs(p.x),p.y,p.z)).lerp(q,t)
def mirror_surface(p):
    # The opposite cheek supplies the missing volume behind the attached hand.
    q=counterpart(p)
    hit,location,normal,face=reference.ray_cast(Vector((q.x,-4,q.z)),Vector((0,1,0)))
    return location.y if hit else p.y+.12

def mirror_color(p):
    q=counterpart(p)
    hit,location,normal,face=reference.ray_cast(Vector((q.x,-4,q.z)),Vector((0,1,0)))
    if hit:
        ids=list(source_mesh.polygons[face].vertices)[:3]
        c=barycentric_transform(location,*(source_mesh.vertices[i].co for i in ids),*(Vector(source_mesh.color_attributes['LuluPaint'].data[i].color[:3]) for i in ids))
        return (*c,1)
    return (1,.63,.04,1)

def extract(name,keep,repair_body):
    bm=bmesh.new();bm.from_mesh(source_mesh);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS');clean_mesh(bm)
    border={e for e in bm.edges if e.is_boundary};loops=[]
    while border:
        edge=border.pop();start,current=edge.verts;loop=[start,current]
        while current is not start:
            choices=[e for e in current.link_edges if e in border]
            if not choices:break
            edge=choices[0];border.remove(edge);current=edge.other_vert(current)
            if current is not start:loop.append(current)
        if current is not start:raise RuntimeError('Cut boundary is not a closed loop')
        loops.append(loop)
    layer=bm.verts.layers.float_color.get('LuluPaint')
    if repair_body:
        # Blend the old boundary into the contralateral surface over nearby skin.
        border_vertices={v for loop in loops for v in loop};weights={v:1.0 for v in border_vertices};frontier=set(border_vertices)
        for step in range(1,15):
            following=set()
            for v in frontier:
                for e in v.link_edges:
                    other=e.other_vert(v)
                    if other not in weights:weights[other]=(1-step/15)**2;following.add(other)
            frontier=following
        for v,w in weights.items():
            v.co.y=(1-w)*v.co.y+w*mirror_surface(v.co)
            if layer:v[layer]=Vector(v[layer]).lerp(Vector(mirror_color(v.co)),w)
    for loop in loops:
        if repair_body:
            border_uv=[Vector((v.co.x,v.co.z)) for v in loop]
            count=len(loop);points=list(border_uv)
            lo=[min(p[k] for p in points) for k in range(2)];hi=[max(p[k] for p in points) for k in range(2)]
            for x in np.arange(lo[0]+.006,hi[0],.012):
                for z in np.arange(lo[1]+.006,hi[1],.012):points.append(Vector((x,z)))
            verts2,_,faces2,origin,_,_=delaunay_2d_cdt(points,[],[list(range(count))],1,1e-7)
            built=[];used={i for f in faces2 for i in f}
            for index,(p,orig) in enumerate(zip(verts2,origin)):
                if index not in used:built.append(None);continue
                ids=[i for i in orig if i<count]
                if ids:built.append(loop[ids[0]]);continue
                q=Vector((p.x,-.3,p.y));q.y=mirror_surface(q);v=bm.verts.new(q)
                if layer:v[layer]=mirror_color(q)
                built.append(v)
            for face in faces2:
                vertices=tuple(built[i] for i in face)
                if len(set(vertices))==len(vertices):
                    try:bm.faces.new(vertices)
                    except ValueError:pass  # A tiny existing boundary triangle may survive the cut.
            continue
        center=sum((v.co for v in loop),Vector())/len(loop)
        previous=loop
        # Nested rings keep triangulation away from one giant stretched fan.
        for ring in range(1,13):
            t=ring/13;inner=[]
            for v in loop:
                p=v.co.lerp(center,t)
                if repair_body:
                    blend=min(1,t*3);blend=blend*blend*(3-2*blend)
                    p.y=p.y*(1-blend)+mirror_surface(p)*blend
                nv=bm.verts.new(p)
                if layer:
                    if repair_body:
                        # Sample source color at the corresponding opposite surface.
                        q=upright@(p-pivot);q.x=-abs(q.x);q=pivot+tilt@q
                        _,idx,_=color_tree.find(q)
                        nv[layer]=source_mesh.color_attributes['LuluPaint'].data[idx].color
                    else:nv[layer]=v[layer]
                inner.append(nv)
            for i in range(len(loop)):
                j=(i+1)%len(loop);bm.faces.new((previous[i],previous[j],inner[j],inner[i]))
            previous=inner
        if repair_body:center.y=mirror_surface(center)
        cv=bm.verts.new(center)
        if layer:cv[layer]=previous[0][layer]
        for i in range(len(loop)):bm.faces.new((previous[i],previous[(i+1)%len(loop)],cv))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    data=bpy.data.meshes.new(name);bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);bpy.data.collections['Lulu_Blockout'].objects.link(obj)
    for material in source_mesh.materials:data.materials.append(material)
    for p in data.polygons:p.use_smooth=True
    print('EXTRACT',name,len(data.vertices),'loops',[len(loop) for loop in loops])
    return obj
color_tree=KDTree(len(source_mesh.vertices))
for v in source_mesh.vertices:color_tree.insert(v.co,v.index)
color_tree.balance()
torso=extract('Lulu.Body',set(range(len(source_mesh.vertices)))-body_cut,True)
arm=extract('Lulu.Arm.L',selected,False)
bpy.data.objects.remove(body,do_unlink=True)
def ease(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def repair_weight(p):
    return ease(.02,.30,p.x)*(1-ease(1.03,1.18,p.x))*ease(.72,.98,p.z)*(1-ease(1.84,2.10,p.z))*(1-ease(-.03,.22,p.y))
# Broaden the repair beyond the old fused seam so it cannot retain a narrow lip.
for v in torso.data.vertices:
    w=repair_weight(v.co)
    if w>0:v.co.y=v.co.y*(1-w)+mirror_surface(v.co)*w
torso.data.update()
bpy.ops.object.select_all(action='DESELECT');torso.select_set(True);bpy.context.view_layer.objects.active=torso
remesh=torso.modifiers.new('Repair detached contact surfaces','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.009;remesh.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth=torso.modifiers.new('Relax repaired skin','SMOOTH');smooth.factor=.6;smooth.iterations=10
bpy.ops.object.modifier_apply(modifier=smooth.name)
attr=torso.data.color_attributes.get('LuluPaint')
if attr:torso.data.color_attributes.remove(attr)
attr=torso.data.color_attributes.new(name='LuluPaint',type='FLOAT_COLOR',domain='POINT')
for v,c in zip(torso.data.vertices,attr.data):
    _,idx,_=color_tree.find(v.co);original_color=Vector(source_mesh.color_attributes['LuluPaint'].data[idx].color)
    c.color=original_color.lerp(Vector(mirror_color(v.co)),repair_weight(v.co))
report=check_geometry.run(names=[torso.name,arm.name],max_verts=400000,out_path=str(OUT/'geometry.json'))
# Exploded review only; the saved model and measurements use the assembled pose.
arm.location.x=.46
sc=bpy.context.scene;sc.render.resolution_x=sc.render.resolution_y=720;sc.cycles.samples=24
focus=Vector((.12,0,1.6));cam=sc.camera;cam.data.ortho_scale=3.85
for name,pos in [('separated-front',(0,-10,1.6)),('separated-side',(8,-6,2.4))]:
    cam.location=pos;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
arm.location.x=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'lulu-articulation.blend'))
