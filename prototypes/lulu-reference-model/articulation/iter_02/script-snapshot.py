"""Articulation study of the retained source sculpt; never writes its master."""
import bpy,bmesh,math,json,sys,argparse,shutil
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.kdtree import KDTree
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
selected={v.index for v in source_mesh.vertices if hand_mask[tree.find(v.co)[1]]}
ARM_CHAIN=[Vector(p) for p in [(.63,.04,1.25),(.78,-.24,1.23),(.64,-.60,1.50),(.55,-.74,1.64)]]
def chain_distance(p):
    distances=[]
    for a,b in zip(ARM_CHAIN,ARM_CHAIN[1:]):
        d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));distances.append((p-a-d*t).length)
    return min(distances)
selected={i for i in selected if chain_distance(source_mesh.vertices[i].co)<.187 and source_mesh.vertices[i].co.z>1.115}
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
