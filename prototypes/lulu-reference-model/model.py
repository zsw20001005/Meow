"""One editable source for the first AI-reference proportion study."""
import sys, math, json, argparse, shutil
from pathlib import Path
sys.path.insert(0, r'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import modelkit as mk
import bpy, bmesh
from mathutils import Vector, Matrix
import check_geometry

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--iteration',default='01')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=ROOT/'renders'/('iter_'+args.iteration);OUT.mkdir(parents=True,exist_ok=True)
shutil.copy2(__file__,OUT/'generator-snapshot.py')
shutil.copy2(ROOT/'spec.json',OUT/'spec-snapshot.json')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
collection=bpy.data.collections.new('Lulu_Blockout');bpy.context.scene.collection.children.link(collection)

def rgb(h):
    values=[int(h[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values)
def mat(name,h,rough=.7,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*rgb(h),1)
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*rgb(h),1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    return m
yellow=mat('Warm yellow','#FFCC32');orange=mat('Orange muzzle','#FF9C22');pants=mat('Tangerine shorts','#E97E28');brown=mat('Chestnut hair','#39271C')
frame=mat('Brown round frames','#6E411B',.32,.25);ivory=mat('Ivory eye','#FFF4DA',.25);iris=mat('Brown iris','#613613',.22);black=mat('Deep pupil','#171008',.18);shine=mat('Eye highlight','#FFFFFF',.13);smile=mat('Small closed smile','#773C0B')

def mesh(name,vertices,faces,material):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(data);bm.free()
    o=bpy.data.objects.new(name,data);collection.objects.link(o);o.data.materials.append(material)
    for p in data.polygons:p.use_smooth=True
    return o
def signed(x,p):return math.copysign(abs(x)**p,x)
def rounded(name,center,radii,material,power=1,warp=None):
    center=Vector(center);rx,ry,rz=radii;rows=40;cols=80
    vertices=[tuple(center+Vector((0,0,rz)))];faces=[]
    for j in range(1,rows):
        theta=math.pi*j/rows
        for i in range(cols):
            phi=math.tau*i/cols
            v=Vector((rx*signed(math.sin(theta),power)*signed(math.cos(phi),power),ry*signed(math.sin(theta),power)*signed(math.sin(phi),power),rz*signed(math.cos(theta),power)))
            if warp:v=warp(v)
            vertices.append(tuple(center+v))
    bottom=len(vertices);v=Vector((0,0,-rz));vertices.append(tuple(center+(warp(v) if warp else v)))
    for i in range(cols):faces.append((0,1+i,1+(i+1)%cols))
    for j in range(rows-2):
        for i in range(cols):
            a=1+j*cols+i;b=1+j*cols+(i+1)%cols;faces.append((a,b,b+cols,a+cols))
    for i in range(cols):faces.append((bottom,1+(rows-2)*cols+(i+1)%cols,1+(rows-2)*cols+i))
    return mesh(name,vertices,faces,material)
def tube(name,points,radius,material,cyclic=False):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=16;c.bevel_depth=radius;c.bevel_resolution=4;c.use_fill_caps=True
    s=c.splines.new('BEZIER');s.bezier_points.add(len(points)-1);s.use_cyclic_u=cyclic
    for b,p in zip(s.bezier_points,points):b.co=p;b.handle_left_type=b.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,c);collection.objects.link(o);c.materials.append(material);return o
def interpolate(values,t):
    f=t*(len(values)-1);i=min(int(f),len(values)-2);u=f-i
    a,b,c,d=[Vector(values[max(0,min(k,len(values)-1))]) for k in (i-1,i,i+1,i+2)]
    return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)
def limb(name,points,material):
    rows=36;cols=32;vertices=[];faces=[]
    for j in range(rows+1):
        t=j/rows;v=interpolate(points,t);pos=Vector(v[:3]);r=max(.004,v[3])
        direction=(interpolate(points,min(1,t+.002))-interpolate(points,max(0,t-.002)))
        tangent=Vector(direction[:3]).normalized();side=tangent.cross(Vector((0,1,0))).normalized();depth=tangent.cross(side).normalized()
        for i in range(cols):
            a=math.tau*i/cols;vertices.append(tuple(pos+r*(side*math.cos(a)+depth*.82*math.sin(a))))
        if j:
            for i in range(cols):a=(j-1)*cols+i;b=(j-1)*cols+(i+1)%cols;faces.append((a,b,b+cols,a+cols))
    vertices.extend([tuple(Vector(points[0][:3])),tuple(Vector(points[-1][:3]))]);top=len(vertices)-2;bottom=top+1
    for i in range(cols):faces.extend([(top,i,(i+1)%cols),(bottom,rows*cols+(i+1)%cols,rows*cols+i)])
    o=mesh(name,vertices,faces,material);return o

# Reuse the whole source sculpt, before the later separate-muzzle experiments.
source_path=ROOT.parent/'lulu-rig/review/sketchfab-lulu/lulu-eyes-v1.blend'
with bpy.data.libraries.load(str(source_path),link=False) as (available,loaded):
    loaded.objects=[n for n in available.objects if 'painted preview' in n or n.startswith('Eye ')]
optics=bpy.data.collections.new('Lulu Optical Details');bpy.context.scene.collection.children.link(optics)
for obj in loaded.objects:
    target=collection if 'painted preview' in obj.name or 'sclera' in obj.name else optics
    target.objects.link(obj)
head=next(o for o in loaded.objects if 'painted preview' in o.name);head.name='ReusedLulu'
head_pivot=Vector((-.019,0,2.265))
tilt=Matrix.Rotation(-math.atan2(.108,.704),3,'Y');upright=tilt.inverted()
preserved={tuple(v.co) for v in head.data.vertices if v.co.z<2.35}
bm=bmesh.new();bm.from_mesh(head.data)
fruit=[v for v in bm.verts if (upright@(v.co-head_pivot)).z>.35 and abs((upright@(v.co-head_pivot)).x)<.58]
bmesh.ops.delete(bm,geom=fruit,context='VERTS')
caps=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces']
bmesh.ops.triangulate(bm,faces=caps)
bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if v.co.z>2.35],dist=.00001)
# Remove paired opposite triangles left by tiny branches in the crown cut.
bm.verts.index_update();face_sets={}
for f in bm.faces:
    if all(v.co.z>2.35 for v in f.verts):
        face_sets.setdefault(tuple(sorted(v.index for v in f.verts)),[]).append(f)
