import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parent/'walk-review/iter_10'
bpy.ops.wm.open_mainfile(filepath=str(root/'lulu-walk-stage.blend'),use_scripts=False)
sc=bpy.context.scene;rig=bpy.data.objects['Lulu full-body skeleton'];cam=sc.camera;report=[]
for f in [1,40,79]:
    sc.frame_set(f);report.append({'frame':f,'rig':list(rig.location),'camera':list(cam.location),'head_in_camera':list(cam.matrix_world.inverted()@rig.matrix_world@rig.pose.bones['Head'].tail)})
print('CAMERA_CHECK',json.dumps(report));sc.frame_set(1);sc.render.filepath=str(root/'check-frame1.png');bpy.ops.render.render(write_still=True)
