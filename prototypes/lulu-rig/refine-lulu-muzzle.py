"""Refine the approved source's muzzle volume and small closed smile.

Derived from Spencer0131's CC BY 4.0 Lulu. The original source and preceding
eye revision are kept intact. Shape and proportions follow reference-approved-v2.
"""
from pathlib import Path
import bpy,math,json,sys
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-eyes-v1.blend'))
body=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
mesh=body.data
with bpy.data.libraries.load(str(root/'source-normalized.blend'),link=False) as (src,dst):dst.meshes=list(src.meshes)
source=max(dst.meshes,key=lambda m:len(m.vertices))
tree=KDTree(len(source.vertices))
for v in source.vertices:tree.insert(v.co,v.index)
tree.balance()
with np.load(root/'surface-regions.npz') as masks:hand=masks['hand'].copy()
hand_ids=np.flatnonzero(hand>.5);hand_tree=KDTree(len(hand_ids))
for i in hand_ids:hand_tree.insert(source.vertices[int(i)].co,int(i))
hand_tree.balance()
def linear(h):
    s=[int(h[i:i+2],16)/255 for i in (1,3,5)]
    return np.array([x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in s])
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*t*(10-15*t+6*t*t)
yellow=linear('#FFD038');orange=linear('#FF971C')
paint=mesh.color_attributes['LuluPaint']
changed=0;max_shift=0
displacement=np.zeros(len(mesh.vertices))
for vert in mesh.vertices:
    x,y,z=vert.co
    u=.986*x+.167*(z-1.76);v=-.167*x+.986*(z-1.76)
    if abs(u)>1.1 or abs(v)>.90:continue
    _,_,hand_distance=hand_tree.find(vert.co)
    # Move the raised hand and its continuous attachment forward together.
    # The lower forearm remains in place; nearby cheek vertices are covered by
    # the new muzzle. This avoids carving a dimple into the orange volume.
    amount=.12*(1-smooth(0,.14,hand_distance))*smooth(1.10,1.50,z)
    displacement[vert.index]=amount
    # Remove the old painted patch: orange now belongs to a real closed volume.
    if y<-.16 and abs(v)<.60:paint.data[vert.index].color=(*yellow,1)
# Smooth the displacement field on the connected mesh, not the coordinates.
# This removes segmentation ridges while preserving the source surface detail.
edges=np.empty(len(mesh.edges)*2,dtype=np.int32);mesh.edges.foreach_get('vertices',edges);edges=edges.reshape(-1,2)
a,b=edges.T;degree=np.bincount(np.r_[a,b],minlength=len(mesh.vertices))
for _ in range(30):
    total=np.bincount(a,weights=displacement[b],minlength=len(mesh.vertices))+np.bincount(b,weights=displacement[a],minlength=len(mesh.vertices))
    displacement=.5*displacement+.5*total/np.maximum(degree,1)
positions=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',positions);positions=positions.reshape(-1,3)
positions[:,1]-=displacement
# Relax only the lower forearm attachment; fingers and facial details remain
# outside this mask. Smooth all three coordinates to avoid directional creases.
relax=np.array([smooth(.20,.40,x)*(1-smooth(.85,1.,x))*smooth(1.02,1.17,z)*(1-smooth(1.42,1.55,z))*(1-smooth(-.12,.12,y)) for x,y,z in positions])
for _ in range(16):
    average=np.column_stack([(np.bincount(a,weights=positions[b,k],minlength=len(mesh.vertices))+np.bincount(b,weights=positions[a,k],minlength=len(mesh.vertices)))/np.maximum(degree,1) for k in range(3)])
    positions+=(average-positions)*(.35*relax[:,None])