duplicate_caps=[f for group in face_sets.values() if len(group)>1 for f in group]
if duplicate_caps:bmesh.ops.delete(bm,geom=duplicate_caps,context='FACES_ONLY')
wire=[e for e in bm.edges if not e.link_faces]
if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
loose=[v for v in bm.verts if not v.link_edges]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(head.data);bm.free();head.data.update()
assert preserved.issubset({tuple(v.co) for v in head.data.vertices}),'Source body must remain unchanged'
head['author']='Spencer0131';head['license']='CC BY 4.0'
head['source_url']='https://sketchfab.com/3d-models/a5747f74f0034470a2029a85f6e9c11d'
head['derivation']='Whole source sculpt and pose retained; eye-repair derivative; central tangerine removed under new bowl-cut; glasses added.'
for p in head.data.polygons:p.use_smooth=True
(OUT/'source-preservation.json').write_text(json.dumps({'source':str(source_path),'preserved_vertices_below_z_2_35':len(preserved),'unchanged':True,'author':'Spencer0131','license':'CC BY 4.0'},indent=2),encoding='utf-8')
bpy.context.view_layer.update()
def on_face(u,v,lift):
    p=head_pivot+tilt@Vector((u,0,v))
    hit,point,normal,index=head.ray_cast(Vector((p.x,-5,p.z)),Vector((0,1,0)))
    if not hit:raise RuntimeError(f'Face projection misses source at {u}, {v}')
    return (p.x,point.y-lift,p.z)
for side,sign in [('L',-1),('R',1)]:
    x=sign*.355
    tube('Frame.'+side,[on_face(x+.225*math.cos(a),.015+.225*math.sin(a),.046) for a in [math.tau*i/48 for i in range(48)]],.013,frame,True)
    tube('Temple.'+side,[on_face(sign*u,v,lift) for u,v,lift in [(.58,.025,.046),(.64,.02,.025),(.70,-.04,-.006)]],.012,frame)
tube('Bridge',[on_face(u,v,.046) for u,v in [(-.13,.03),(0,.065),(.13,.03)]],.012,frame)
tube('Smile',[on_face(u,-.61+.03*(u/.065)**2,.003) for u in [-.065,-.035,0,.035,.065]],.009,smile)

