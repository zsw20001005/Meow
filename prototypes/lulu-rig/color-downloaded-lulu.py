"""Paint the approved downloaded STL without replacing or reshaping its mesh."""
from pathlib import Path
import bpy, math, json
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

root=Path(__file__).resolve().parent
out=root/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(out/'source-normalized.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
obj.name='Lulu — Spencer0131 — painted preview'
mesh=obj.data
def rgb(h):
    c=[int(h[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in c)
palette={k:rgb(v) for k,v in dict(skin='#FFD038',snout='#FF981B',shorts='#E97827',leaf='#53833A',stem='#7A5933',eye='#FFF4D7',pupil='#302217',shine='#FFFFFF',mouth='#884817').items()}
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def blend(a,b,w):return tuple(x*(1-w)+y*w for x,y in zip(a,b))
attr=mesh.color_attributes.new(name='LuluPaint',type='FLOAT_COLOR',domain='POINT')
with np.load(out/'surface-regions.npz') as packed:
    regions={name:packed[name] for name in packed.files}
# Fit a smooth outline to the measured snout border. A fixed surface distance
# controls the feather width, independent of the source mesh's vertex density.
positions=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',positions);positions=positions.reshape(-1,3)
edges=np.empty(len(mesh.edges)*2,dtype=np.int32);mesh.edges.foreach_get('vertices',edges);edges=edges.reshape(-1,2)
a,b=edges.T
cross=(regions['snout'][a]>.5)!=(regions['snout'][b]>.5)
border=(positions[a[cross]]+positions[b[cross]])*.5
border=border[(border[:,1]<-.25)&(border[:,2]>1.25)&(border[:,2]<2.25)]
bu=.986*border[:,0]+.167*(border[:,2]-1.79)
bv=-.167*border[:,0]+.986*(border[:,2]-1.79)
angles=np.arctan2(bv/.40,bu/.80);radii=np.hypot(bu/.80,bv/.40)
sample_a=[];sample_r=[]
for i in range(72):
    lo=-math.pi+2*math.pi*i/72;hi=lo+2*math.pi/72
    values=radii[(angles>=lo)&(angles<hi)]
    if len(values):sample_a.append((lo+hi)/2);sample_r.append(float(np.quantile(values,.85)))
def basis(theta):return [1]+[f(k*theta) for k in range(1,6) for f in (math.cos,math.sin)]
matrix=np.array([basis(t) for t in sample_a])
penalty=np.diag([0]+[.2*k*k for k in range(1,6) for _ in range(2)])
outline=np.linalg.solve(matrix.T@matrix+penalty,matrix.T@np.array(sample_r))
curve_tree=KDTree(1024)
for i in range(1024):
    theta=2*math.pi*i/1024;r=float(np.dot(outline,basis(theta)))
    curve_tree.insert((.8*r*math.cos(theta),.4*r*math.sin(theta),0),i)
curve_tree.balance()
for v in mesh.vertices:
    x,y,z=v.co
    c=palette['skin']
    # Original raised shorts and leg openings, with a slightly sloping waistband.
    trousers=float(regions['pants'][v.index])
    c=blend(c,palette['shorts'],trousers)
    # Snout follows the tilted head, with the raised hand kept yellow.
    u=x*.986+(z-1.86)*.167
    w=-x*.167+(z-1.86)*.986
    pu=.986*x+.167*(z-1.79);pv=-.167*x+.986*(z-1.79)
    theta=math.atan2(pv/.4,pu/.8);radius=math.hypot(pu/.8,pv/.4)
    boundary=float(np.dot(outline,basis(theta)))
    _,_,distance=curve_tree.find((pu,pv,0))
    signed=distance if radius>boundary else -distance
    orange=(1-smooth(-.012,.012,signed))*(1-smooth(-.30,-.16,y))*(1-float(regions['hand'][v.index]))
    muzzle=blend(rgb('#F39A20'),rgb('#FFA222'),smooth(-.36,-.76,y))
    c=blend(c,muzzle,orange)
    # Tangerine on the original head; stem and leaf are already sculpted in.
    c=blend(c,palette['snout'],float(regions['hat'][v.index]))
    if z>2.9:
        c=palette['stem'] if x<-.13 else palette['leaf']
    # Paint the existing embossed eyes rather than adding new eyeball geometry.
    for eye,(ex,ez) in zip(['eyeL','eyeR'],[(-.371,2.211),(.333,2.319)]):
        dx=x-ex;dz=z-ez
        du=dx*.986+dz*.167;dv=-dx*.167+dz*.986
        r=(du/.121)**2+(dv/.118)**2
        eye_weight=float(regions[eye][v.index])
        if eye_weight>0:
            c=blend(c,palette['eye'],eye_weight)
            pr=((du-.013)/.073)**2+((dv+.003)/.081)**2
            c=blend(c,palette['pupil'],(1-smooth(.94,1.06,pr))*eye_weight)
            hr=((du-.037)/.022)**2+((dv-.032)/.023)**2
            c=blend(c,palette['shine'],(1-smooth(.84,1.16,hr))*eye_weight)
    attr.data[v.index].color=(*c,1)
mat=bpy.data.materials.new('Lulu painted warm palette');mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.72
bs.inputs['Specular IOR Level'].default_value=.28
bs.inputs['Sheen Weight'].default_value=.12
noise=mat.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=280;noise.inputs['Detail'].default_value=2
bump=mat.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.0008
mat.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);mat.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
vc=mat.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='LuluPaint'
mat.node_tree.links.new(vc.outputs['Color'],bs.inputs['Base Color'])
mesh.materials.clear();mesh.materials.append(mat)
for p in mesh.polygons:p.use_smooth=True
obj['source_url']='https://sketchfab.com/3d-models/a5747f74f0034470a2029a85f6e9c11d'
obj['author']='Spencer0131';obj['license']='CC BY 4.0'
obj['changes']='Coordinate normalization and vertex color/material painting only; original geometry preserved.'
# A fine smile follows the existing surface; the source mesh stays unchanged.
curve=bpy.data.curves.new('Closed smile on surface','CURVE');curve.dimensions='3D';curve.resolution_u=16
curve.bevel_depth=.006;curve.bevel_resolution=3
sp=curve.splines.new('POLY');sp.points.add(40)
for i,point in enumerate(sp.points):
    u=-.108+.216*i/40;w=-.19+.042*(u/.108)**2
    x=u*.986-w*.167;z=1.86+u*.167+w*.986
    hit,pos,normal,face=obj.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
    pos+=normal*.003
    point.co=(*pos,1)
mouth_obj=bpy.data.objects.new('Small closed smile',curve);bpy.context.collection.objects.link(mouth_obj)
mouthmat=bpy.data.materials.new('Smile brown');mouthmat.use_nodes=True
mouthmat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*palette['mouth'],1)
mouthmat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
curve.materials.append(mouthmat)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'lulu-colored.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'lulu-colored.glb'),export_format='GLB',export_extras=True)
print('Painted',len(mesh.vertices),'vertices;',len(mesh.polygons),'triangles')
