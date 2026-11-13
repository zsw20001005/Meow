"""Replace the STL's embossed eyes with layered eyes based on the approved AI reference."""
from pathlib import Path
import bpy,math,json
import numpy as np
from mathutils import Vector

root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-colored.blend'))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
mesh=body.data
coords=np.empty(len(mesh.vertices)*3,dtype=np.float64);mesh.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
original=coords.copy()
with np.load(root/'surface-regions.npz') as regions:
    old_eye_paint=(regions['eyeL']>0)|(regions['eyeR']>0)
def linear(h):
    values=[int(h[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values)+(1,)
def material(name,h,rough=.35):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=linear(h)
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=linear(h);p.inputs['Roughness'].default_value=rough
    return m
white=material('Eye ivory sclera','#FFF4D7',.25)
iris=material('Eye warm brown iris','#613811',.18)
pupil=material('Eye deep pupil','#130D09',.13)
glint=material('Eye small catchlight','#FFFDF3',.18)
glint.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value=linear('#FFFDF3')
glint.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.4
for mat in [white,iris,pupil]:
    p=mat.node_tree.nodes['Principled BSDF'];p.inputs['Coat Weight'].default_value=.15;p.inputs['Coat Roughness'].default_value=.18;p.inputs['Specular IOR Level'].default_value=.22
collection=bpy.data.collections.new('Lulu rebuilt eyes');bpy.context.scene.collection.children.link(collection)
def make_mesh(name,verts,faces,mat):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    o=bpy.data.objects.new(name,data);collection.objects.link(o);data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    return o
headX=Vector((.986,0,.167));headZ=Vector((-.167,0,.986))
def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)
patches=[]
skin_patches=[]
def features(u,v):
    u=u/.2;v=v/.2
    return np.array([np.ones_like(u),u,v,u*u,u*v,v*v,u*u*u,u*u*v,u*v*v,v*v*v]).T
def height(fit,u,v):return float(features(float(u),float(v))@fit)
for side,(ex,ez) in zip(['L','R'],[(-.371,2.211),(.333,2.319)]):
    dx=coords[:,0]-ex;dz=coords[:,2]-ez
    u=dx*.986+dz*.167;v=-dx*.167+dz*.986
    rr=np.sqrt((u/.154)**2+(v/.164)**2)
    # Reconstruct skin under the old relief from its surrounding forehead.
    ring=(rr>1.45)&(rr<2.05)&(coords[:,1]<-.05)
    A=features(u[ring],v[ring])
    fit=np.linalg.lstsq(A,coords[ring,1],rcond=None)[0]
    affected=(rr<1.15)&(coords[:,1]<-.25)
    strength=1-smooth((rr-.80)/.35)
    skin_patches.append((ex,ez,fit))
    center=Vector((ex,float(fit[0])+.003,ez))
    # The eye conforms to the forehead instead of sitting on a separate tilted disk.
    X=headX.normalized();Z=headZ.normalized();N=Vector((0,-1,0))
    rx,depth,rz=.098,.023,.112
    def point(a,b,d):
        x=ex+X.x*a+Z.x*b;z=ez+X.z*a+Z.z*b
        return (x,height(fit,a,b)+.003-d,z)
    # A shallow, vertical eyeball is embedded into the skin rather than stuck on it.
    verts=[point(0,rz,0)];faces=[];rows=40;cols=64
    for j in range(1,rows):
        theta=math.pi*j/rows
        for k in range(cols):
            phi=2*math.pi*k/cols
            verts.append(point(rx*math.sin(theta)*math.cos(phi),rz*math.cos(theta),depth*math.sin(theta)*math.sin(phi)))
    for k in range(cols):faces.append((0,1+(k+1)%cols,1+k))
    for j in range(rows-2):
        for k in range(cols):
            a=1+j*cols+k;b=1+j*cols+(k+1)%cols;c=1+(j+1)*cols+(k+1)%cols;d=1+(j+1)*cols+k
            faces.append((a,b,c,d))
    bottom=len(verts);verts.append(point(0,-rz,0))
    for k in range(cols):faces.append((1+(rows-2)*cols+k,1+(rows-2)*cols+(k+1)%cols,bottom))
    eye=make_mesh('Eye '+side+' sclera',verts,faces,white)
    def cap(name,ax,az,mat,offset=(0,0),lift=.001):
        rings=18;segments=72
        def surface(a,b):return point(a,b,depth*math.sqrt(max(.01,1-(a/rx)**2-(b/rz)**2))+lift)
        verts=[surface(*offset)];faces=[]
        for j in range(1,rings+1):
            r=j/rings
            for k in range(segments):
                phi=2*math.pi*k/segments
                verts.append(surface(offset[0]+ax*r*math.cos(phi),offset[1]+az*r*math.sin(phi)))
        for k in range(segments):faces.append((0,1+k,1+(k+1)%segments))
        for j in range(rings-1):
            for k in range(segments):
                a=1+j*segments+k;b=1+j*segments+(k+1)%segments
                c=1+(j+1)*segments+(k+1)%segments;d=1+(j+1)*segments+k
                faces.append((a,b,c,d))
        obj=make_mesh('Eye '+side+' '+name,verts,faces,mat)
        # The cap basis faces toward -Y; reverse if its normal faces inward.
        if obj.data.polygons[0].normal.dot(N)<0:
            import bmesh
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
        return obj
    # Consistent pupil centres give a calm, engaged gaze rather than drifting eyes.
    gaze=(.003 if side=='L' else -.003,-.008)
    iris_obj=cap('iris',.085,.098,iris,gaze,.0007)
    colors=iris_obj.data.color_attributes.new(name='IrisBrown',type='FLOAT_COLOR',domain='POINT')
    for vert in iris_obj.data.vertices:
        relative=vert.co-center
        a=relative.dot(X)-gaze[0];b=relative.dot(Z)-gaze[1]
        r=math.sqrt((a/.085)**2+(b/.098)**2)
        angle=math.atan2(b/.098,a/.085)
        rim=1-float(smooth((r-.82)/.18))
        brightness=.48+.52*rim
        fiber=.94+.06*math.sin(angle*54+r*18)
        color=linear('#704016')
        colors.data[vert.index].color=tuple(c*brightness*fiber for c in color[:3])+(1,)
    inode=iris.node_tree.nodes.get('Iris color')
    if inode is None:
        inode=iris.node_tree.nodes.new('ShaderNodeVertexColor');inode.name='Iris color';inode.layer_name='IrisBrown'
        iris.node_tree.links.new(inode.outputs['Color'],iris.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    cap('pupil',.067,.078,pupil,gaze,.0014)
    cap('catchlight',.014,.016,glint,(-.025,.034),.0021)
    patches.append({'side':side,'center':list(center),'modified_skin_vertices':int(np.sum(affected))})
# Replace the embossed relief with clean rings; projecting its folded topology
# directly produces collapsed faces and wrinkles around the new eyeballs.
import bmesh
from mathutils.kdtree import KDTree
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
new_skin_verts=[]
color_layer=bm.verts.layers.float_color.get('LuluPaint')
old_colors=[tuple(mesh.color_attributes['LuluPaint'].data[i].color) if not old_eye_paint[i] else linear('#FFD038') for i in range(len(coords))]
for ex,ez,fit in skin_patches:
    def radius(p):
        dx=p.x-ex;dz=p.z-ez
        return math.sqrt(((dx*.986+dz*.167)/.154)**2+((-dx*.167+dz*.986)/.164)**2)
    # Match both position and tangent across a broad, smooth transition. The
    # old circular seam came from locking the boundary while changing its slope.
    for vert in bm.verts:
        if vert.co.y>=-.05:continue
        r=radius(vert.co)
        if r>=2.1:continue
        u=(vert.co.x-ex)*.986+(vert.co.z-ez)*.167
        v=-(vert.co.x-ex)*.167+(vert.co.z-ez)*.986
        t=max(0,min(1,(r-1.5)/.6));weight=1-(6*t**5-15*t**4+10*t**3)
        vert.co.y=vert.co.y*(1-weight)+height(fit,u,v)*weight
    candidate={v for v in bm.verts if v.co.y<-.05 and radius(v.co)<1.38}
    faces=[f for f in bm.faces if all(v in candidate for v in f.verts)]
    bmesh.ops.delete(bm,geom=faces,context='FACES')
    boundary=[e for e in bm.edges if e.is_boundary]
    adjacency={}
    for edge in boundary:
        a,b=edge.verts;adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
    assert adjacency and all(len(v)==2 for v in adjacency.values()),'Eye cut is not a single closed loop'
    first=next(iter(adjacency));ordered=[first];previous=None;current=first
    while True:
        nxt=next(v for v in adjacency[current] if v is not previous)
        if nxt is first:break
        ordered.append(nxt);previous,current=current,nxt
    assert len(ordered)==len(adjacency),'Multiple eye boundaries'
    source_ids=np.flatnonzero((np.abs(coords[:,0]-ex)<.25)&(np.abs(coords[:,2]-ez)<.25)&(coords[:,1]<-.25))
    tree=KDTree(len(source_ids))
    for index in source_ids:tree.insert((coords[index,0],coords[index,2],0),int(index))
    tree.balance()
    def paint(vert):
        # Interpolate the original surface color instead of copying the nearest
        # vertex. Nearest-neighbour sampling made the snout edge visibly jagged
        # where it crosses the rebuilt lower eye patches.
        from mathutils.geometry import barycentric_transform
        hit,pos,normal,face=body.ray_cast(Vector((vert.co.x,-3,vert.co.z)),Vector((0,1,0)))
        if hit:
            ids=list(mesh.polygons[face].vertices)
            assert len(ids)==3,'Expected triangulated source STL'
            color=barycentric_transform(pos,*(mesh.vertices[i].co for i in ids),*(Vector(old_colors[i][:3]) for i in ids))
            vert[color_layer]=(*color,1)
        else:
            _,index,_=tree.find((vert.co.x,vert.co.z,0));vert[color_layer]=old_colors[index]
    from mathutils.geometry import delaunay_2d_cdt
    def uv(p):return Vector(((p.x-ex)*.986+(p.z-ez)*.167,-(p.x-ex)*.167+(p.z-ez)*.986))
    border=[uv(v.co) for v in ordered]
    area=sum(border[i].x*border[(i+1)%len(border)].y-border[(i+1)%len(border)].x*border[i].y for i in range(len(border)))
    if area<0:ordered.reverse();border.reverse()
    count=len(border);points=list(border)
    for u in np.arange(-.20,.201,.008):
        for v in np.arange(-.215,.216,.008):
            if (u/.154)**2+(v/.164)**2<1.26**2:points.append(Vector((u,v)))
    verts2,edges2,faces2,origin,_,_=delaunay_2d_cdt(points,[],[list(range(count))],1,1e-8)
    boundary_uv=np.array(border)
    built=[]
    used={i for face in faces2 for i in face}
    for index,(p,orig) in enumerate(zip(verts2,origin)):
        if index not in used:
            built.append(None);continue
        original_border=[i for i in orig if i<count]
        if original_border:
            assert len(original_border)==1,'Projected border merged'
            built.append(ordered[original_border[0]]);continue
        u,v=p
        y=height(fit,u,v)
        vert=bm.verts.new((ex+u*.986-v*.167,y,ez+u*.167+v*.986));paint(vert);built.append(vert);new_skin_verts.append(vert)
    for face in faces2:bm.faces.new(tuple(built[i] for i in face))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
for poly in mesh.polygons:poly.use_smooth=True
body['eye_changes']='Original embossed eye relief blended into surrounding skin; separate oval sclera, brown iris, pupil and catchlight.'
body['changes']='Coordinate normalization, vertex colors, local eye-region replacement and separate eye components. The body outside the eye patches is preserved.'
(root/'eyes-v1-report.json').write_text(json.dumps({'source_vertices':len(coords),'rebuilt_body_vertices':len(mesh.vertices),'eyes':patches,'reference':'windows/Meow.Windows/Assets/Lulu/reference-approved-v2.png'},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(root/'lulu-eyes-v1.blend'))
bpy.ops.export_scene.gltf(filepath=str(root/'lulu-eyes-v1.glb'),export_format='GLB',export_extras=True)
print('EYES_REBUILT',json.dumps(patches))
