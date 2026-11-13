import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'rig-review/iter_05/lulu-wave-test.blend'),use_scripts=False)
rig=bpy.data.objects['Lulu articulated test'];rig.animation_data_clear()
for b in rig.pose.bones:b.rotation_quaternion=(1,0,0,0);b.scale=(1,1,1);b.location=(0,0,0)
body=bpy.data.objects['Lulu.Body'];a=np.array([v.co[:] for v in body.data.vertices]);report={}
for z in [.05,.12,.2,.3,.4,.5,.6,.7,.8,.9,1,1.1,1.2,1.3,1.4,1.5,1.6]:
    p=a[abs(a[:,2]-z)<.008];report[str(z)]={'min':p.min(0).tolist(),'max':p.max(0).tolist(),'left_center':p[p[:,0]<0].mean(0).tolist(),'right_center':p[p[:,0]>0].mean(0).tolist()}
print('SECTIONS',json.dumps(report))
out=root/'walk-review/source';out.mkdir(parents=True,exist_ok=True)
sc=bpy.context.scene;sc.render.engine='BLENDER_EEVEE_NEXT';sc.eevee.taa_render_samples=32;sc.render.resolution_x=sc.render.resolution_y=720
focus=Vector((0,0,1.3));cam=sc.camera;cam.data.ortho_scale=3.3
for name,pos in [('side',(8,-2,1.6)),('back',(0,10,1.5)),('front',(0,-10,1.5))]:
    cam.location=pos;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
