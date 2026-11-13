from pathlib import Path
import bpy,argparse,sys
from mathutils import Vector
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
parser=argparse.ArgumentParser();parser.add_argument('--clip',choices=['Idle','Blink','Nod','Look','Wave'])
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-motion-v1.blend'))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=sc.render.resolution_y=700;sc.render.resolution_percentage=100
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=-.25
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.8,.8,.8,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.28
focus=Vector((0,0,1.5))
def aim(o):o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
for name,pos,power,size in [('Key',(-3,-4,6),260,4),('Fill',(4,-3,4),140,4),('Rim',(1,3,5),260,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=pos;aim(o)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=3.55;sc.camera=cam;cam.location=(0,-10,1.5);aim(cam)
owners=[bpy.data.objects['Lulu Motion Rig']]+[o.data.shape_keys for o in sc.objects if o.type=='MESH' and o.data.shape_keys]
for name,frame in [('Idle',30),('Blink',24),('Nod',36),('Look',48),('Wave',50)]:
    if args.clip and name!=args.clip:continue
    for owner in owners:
        for track in owner.animation_data.nla_tracks:track.mute=track.name!=name
    sc.frame_set(frame)
    cam.data.ortho_scale=2.15 if name=='Blink' else 3.55;focus.z=2.1 if name=='Blink' else 1.5;cam.location.z=focus.z;aim(cam)
    sc.render.filepath=str(root/('motion-check-'+name.lower()+'.png'));bpy.ops.render.render(write_still=True)
print('MOTION_REVIEW_RENDERED')
