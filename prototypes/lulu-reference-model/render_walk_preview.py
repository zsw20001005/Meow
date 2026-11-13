"""Actual 60 fps rig render with world travel, tracking camera and floor marks."""
import bpy,sys,argparse,json,math
from pathlib import Path
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--iteration',default='04');ap.add_argument('--resume',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root=Path(__file__).resolve().parent/'walk-review'/('iter_'+args.iteration)
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-walk.blend'),use_scripts=False)
sc=bpy.context.scene;rig=bpy.data.objects['Lulu full-body skeleton'];cam=sc.camera
meta=json.loads((root/'motion-targets.json').read_text());fps=meta['fps'];period=meta['period_seconds'];speed=meta['speed_units_per_second'];cycle=round(fps*period)
for o in sc.objects:
    if o.type=='MESH' and o.parent!=rig:o.hide_render=True
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.85;return m
floor=material('Soft neutral stage',(.42,.46,.50));grid=material('Quiet ground markers',(.09,.12,.16))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.0005));o=bpy.context.object;o.name='_Walk review floor';o.data.materials.append(floor)
verts=[];faces=[];step=speed*period;width=.004
for i in range(-24,25):
    y=i*step;j=len(verts);verts.extend([(-8,y-width,-.0004),(8,y-width,-.0004),(8,y+width,-.0004),(-8,y+width,-.0004)]);faces.append((j,j+1,j+2,j+3))
for i in range(-15,16):
    x=i*step;j=len(verts);verts.extend([(x-width,-10,-.0004),(x+width,-10,-.0004),(x+width,10,-.0004),(x-width,10,-.0004)]);faces.append((j,j+1,j+2,j+3))
me=bpy.data.meshes.new('Ground markers');me.from_pydata(verts,[],faces);o=bpy.data.objects.new('_Ground markers',me);sc.collection.objects.link(o);me.materials.append(grid)
cam.location=(4.8,-10,2.5);focus=Vector((0,0,1.48));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=3.55;base=cam.location.copy()
for o in sc.objects:
    if o.type=='LIGHT':
        world=o.matrix_world.copy();o.parent=rig;o.matrix_world=world
for f in [1,sc.frame_end]:
    t=(f-1)/fps;rig.location=(0,-speed*t,0);rig.keyframe_insert('location',frame=f);cam.location=base+Vector((0,-speed*t,0));cam.keyframe_insert('location',frame=f)
for o in [rig,cam]:
    for fc in o.animation_data.action.fcurves:
        for key in fc.keyframe_points:key.interpolation='LINEAR'
sc.render.engine='BLENDER_EEVEE_NEXT';sc.eevee.taa_render_samples=96;sc.render.resolution_x=sc.render.resolution_y=640;sc.render.image_settings.file_format='PNG';sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'lulu-walk-stage.blend'))
frames=root/'frames-final';frames.mkdir(exist_ok=True)
for f in range(1,cycle+2):
    if args.resume and (frames/f'frame-{f:04d}.png').exists():continue
    sc.frame_set(f);sc.render.filepath=str(frames/f'frame-{f:04d}.png');bpy.ops.render.render(write_still=True)
print('RENDER_DONE',cycle+1,'FPS',fps)