# Sculpted locks flow from the crown; grooves and rounded tips are geometry.
HAIR_LOCKS=16
def hair_surface(t,phi):
    front=max(0,math.cos(phi));phase=HAIR_LOCKS*phi
    lobe=(.5+.5*math.cos(phase))**.55
    end=2.02-.44*front+.12*lobe
    theta=t*end
    flow=phi+.13*(1-t)**2
    base=Vector((.74*math.sin(theta)*math.sin(flow),
                 .015-.57*math.sin(theta)*math.cos(flow),
                 2.83+.46*math.cos(theta)-.006*math.sin(phi*3)*t**4))
    normal=Vector((base.x/.74**2,(base.y-.015)/.57**2,(base.z-2.83)/.46**2)).normalized()
    relief=(.060*lobe-.028*(1-lobe)**3)*math.sin(theta)**1.3
    return base+normal*relief
rows=48;cols=256;verts=[(0,.015,3.29)];faces=[]
for j in range(1,rows+1):
    for i in range(cols):
        verts.append(tuple(hair_surface(j/rows,math.tau*i/cols)))
for i in range(cols):faces.append((0,1+i,1+(i+1)%cols))
for j in range(rows-1):
    for i in range(cols):a=1+j*cols+i;b=1+j*cols+(i+1)%cols;faces.append((a,b,b+cols,a+cols))
hair=mesh('Hair',verts,faces,brown)
solid=hair.modifiers.new('Fringe thickness','SOLIDIFY');solid.thickness=.025

# Fine, attached flow lines; one object avoids hundreds of scene objects.
strand_mat=mat('Hair flow lines','#493020',.85)
for material in (brown,strand_mat):
    shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    shader.inputs['Roughness'].default_value=.68;shader.inputs['Specular IOR Level'].default_value=.26
strands=bpy.data.curves.new('Hair flow','CURVE');strands.dimensions='3D';strands.bevel_depth=.0012;strands.bevel_resolution=1;strands.use_fill_caps=True
for i in range(HAIR_LOCKS*12):
    phi=math.tau*(i+.31)/(HAIR_LOCKS*12)
    spline=strands.splines.new('POLY');spline.points.add(27)
    for j,point in enumerate(spline.points):
        t=.08+.905*j/27
        v=hair_surface(t,phi)
        normal=Vector((v.x/.74**2,(v.y-.015)/.57**2,(v.z-2.83)/.46**2)).normalized()
        point.co=(*(v+normal*.0005),1);point.radius=.65+.35*math.sin(math.pi*j/27)
strand_object=bpy.data.objects.new('HairFlow',strands);collection.objects.link(strand_object);strands.materials.append(strand_mat)
tuft=tube('Cowlick',[(.02,.025,3.265),(.005,.025,3.36),(-.07,.025,3.43),(-.16,.025,3.45)],.069,brown)
for b,r in zip(tuft.data.splines[0].bezier_points,[.70,1,.85,.06]):b.radius=r

# Fit existing hair construction to the source head's tilt and eye-line anchor.
hair_transform=Matrix.Translation(head_pivot)@tilt.to_4x4()@Matrix.Translation((0,0,-2.49))
for obj in (hair,strand_object,tuft):obj.matrix_world=hair_transform

bpy.context.view_layer.update()
report=check_geometry.run(spec_path=str(ROOT/'spec.json'),out_path=str(OUT/'geometry.json'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=-.1
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(1,1,1,1);bg.inputs['Strength'].default_value=.35
nodes=scene.world.node_tree.nodes;links=scene.world.node_tree.links
visible_bg=nodes.new('ShaderNodeBackground');visible_bg.inputs['Color'].default_value=(1,1,1,1);visible_bg.inputs['Strength'].default_value=1.08
ray=nodes.new('ShaderNodeLightPath');mix=nodes.new('ShaderNodeMixShader')
links.new(ray.outputs['Is Camera Ray'],mix.inputs[0]);links.new(bg.outputs[0],mix.inputs[1]);links.new(visible_bg.outputs[0],mix.inputs[2])
links.new(mix.outputs[0],next(n for n in nodes if n.type=='OUTPUT_WORLD').inputs['Surface'])
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.007));floor=bpy.context.object;floor.name='_Studio floor';floor.data.materials.append(mat('Backdrop','#F7F5F1'))
focus=Vector((0,0,1.60))
for name,pos,power,size in [('Key',(-3,-4,6),320,4),('Fill',(4,-3,4),160,4),('Rim',(1,3,5),280,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Review');o=bpy.data.objects.new('Review',camera);scene.collection.objects.link(o);scene.camera=o;camera.type='ORTHO';camera.ortho_scale=3.80
for name,pos in [('front',(0,-10,1.60)),('side',(10,0,1.60)),('three-quarter',(7,-10,2.9))]:
    o.location=pos;o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
o.location=(0,-10,1.70);o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'lulu-proportions.blend'))
print('PROPORTION_MODEL',str(OUT),'CHECK',report['summary'])
