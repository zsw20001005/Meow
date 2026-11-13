import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-set-01'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Lulu-Five-Motions.blend'),use_scripts=False)
manifest=json.loads((OUT/'manifest.json').read_text())
scene=bpy.context.scene;rig=bpy.data.objects['Lulu_Rig'];body=bpy.data.objects['Lulu_Body'];cam=scene.camera
scene.render.engine='BLENDER_WORKBENCH';scene.render.fps=30
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT';scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=False;scene.display.shading.show_object_outline=False
body.color=(.70,.72,.76,1)
scene.display.shading.background_type='WORLD';scene.world.color=(.055,.065,.085)
cam.data.type='ORTHO';cam.data.ortho_scale=3.65
camera_base=Vector((3.5,-8,3.15));target_base=Vector((0,0,1.45))
cam.rotation_euler=(target_base-camera_base).to_track_quat('-Z','Y').to_euler()
# Static floor references show forward locomotion and make camera/body rotation distinguishable.
floor_data=bpy.data.meshes.new('Ground reference mesh')
floor_data.from_pydata([(-4,-5,-.035),(4,-5,-.035),(4,4,-.035),(-4,4,-.035)],[],[(0,1,2,3)])
floor=bpy.data.objects.new('Ground reference',floor_data);scene.collection.objects.link(floor);floor.color=(.10,.12,.15,1)
curve=bpy.data.curves.new('Ground grid','CURVE');curve.dimensions='3D';curve.bevel_depth=.002;curve.bevel_resolution=0
for i in range(-10,11):
    a=i*.4
    for coords in [[(a,-4,-.032),(a,4,-.032)],[(-4,a,-.032),(4,a,-.032)]]:
        spline=curve.splines.new('POLY');spline.points.add(1)
        for p,co in zip(spline.points,coords):p.co=(*co,1)
grid=bpy.data.objects.new('Stationary ground grid',curve);scene.collection.objects.link(grid);grid.color=(.16,.19,.23,1)
for clip in manifest['clips']:
    rig.animation_data.action=bpy.data.actions[clip['action']]
    scene.frame_start=1;scene.frame_end=clip['frames'];dest=OUT/'frames'/clip['slug'];dest.mkdir(parents=True,exist_ok=True)
    for f in range(1,clip['frames']+1):
        scene.frame_set(f);bpy.context.view_layer.update()
        # Track translation only for walking. Never rotate the camera for the turn clip.
        shift=Vector((0,rig.location.y,0)) if clip['slug']=='walk' else Vector((0,0,0))
        cam.location=camera_base+shift
        scene.render.filepath=str(dest/f'{f:04d}.png');bpy.ops.render.render(write_still=True)
    print('RENDERED',clip['slug'],clip['frames'],flush=True)
rig.animation_data.action=bpy.data.actions['Lulu_Idle'];scene.frame_start=1;scene.frame_end=120;scene.frame_set(1);cam.location=camera_base
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Lulu-Five-Motions-Preview.blend'))
print('ALL_PREVIEWS_RENDERED',flush=True)
