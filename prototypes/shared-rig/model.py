"""Non-destructive studio inspection of Quaternius' CC0 rigged characters."""
import sys, json, math
from pathlib import Path
sys.path.insert(0, r'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import modelkit as mk
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'renders' / 'iter_01'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 760
scene.render.resolution_percentage = 100
scene.world.color = (.3, .3, .3)
scene.view_settings.view_transform = 'AgX'
scene.render.image_settings.file_format = 'PNG'
report = []
for label, offset in [('Panda', -1.7), ('Rabbit_Pink', 1.7)]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/sushi-original' / (label + '.gltf')))
    objects = set(bpy.data.objects) - before
    rigs = [o for o in objects if o.type == 'ARMATURE']
    widgets = {b.custom_shape for rig in rigs for b in rig.pose.bones if b.custom_shape is not None}
    objects -= widgets
    for rig in rigs:
        tracks = list(rig.animation_data.nla_tracks) if rig.animation_data else []
        idle = next((t.strips[0].action for t in tracks if t.name == 'Idle'), None)
        if idle is None:
            idle = next((t.strips[0].action for t in tracks if 'Idle' in t.name and 'Holding' not in t.name and 'Sitting' not in t.name), None)
        for t in tracks: t.mute = True
        if idle:
            rig.animation_data.action = idle
            if hasattr(idle, 'slots') and len(idle.slots): rig.animation_data.action_slot = idle.slots[0]
        report.append({'character': label, 'bones': len(rig.data.bones), 'actions': [t.name for t in tracks], 'idle': idle.name if idle else None})
    scene.frame_set(10)
    bpy.context.view_layer.update()
    meshes = [o for o in objects if o.type == 'MESH' and o.visible_get()]
    deps = bpy.context.evaluated_depsgraph_get()
    coords = [o.matrix_world @ v.co for o in meshes for v in o.evaluated_get(deps).data.vertices]
    lo = Vector([min(p[k] for p in coords) for k in range(3)])
    hi = Vector([max(p[k] for p in coords) for k in range(3)])
    factor = 3 / (hi.z-lo.z)
    pivot = bpy.data.objects.new(label+' Display', None)
    scene.collection.objects.link(pivot)
    for o in objects:
        if o.parent not in objects: o.parent = pivot
    pivot.scale = (factor,)*3
    pivot.location = (offset-(hi.x+lo.x)/2*factor, -(hi.y+lo.y)/2*factor, -lo.z*factor)
    report[-1]['source_dimensions'] = list(hi-lo)
    for o in meshes:
        for mat in o.data.materials:
            if mat and mat.use_nodes:
                bs = next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'), None)
                if bs:
                    bs.inputs['Roughness'].default_value=.68
                    bs.inputs['Metallic'].default_value=0
    # Preserve authored normals/topology; do not smooth away facial features.

bpy.ops.mesh.primitive_plane_add(size=200)
floor = bpy.context.object
floor.name = 'Studio floor'
mat = bpy.data.materials.new('Warm porcelain backdrop'); mat.diffuse_color=(.79,.83,.85,1)
floor.data.materials.append(mat)
def area(name, location, power, size):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=location
    obj.rotation_euler=(Vector((0,0,1.5))-obj.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-4,-6,8),1100,6);area('Fill',(5,-3,5),650,5);area('Rim',(1,4,7),1200,4)
data=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',data);scene.collection.objects.link(cam)
cam.location=(0,-12,5.0);cam.rotation_euler=(Vector((0,0,1.5))-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=7.9;scene.camera=cam
# Importing a second glTF resets scene animation time. Re-evaluate both poses
# before grounding, using the actual deformed meshes rather than rest bounds.
scene.frame_set(10);bpy.context.view_layer.update()
for name in ['Panda Display','Rabbit_Pink Display']:
    pivot=bpy.data.objects[name]
    deps=bpy.context.evaluated_depsgraph_get()
    bottom=min((o.evaluated_get(deps).matrix_world @ v.co).z for o in pivot.children_recursive if o.type=='MESH' for v in o.evaluated_get(deps).data.vertices)
    pivot.location.z-=bottom
bpy.context.view_layer.update()
(OUT/'inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidates.blend'))
scene.render.filepath=str(OUT/'candidates.png');bpy.ops.render.render(write_still=True)