mesh.vertices.foreach_set('co',positions.ravel())
changed=int(np.count_nonzero(displacement>1e-6));max_shift=float(displacement.max())
mesh.update()
body['muzzle_changes']='Old orange face patch removed; raised hand advanced to contact a separate embedded rounded muzzle.'
# A closed, editable ellipsoid, deeply embedded in the source head. Its curved
# sides and underside define the silhouette and generate real contact shading.
X=Vector((.986,0,.167)).normalized();Z=Vector((-.167,0,.986)).normalized()
center=Vector((0,-.52,1.76));rx,ry,rz=.79,.42,.405
verts=[center+Z*rz];faces=[];rows=64;cols=128
for j in range(1,rows):
    theta=math.pi*j/rows
    for k in range(cols):
        phi=2*math.pi*k/cols
        verts.append(center+X*(rx*math.sin(theta)*math.cos(phi))+Z*(rz*math.cos(theta))+Vector((0,ry*math.sin(theta)*math.sin(phi),0)))
for k in range(cols):faces.append((0,1+(k+1)%cols,1+k))
for j in range(rows-2):
    for k in range(cols):
        a=1+j*cols+k;b=1+j*cols+(k+1)%cols;c=1+(j+1)*cols+(k+1)%cols;d=1+(j+1)*cols+k
        faces.append((a,b,c,d))
bottom=len(verts);verts.append(center-Z*rz)
for k in range(cols):faces.append((1+(rows-2)*cols+k,1+(rows-2)*cols+(k+1)%cols,bottom))
data=bpy.data.meshes.new('Rounded muzzle solid');data.from_pydata(verts,[],[tuple(reversed(f)) for f in faces]);data.update()
muzzle=bpy.data.objects.new('Lulu rounded muzzle',data);bpy.context.scene.collection.objects.link(muzzle)
for p in data.polygons:p.use_smooth=True
muzzle_mat=bpy.data.materials.new('Muzzle orange plush');muzzle_mat.use_nodes=True
nodes=muzzle_mat.node_tree.nodes;links=muzzle_mat.node_tree.links;bs=nodes['Principled BSDF']
bs.inputs['Base Color'].default_value=(*orange,1);bs.inputs['Roughness'].default_value=.82
bs.inputs['Specular IOR Level'].default_value=.20;bs.inputs['Sheen Weight'].default_value=.18
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=240;noise.inputs['Detail'].default_value=2
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.001
links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
data.materials.append(muzzle_mat)
muzzle['design_reference']='reference-approved-v2.png; rounded orange snout with a small closed smile'
old=bpy.data.objects.get('Small closed smile')
if old:bpy.data.objects.remove(old,do_unlink=True)
curve=bpy.data.curves.new('Reference proportion closed smile','CURVE')
curve.dimensions='3D';curve.bevel_depth=.007;curve.bevel_resolution=4;curve.use_fill_caps=True
sp=curve.splines.new('POLY');sp.points.add(48)
for i,p in enumerate(sp.points):
    t=-1+2*i/48;u=.065*t;v=-.135+.016*t*t
    x=.986*u-.167*v;z=1.76+.167*u+.986*v
    hit,pos,normal,face=muzzle.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
    assert hit,'Smile must attach to the muzzle'
    pos+=normal*.001
    p.co=(*pos,1);p.radius=.3+.7*min(1,(1-abs(t))/.12)
mouth=bpy.data.objects.new('Small closed smile',curve);bpy.context.scene.collection.objects.link(mouth)
mat=bpy.data.materials.new('Soft dark orange smile');mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*linear('#6B310C'),1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.82
curve.materials.append(mat)
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import check_geometry
health=check_geometry.run(names=[body.name,'Eye L sclera','Eye R sclera',muzzle.name],spec={'expect_embedded':[['Eye * sclera',body.name],[muzzle.name,body.name]]})
report={'reference':'windows/Meow.Windows/Assets/Lulu/reference-approved-v2.png','hand_and_cheek_vertices_changed':changed,'max_forward_change':max_shift,'muzzle_axes':[2*rx,2*ry,2*rz],'muzzle_front_y':center.y-ry,'smile_width':.13,'smile_rise':.016,'health':health}
(root/'muzzle-v4-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
assert not health['errors'],health['errors']
bpy.ops.wm.save_as_mainfile(filepath=str(root/'lulu-face-v4.blend'))
bpy.ops.export_scene.gltf(filepath=str(root/'lulu-face-v4.glb'),export_format='GLB',export_extras=True)
print('MUZZLE_REVISION',json.dumps({k:v for k,v in report.items() if k!='health'}))
