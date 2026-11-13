"""Render the real exported mesh offline; no browser automation or image editing."""
import argparse
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--view', default='front', choices=['front', 'side', 'three-quarter', 'back'])
parser.add_argument('--samples', type=int, default=32)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
model_path=Path(args.model).resolve()
if model_path.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(model_path))
else:bpy.ops.import_scene.gltf(filepath=str(model_path))
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.color = (.6, .6, .6)
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.82, .83, .85, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()

def light(name, position, power, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = position
    aim(obj, (0, 0, 1.6))

light('Key softbox', (-3.5, -4.5, 6), 480, 4)
light('Fill softbox', (4, -2.5, 3.5), 260, 4)
light('Rim softbox', (1, 3, 5), 400, 3)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.025))
floor = bpy.context.object
mat = bpy.data.materials.new('neutral studio')
mat.diffuse_color = (.85, .85, .82, 1)
floor.data.materials.append(mat)
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 3.95
camera.location = {'front': (0, -10, 1.72), 'side': (10, 0, 1.72), 'three-quarter': (5, -10, 2.65), 'back': (0, 10, 1.72)}[args.view]
aim(camera, (0, 0, 1.72))
scene.camera = camera
out = Path(args.output).resolve()
out.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(out)
bpy.ops.wm.save_as_mainfile(filepath=str(out.with_suffix('.blend')))
bpy.ops.render.render(write_still=True)
