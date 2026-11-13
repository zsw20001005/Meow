import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'rigged'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'lulu-tpose-rigged-v5.blend'),use_scripts=False)
scene=bpy.context.scene
rig=bpy.data.objects['Lulu_Rig'];mesh=bpy.data.objects['Lulu_Body']
for fc in rig.animation_data.action.fcurves:
    for k in fc.keyframe_points:
        if k.co.x==240:k.co.x=261
        k.handle_left_type='AUTO_CLAMPED';k.handle_right_type='AUTO_CLAMPED'
scene.frame_end=270
camdata=bpy.data.cameras.new('Lulu Preview Camera')
cam=bpy.data.objects.new('Lulu Preview Camera',camdata);scene.collection.objects.link(cam)
cam.location=(3.5,-8,3)
target=Vector((0,0,1.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
camdata.type='ORTHO';camdata.ortho_scale=3.55
scene.camera=cam;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.fps=30
scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE'
scene.display.shading.single_color=(.72,.74,.78)
scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=False
scene.display.shading.background_type='WORLD'
if scene.world is None:scene.world=bpy.data.worlds.new('Preview World')
scene.world.color=(.055,.065,.085)
scene.render.image_settings.file_format='PNG'
frames=OUT/'preview-frames';frames.mkdir(exist_ok=True)
# Set a useful initial viewport and retain an editable animation in the deliverable.
scene.frame_set(31)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=4.5
            area.spaces.active.region_3d.view_location=target
            area.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
            area.spaces.active.shading.color_type='SINGLE'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Lulu-Tpose-Rig-Preview.blend'))
for f in range(1,271):
    scene.frame_set(f);scene.render.filepath=str(frames/f'{f:04d}.png');bpy.ops.render.render(write_still=True)
print('PREVIEW_COMPLETE 270 frames at 30 fps',flush=True)
