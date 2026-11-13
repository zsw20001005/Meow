import bpy, json, math
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'rigged/lulu-mia-rigged.blend'),use_scripts=False)
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=next(o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers))
for o in scene.objects:
    if o.type=='MESH' and o!=mesh: o.hide_render=True
def axis_rotation(name, axis, angle):
    b=arm.pose.bones['mixamorig:'+name]
    worldrot=(arm.matrix_world.to_3x3() @ b.bone.matrix_local.to_3x3()).normalized()
    local=worldrot.inverted() @ Vector(axis)
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=Quaternion(local,math.radians(angle))
def coords():
    bpy.context.view_layer.update()
    e=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [e.matrix_world @ v.co for v in e.data.vertices]
base=coords()
movement={}
for name,axis in [('LeftArm',(0,1,0)),('RightArm',(0,1,0)),('LeftUpLeg',(1,0,0)),('RightUpLeg',(1,0,0))]:
    axis_rotation(name,axis,20)
    pts=coords()
    ds=[(a-b).length for a,b in zip(base,pts)]
    movement[name]={'test_angle_degrees':20,'vertices_moved_over_1mm':sum(d>0.001 for d in ds),'max_displacement':max(ds)}
    axis_rotation(name,axis,0)
(ROOT/'rigged/motion-check.json').write_text(json.dumps(movement,indent=2),encoding='utf-8')
scene.frame_start=1
scene.frame_end=48
scene.render.fps=24
for f in range(1,49):
    phase=(f-1)/47*2*math.pi
    for name,axis,amp in [('LeftArm',(0,1,0),18),('RightArm',(0,1,0),-18),('LeftUpLeg',(1,0,0),15),('RightUpLeg',(1,0,0),-15)]:
        axis_rotation(name,axis,amp*math.sin(phase))
        arm.pose.bones['mixamorig:'+name].keyframe_insert('rotation_quaternion',frame=f)
scene.frame_set(1)
camdata=bpy.data.cameras.new('Diagnostic camera')
cam=bpy.data.objects.new('Diagnostic camera',camdata)
scene.collection.objects.link(cam)
cam.location=(4,-8,3.1)
cam.rotation_euler=(Vector((0,0,1.5))-cam.location).to_track_quat('-Z','Y').to_euler()
camdata.type='ORTHO'; camdata.ortho_scale=3.8
scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(0.65,0.67,0.7)
scene.display.shading.background_type='WORLD'
if scene.world is None: scene.world=bpy.data.worlds.new('Diagnostic world')
scene.world.color=(0.12,0.12,0.12)
scene.render.image_settings.file_format='PNG'
out=ROOT/'rigged/motion-frames';out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'rigged/lulu-motion-diagnostic.blend'))
for f in range(1,49):
    scene.frame_set(f);scene.render.filepath=str(out/f'{f:04d}.png');bpy.ops.render.render(write_still=True)
print('MOTION_CHECK',json.dumps(movement),flush=True)
