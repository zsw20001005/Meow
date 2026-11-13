"""Cleaner studio animation preview of the already-built, unchanged test rig."""
import bpy,argparse,sys
from pathlib import Path
from mathutils import Vector
parser=argparse.ArgumentParser();parser.add_argument('--iteration',default='05');parser.add_argument('--ends-only',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root=Path(__file__).resolve().parent/'rig-review'/('iter_'+args.iteration)
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-wave-test.blend'),use_scripts=False)
sc=bpy.context.scene;sc.render.engine='BLENDER_EEVEE_NEXT';sc.eevee.taa_render_samples=96
sc.render.resolution_x=sc.render.resolution_y=600;sc.render.image_settings.file_format='PNG'
light=bpy.data.lights.new('Preview lower fill','AREA');light.energy=100;light.shape='DISK';light.size=5
obj=bpy.data.objects.new('Preview lower fill',light);sc.collection.objects.link(obj);obj.location=(0,-4,1.5);obj.rotation_euler=(Vector((0,0,1.5))-obj.location).to_track_quat('-Z','Y').to_euler()
frames=root/'frames-clean';frames.mkdir(exist_ok=True);sc.render.filepath=str(frames/'frame-')
if args.ends_only:
    for frame in list(range(1,12))+list(range(116,122)):
        sc.frame_set(frame);sc.render.filepath=str(frames/f'frame-{frame:04d}.png');bpy.ops.render.render(write_still=True)
else:bpy.ops.render.render(animation=True)
