"""Enable the installed addon and prepare a disposable inspection scene."""
from pathlib import Path
import bpy,addon_utils,math
from mathutils import Euler,Vector

root=Path(__file__).resolve().parent
addon_utils.enable('blender_mcp',default_set=True,persistent=True)
prefs=bpy.context.preferences.addons['blender_mcp'].preferences
prefs.bind_address='127.0.0.1'
prefs.allow_remote_connections=False
prefs.telemetry_consent=False
bpy.ops.wm.save_userpref()
bpy.ops.wm.open_mainfile(filepath=str(root/'review/sketchfab-lulu/source-normalized.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
obj.name='Lulu_Source_Inspection'
mat=bpy.data.materials.new('Lulu_Material_Connection_Test');mat.use_nodes=True
mat.diffuse_color=(.62,.62,.62,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.62,.62,.62,1)
obj.data.materials.clear();obj.data.materials.append(mat)
bpy.context.scene.blendermcp_auto_start_server=True
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.region_3d.view_rotation=Euler((math.pi/2,0,0)).to_quaternion()
            space.region_3d.view_location=Vector((0,0,1.5))
            space.region_3d.view_distance=5.2
            space.region_3d.view_perspective='ORTHO'
            space.overlay.show_overlays=False
            space.shading.type='SOLID'
            space.shading.color_type='MATERIAL'
            space.shading.light='STUDIO'
            space.shading.show_cavity=True
bpy.ops.wm.save_as_mainfile(filepath=str(root/'review/sketchfab-lulu/mcp-inspection.blend'))
print('MCP_ADDON_ENABLED_AND_INSPECTION_READY')
