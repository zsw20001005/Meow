"""Render the actual painted mesh with neutral, color-preserving studio light."""
import bpy,sys,argparse
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
parser=argparse.ArgumentParser()
parser.add_argument('--model',default='lulu-colored.blend');parser.add_argument('--prefix',default='painted');parser.add_argument('--head',action='store_true')
parser.add_argument('--views',nargs='+',choices=['front','three-quarter','side'],default=['front','three-quarter','side'])
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(root/args.model))
sc=bpy.context.scene
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=sc.render.resolution_y=1200;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=-.25
sc.world.use_nodes=True
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.8,.8,.8,1)
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.28
focus=Vector((0,0,2.10 if args.head else 1.5))
def aim(o):o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
for name,pos,power,size in [('Key',(-3,-4,6),260,4),('Fill',(4,-3,4),140,4),('Rim',(1,3,5),260,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=pos;aim(o)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.018))
m=bpy.data.materials.new('Warm neutral studio');m.diffuse_color=(.77,.76,.73,1);bpy.context.object.data.materials.append(m)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=2.15 if args.head else 3.55;sc.camera=cam
for view,pos in [('front',(0,-10,focus.z)),('three-quarter',(4.5,-10,focus.z+.8)),('side',(10,0,focus.z))]:
    if view not in args.views:continue
    cam.location=pos;aim(cam)
    sc.render.filepath=str(root/(args.prefix+'-'+view+'.png'))
    bpy.ops.render.render(write_still=True)
cam.location=(0,-10,focus.z);aim(cam)
bpy.ops.wm.save_as_mainfile(filepath=str(root/(args.prefix+'-studio.blend')))
