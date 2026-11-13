from pathlib import Path
import bpy,sys,argparse
from mathutils import Vector
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
parser=argparse.ArgumentParser();parser.add_argument('--video',action='store_true');parser.add_argument('--limbs',action='store_true');parser.add_argument('--free',action='store_true');parser.add_argument('--labels',nargs='+');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if args.free:args.limbs=True
bpy.ops.wm.open_mainfile(filepath=str(root/('lulu-limbs-v2.blend' if args.free else 'lulu-limbs-v1.blend' if args.limbs else 'lulu-performance-v1.blend')))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=8 if args.video else 24;sc.cycles.use_denoising=True
sc.render.resolution_x=sc.render.resolution_y=512 if args.video else 800;sc.render.resolution_percentage=100
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=-.25
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.8,.8,.8,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.28
if args.free:
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));floor=bpy.context.object
    mat=bpy.data.materials.new('Review ground');mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.32,.32,.32,1);mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.9;floor.data.materials.append(mat)
focus=Vector((0,0,1.5))
def aim(o):o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
for name,pos,power,size in [('Key',(-3,-4,6),260,4),('Fill',(4,-3,4),140,4),('Rim',(1,3,5),260,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=pos;aim(o)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=3.55;cam.location=(0,-10,1.5);aim(cam);sc.camera=cam
owners=[bpy.data.objects['Lulu Motion Rig']]+[o.data.shape_keys for o in sc.objects if o.type=='MESH' and o.data.shape_keys]
def select(name,frame):
    for owner in owners:
        if owner.animation_data:
            for track in owner.animation_data.nla_tracks:track.mute=track.name!=name
    sc.frame_set(frame)
if args.video:
    select('HumanWave' if args.free else 'Steps' if args.limbs else 'Greeting',0);sc.frame_start=0;sc.frame_end=179;sc.render.fps=30
    sc.render.image_settings.file_format='FFMPEG';sc.render.ffmpeg.format='MPEG4';sc.render.ffmpeg.codec='H264';sc.render.ffmpeg.constant_rate_factor='MEDIUM';sc.render.filepath=str(root/('limbs-v2.mp4' if args.free else 'limbs-v1.mp4' if args.limbs else 'greeting-v1.mp4'))
    bpy.ops.render.render(animation=True)
else:
    poses=([('rest','Idle',0),('arms','Arms',75),('arms-side','Arms',75),('left-knee','Legs',40),('right-knee','Legs',109),('knee-side','Legs',40)] if args.limbs else [('neutral','Idle',0),('notice','Greeting',17),('blink','Greeting',34),('happy','Greeting',69),('curious','Curious',54),('settle','Greeting',155)])
    if args.free:poses=[('rest','Idle',0),('arms','HumanWave',75),('arms-side','HumanWave',75),('left-knee','HumanSteps',45),('right-knee','HumanSteps',126),('knee-side','HumanSteps',45)]
    for label,name,frame in poses:
        if args.labels and label not in args.labels:continue
        select(name,frame);cam.data.ortho_scale=3.5 if args.limbs else 2.3;focus.z=1.5 if args.limbs else 2.05;cam.location=(7,-7,focus.z) if label.endswith('side') else (0,-10,focus.z);aim(cam)
        sc.render.filepath=str(root/(('free-' if args.free else 'limbs-' if args.limbs else 'performance-')+label+'.png'));bpy.ops.render.render(write_still=True)
print('PERFORMANCE_REVIEW_DONE')
