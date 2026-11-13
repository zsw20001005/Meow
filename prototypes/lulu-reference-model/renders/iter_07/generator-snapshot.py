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

# Proportions are measured from the approved front photograph.
def cheek_shape(v):
    v.x*=1-.10*(v.z/.73)
    return v
rounded('Head',(0,0,2.33),(.94,.58,.73),yellow,.93,cheek_shape)
rounded('Body',(0,.025,1.16),(.755,.445,.72),yellow,.94)
def trouser_shape(v):
    # Taper the hem while keeping the waist broad; a shallow crotch separates legs.
    v.x*=1+.13*(v.z/.30)
    if v.z<0:v.z+=.10*math.exp(-(v.x/.22)**2)*(-v.z/.30)**2
    return v
rounded('Shorts',(0,.025,.61),(.765,.46,.30),pants,.57,trouser_shape)
for side,sign in [('L',-1),('R',1)]:
    rounded('Leg.'+side,(sign*.36,.015,.33),(.19,.19,.27),yellow)
    rounded('Foot.'+side,(sign*.36,-.085,.15),(.24,.265,.15),yellow,.82)
    limb('Arm.'+side,[(sign*.57,.015,1.66,.06),(sign*.69,-.025,1.50,.16),(sign*.83,-.055,1.20,.145),(sign*.86,-.12,.99,.145),(sign*.86,-.135,.88,.105),(sign*.86,-.135,.835,.008)],yellow)
    rounded('Thumb.'+side,(sign*.765,-.225,.98),(.065,.065,.10),yellow)
    ear=rounded('Ear.'+side,(sign*.79,.005,2.82),(.16,.13,.26),yellow)
    rounded('InnerEar.'+side,(sign*.80,-.105,2.84),(.095,.033,.16),orange)
MUZZLE_POWER=.94
rounded('Muzzle',(0,-.505,1.96),(.865,.39,.44),orange,MUZZLE_POWER)

# Reuse Spencer0131's continuous sculpt, before the later separate muzzle edits.
# This derivative only repairs the embossed eye regions of the original STL.
source_path=ROOT.parent/'lulu-rig/review/sketchfab-lulu/lulu-eyes-v1.blend'
with bpy.data.libraries.load(str(source_path),link=False) as (available,loaded):
    loaded.objects=[n for n in available.objects if 'painted preview' in n]
assert len(loaded.objects)==1,'Expected one source Lulu sculpt'
source=loaded.objects[0];collection.objects.link(source)
bm=bmesh.new();bm.from_mesh(source.data)
upright=Matrix.Rotation(math.atan2(.108,.704),3,'Y')
for v in bm.verts:
    p=upright@(v.co-Vector((-.019,0,2.265)))
    v.co=(p.x*1.05,p.y*.95-.08,p.z*1.05+2.49)
def crop(point,normal,outer=True):
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,
                          plane_co=point,plane_no=normal,clear_outer=outer,clear_inner=not outer)
# Use the cheek without the fused raised hand, then mirror that source surface.
crop((0,0,0),(1,0,0))
crop((0,0,1.57),(0,0,1),False)
crop((0,0,2.92),(0,0,1))
# Old ear/tangerine junctions are trimmed under the current hair and ears.
crop((-.80,0,2.82),(-1,0,1))
bmesh.ops.mirror(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),matrix=Matrix.Identity(4),axis='X',merge_dist=.0001)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
caps=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces']
bmesh.ops.triangulate(bm,faces=caps)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
for name in ('Head','Muzzle'):bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
head_data=bpy.data.meshes.new('Reused Lulu head');bm.to_mesh(head_data);bm.free()
bpy.data.objects.remove(source,do_unlink=True)
skin_mat=mat('Continuous yellow orange face','#FFCC32',.75)
head=bpy.data.objects.new('Head',head_data);collection.objects.link(head);head.data.materials.clear();head.data.materials.append(skin_mat)
head['author']='Spencer0131';head['license']='CC BY 4.0'
head['source_url']='https://sketchfab.com/3d-models/a5747f74f0034470a2029a85f6e9c11d'
head['derivation']='Source sculpt: eye repair, upright alignment, left-cheek mirror, neck/top trimming; no separate muzzle.'
for p in head.data.polygons:p.use_smooth=True
def smoothstep(a,b,v):
    t=max(0,min(1,(v-a)/(b-a)));return t*t*(3-2*t)
