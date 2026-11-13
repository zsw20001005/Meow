"""Author an editable, remeshed Lulu base from the approved front reference.

This is real geometry, not an image pasted onto the old avatar. Coordinates in
the helpers use the existing Y-up character convention; Blender receives Z-up.
"""
import argparse
import bisect
import math
import random
import sys
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
rng=random.Random(21873)
def xyz(p): return (p[0],-p[2],p[1])
def linear(c): return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
def color(hex): return tuple(linear(int(hex[i:i+2],16)/255) for i in (1,3,5))+(1,)
def material(name,hex,roughness=.8,plush=False):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=color(hex);p.inputs['Roughness'].default_value=roughness
    if plush:
        p.inputs['Sheen Weight'].default_value=.45;p.inputs['Sheen Roughness'].default_value=.8
        p.inputs['Subsurface Weight'].default_value=.025
        tex=m.node_tree.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=185;tex.inputs['Detail'].default_value=2.5
        bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.24;bump.inputs['Distance'].default_value=.006
        m.node_tree.links.new(tex.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m
yellow=material('Golden plush','#ffbf32',plush=True);orange=material('Warm orange muzzle','#f59a19',plush=True)
pants=material('Orange cotton shorts','#e87924',plush=True);seam=material('Soft orange stitching','#d66d1e',.95)
hair=material('Chestnut velvet hair','#392417',.78,True);hair_lights=[material('Hair fiber '+str(i),h,.76) for i,h in enumerate(['#3d281b','#432c1c','#352115','#4a3120'])]
frame=material('Warm brown round frames','#74451e',.4);white=material('Warm ivory sclera','#fff3cc',.35)
iris=material('Deep brown iris','#542b0c',.2);pupil=material('Dark pupil','#170e06',.16);mouth=material('Small gentle smile','#703a12',.8)
skin=[];shorts=[]
def mesh(name,verts,faces,mat):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update();obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    if mat:obj.data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    return obj
def signed(v,p):return math.copysign(abs(v)**p,v)
def shape(name,pos,scale,mat,group=None,power=1):
    vertices=[];faces=[];u_count=64;v_count=40
    for j in range(v_count+1):
        theta=math.pi*j/v_count
        for i in range(u_count+1):
            phi=math.tau*i/u_count
            p=(scale[0]*signed(math.sin(theta),power)*signed(math.cos(phi),power),scale[1]*signed(math.cos(theta),power),scale[2]*signed(math.sin(theta),power)*signed(math.sin(phi),power))
            vertices.append(xyz(tuple(pos[k]+p[k] for k in range(3))))
            if j<v_count and i<u_count:
                a=j*(u_count+1)+i;faces.append((a,a+1,a+u_count+2,a+u_count+1))
    obj=mesh(name,vertices,faces,mat)
    if group is not None:group.append(obj)
    return obj
def curve(name,points,radius,mat):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=12;data.bevel_depth=radius;data.bevel_resolution=3;data.use_fill_caps=True
    s=data.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
    for b,p in zip(s.bezier_points,points):b.co=xyz(p);b.handle_left_type=b.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.data.materials.append(mat);return obj
def merge_smooth(objects,name,voxel):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=bpy.context.object;obj.name=name
    # Voxel union removes the visible primitive seams at shoulders, hands, ears and toes.
    remesh=obj.modifiers.new('Unified sculpt surface','REMESH');remesh.mode='VOXEL';remesh.voxel_size=voxel;remesh.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=obj.modifiers.new('Soft plush transitions','SMOOTH');smooth.factor=1.0;smooth.iterations=4;bpy.ops.object.modifier_apply(modifier=smooth.name)
    decimate=obj.modifiers.new('Even review mesh','DECIMATE');decimate.ratio=.52;bpy.ops.object.modifier_apply(modifier=decimate.name)
    for p in obj.data.polygons:p.use_smooth=True
    return obj

shape('Broad soft head',(0,2.33,0),(.925,.745,.61),yellow,skin,power=.96)
shape('Round belly',(0,1.23,0),(.715,.63,.455),yellow,skin)
for s in [-1,1]:
    shape('Small ear',(s*.80,2.82,-.025),(.16,.23,.13),yellow,skin)
    shape('Inner ear',(s*.815,2.84,.082),(.091,.145,.039),material('Ear warmth '+str(s),'#f4ac28',.9,True))
    # Overlapping smooth sculpt volumes are remeshed into one continuous limb.
    for x,y,z,rx,ry,rz in [(.50,1.69,0,.19,.25,.17),(.65,1.48,.015,.174,.26,.168),(.755,1.24,.055,.15,.245,.15),(.775,1.025,.10,.145,.17,.145),(.675,1.02,.16,.068,.085,.065)]:
        shape('Arm and soft paw',(s*x,y,z),(rx,ry,rz),yellow,skin)
    shape('Short leg',(s*.31,.37,.005),(.183,.255,.19),yellow,skin)
    shape('Soft single foot',(s*.31,.135,.105),(.235,.135,.255),yellow,skin,power=.88)
    shape('Short trouser leg',(s*.32,.49,.005),(.33,.18,.36),pants,shorts,power=.85)
shape('Shorts seat',(0,.705,-.015),(.705,.33,.445),pants,shorts,power=.95)
body=merge_smooth(skin,'Lulu continuous plush body',.012)
trousers=merge_smooth(shorts,'Separate rounded shorts',.010)
muzzle=shape('Broad rounded orange muzzle',(0,2.105,.555),(.862,.435,.373),orange,power=.83)
for s in [-1,1]:
    for offset in [-.075,.075]:
        x=s*.31+offset
        curve('Subtle toe stitch',[(x,.052,.324),(x,.095,.345),(x,.13,.349)],.0028,material('Toe shade '+str(s)+str(offset),'#dfa429',1))
waist=[]
for i in range(65):
    t=math.tau*i/64;front=max(0,math.cos(t));waist.append((.674*math.sin(t),.995-.10*front**2,.435*math.cos(t)))
curve('Curved waistband',waist,.020,seam)
curve('Shorts center seam',[(0,.48,.42),(0,.62,.441),(0,.78,.425),(0,.88,.388)],.0028,seam)

# Eyes lie close to the head instead of standing out as spherical eyeballs.
for s in [-1,1]:
    x=s*.315
    shape('Inset ivory eye',(x,2.575,.55),(.106,.137,.036),white)
    shape('Brown iris',(x,2.567,.58),(.077,.106,.021),iris)
    shape('Pupil',(x,2.569,.598),(.050,.079,.009),pupil)
    shape('Eye catchlight',(x-.024,2.615,.608),(.019,.025,.006),white)
    ring=[(x+.228*math.cos(t),2.61+.226*math.sin(t),.612+.012*math.cos(t)**2) for t in [math.tau*i/64 for i in range(65)]]
    curve('Independent round glasses',ring,.0125,frame)
    curve('Glasses temple',[(s*.543,2.62,.614),(s*.67,2.63,.49),(s*.79,2.56,.22)],.012,frame)
curve('Glasses bridge',[(-.087,2.625,.625),(0,2.66,.65),(.087,2.625,.625)],.011,frame)
curve('Small smile',[(-.060,1.979,.911),(0,1.957,.918),(.060,1.979,.911)],.010,mouth)

# A soft scalloped fringe plus many actual curved fibers, not painted helmet grooves.
def hair_point(phi,t,offset=0):
    front=max(0,math.cos(phi));end=1.66-.25*front+.018*math.cos(phi*23+.35)
    theta=t*end;flow=phi+.045*math.sin(t*math.pi)*math.sin(phi)
    ridge=1+.012*math.cos(phi*23)*math.sin(theta)**1.3
    return Vector((.755*math.sin(theta)*math.sin(flow)*ridge,2.62+.69*math.cos(theta),.605*math.sin(theta)*math.cos(flow)*ridge-.02))+Vector((math.sin(theta)*math.sin(flow),math.cos(theta),math.sin(theta)*math.cos(flow)))*offset
verts=[];faces=[];segments=192;rings=48
for j in range(rings+1):
    for i in range(segments+1):
        verts.append(xyz(hair_point(i/segments*math.tau,j/rings)))
        if j<rings and i<segments:
            k=j*(segments+1)+i;faces.append((k,k+segments+1,k+segments+2,k+1))
cap=mesh('Soft bowl-cut cap',verts,faces,hair)
solid=cap.modifiers.new('Fringe thickness','SOLIDIFY');solid.thickness=.025
fibers=[];fiber_faces=[];fiber_mats=[]
for n in range(2000):
    phi=rng.random()*math.tau;begin=.07+rng.random()*.2;end=.96+rng.random()*.04
    base=len(fibers);steps=18
    for j in range(steps+1):
        t=begin+(end-begin)*j/steps;point=hair_point(phi,t,.0015)
        normal=Vector((point.x/.755,(point.y-2.62)/.69,(point.z+.02)/.605)).normalized()
        tangent=Vector((math.cos(phi),0,-math.sin(phi)));side=normal.cross(tangent).normalized()
        radius=.0009*(.5+.5*math.sin(math.pi*j/steps)**.3)
        for k in range(3):
            p=point+radius*(tangent*math.cos(k*math.tau/3)+normal*math.sin(k*math.tau/3));fibers.append(xyz(p))
        if j<steps:
            for k in range(3):a=base+j*3+k;fiber_faces.append((a,base+j*3+(k+1)%3,base+(j+1)*3+(k+1)%3,base+(j+1)*3+k));fiber_mats.append(n%4)
strand_mesh=mesh('Individual curved chestnut fibers',fibers,fiber_faces,None)
for m in hair_lights:strand_mesh.data.materials.append(m)
for p,mi in zip(strand_mesh.data.polygons,fiber_mats):p.material_index=mi
tuft=curve('Soft tapered cowlick',[(0,3.265,-.035),(-.01,3.38,-.01),(-.10,3.48,.005),(-.16,3.50,.015)],.065,hair)
for b,r in zip(tuft.data.splines[0].bezier_points,[.6,1,.55,.035]):b.radius=r

def plush_fibers(obj,count,mat,name):
    obj.data.calc_loop_triangles();triangles=obj.data.loop_triangles;weights=[];total=0
    for tri in triangles:total+=tri.area;weights.append(total)
    vertices=[];faces=[];normals=[]
    for _ in range(count):
        tri=triangles[bisect.bisect_left(weights,rng.random()*total)];a,b,c=[obj.data.vertices[i] for i in tri.vertices]
        u=math.sqrt(rng.random());v=rng.random();w=(1-u,u*(1-v),u*v)
        p=a.co*w[0]+b.co*w[1]+c.co*w[2];normal=(a.normal*w[0]+b.normal*w[1]+c.normal*w[2]).normalized()
        tangent=normal.cross(Vector((.1,.3,1))).normalized();theta=rng.random()*math.tau;tangent=tangent*math.cos(theta)+normal.cross(tangent)*math.sin(theta)
        width=.00065;length=.004+rng.random()*.004;i=len(vertices)
        vertices.extend([p-tangent*width,p+tangent*width,p+normal*length+tangent*.001]);faces.append((i,i+1,i+2));normals.extend([normal]*3)
    fibers=mesh(name,vertices,faces,mat);fibers.data.normals_split_custom_set_from_vertices(normals)
plush_fibers(body,48000,yellow,'Golden micro pile')
plush_fibers(muzzle,26000,orange,'Muzzle micro pile')
plush_fibers(trousers,15000,pants,'Shorts soft pile')

# Save a model-only editable source and a real GLB for viewport inspection.
for obj in list(bpy.context.scene.objects):
    if obj.type=='CURVE':
        bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.convert(target='MESH');bpy.context.object.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'lulu-sculpt-v2.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'lulu-sculpt-v2.glb'),export_format='GLB',export_apply=True,export_animations=False,export_materials='EXPORT')
print('MODEL_READY',out/'lulu-sculpt-v2.glb')