tint=head.data.color_attributes.new(name='FaceTint',type='FLOAT_COLOR',domain='POINT')
base_color=rgb('#FFCC32');nose_color=rgb('#FF9C22')
for v,c in zip(head.data.vertices,tint.data):
    x,y,z=v.co;q=(x/.89)**2+((z-1.96)/.46)**2
    weight=(1-smoothstep(.78,1.12,q))*(1-smoothstep(-.48,-.26,y))
    c.color=(*(a*(1-weight)+b*weight for a,b in zip(base_color,nose_color)),1)
color_node=skin_mat.node_tree.nodes.new('ShaderNodeVertexColor');color_node.layer_name='FaceTint'
skin_shader=next(n for n in skin_mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
skin_mat.node_tree.links.new(color_node.outputs['Color'],skin_shader.inputs['Base Color'])
bpy.context.view_layer.update()
def face_front(x,z):
    hit,point,normal,index=head.ray_cast(Vector((x,-5,z)),Vector((0,1,0)))
    if not hit:raise RuntimeError(f'Face projection misses head at {x}, {z}')
    return point.y
for side,sign in [('L',-1),('R',1)]:
    x=sign*.313
    eye_y=face_front(x,2.49)+.008
    rounded('Eye.'+side,(x,eye_y,2.49),(.105,.033,.13),ivory)
    rounded('Iris.'+side,(x,eye_y-.027,2.484),(.075,.017,.100),iris)
    rounded('Pupil.'+side,(x,eye_y-.041,2.486),(.054,.009,.078),black)
    rounded('Highlight.'+side,(x-.021,eye_y-.050,2.527),(.017,.006,.022),shine)
    x=sign*.331
    tube('Frame.'+side,[(x+.217*math.cos(a),face_front(x+.217*math.cos(a),2.526+.217*math.sin(a))-.045,2.526+.217*math.sin(a)) for a in [math.tau*i/48 for i in range(48)]],.013,frame,True)
    tube('Temple.'+side,[(sign*.548,face_front(sign*.548,2.54)-.045,2.54),(sign*.68,face_front(sign*.68,2.55)-.02,2.55),(sign*.76,face_front(sign*.76,2.49)+.008,2.49)],.012,frame)
tube('Bridge',[(x,face_front(x,z)-.045,z) for x,z in [(-.114,2.54),(0,2.575),(.114,2.54)]],.012,frame)
def muzzle_front(x,z):
    return face_front(x,z)
tube('Smile',[(x,muzzle_front(x,z)-.003,z) for x,z in [(-.066,1.81),(-.036,1.786),(0,1.78),(.036,1.786),(.066,1.81)]],.010,smile)
waist_z=.85;waist_relative=(waist_z-.61)/.30
waist_factor=math.sin(math.acos(waist_relative**(1/.57)))**.57
tube('Waistband',[(.765*(1+.13*waist_relative)*waist_factor*signed(math.sin(a),.57),.025-.46*waist_factor*signed(math.cos(a),.57),waist_z) for a in [math.tau*i/96 for i in range(96)]],.013,pants,True)

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
focus=Vector((0,0,1.70))
for name,pos,power,size in [('Key',(-3,-4,6),320,4),('Fill',(4,-3,4),160,4),('Rim',(1,3,5),280,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Review');o=bpy.data.objects.new('Review',camera);scene.collection.objects.link(o);scene.camera=o;camera.type='ORTHO';camera.ortho_scale=4.02
for name,pos in [('front',(0,-10,1.70)),('side',(10,0,1.70)),('three-quarter',(7,-10,3.0))]:
    o.location=pos;o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
o.location=(0,-10,1.70);o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'lulu-proportions.blend'))
print('PROPORTION_MODEL',str(OUT),'CHECK',report['summary'])
