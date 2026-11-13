import bpy,json
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-set-01'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Lulu-Five-Motions.blend'),use_scripts=False)
manifest=json.loads((OUT/'manifest.json').read_text())
rig=bpy.data.objects['Lulu_Rig'];body=bpy.data.objects['Lulu_Body'];scene=bpy.context.scene
def positions(frame):
    scene.frame_set(frame);bpy.context.view_layer.update()
    obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return np.array([obj.matrix_world@v.co for v in obj.data.vertices]),np.array(rig.location)
result={}
neutral=None
for clip in manifest['clips']:
    rig.animation_data.action=bpy.data.actions[clip['action']]
    start,root0=positions(1);end,root1=positions(clip['frames']+1)
    if neutral is None:neutral=start-root0
    delta=np.linalg.norm((end-root1)-(start-root0),axis=1)
    frames=[1,clip['frames']//4,clip['frames']//2,3*clip['frames']//4,clip['frames']]
    sampled=[positions(f)[0] for f in frames]
    item={'end_pose_max_difference_after_root_translation':float(delta.max()),'start_pose_difference_from_idle':float(np.linalg.norm((start-root0)-neutral,axis=1).max()),'root_translation':(root1-root0).tolist(),'sampled_minimum_surface_z':min(float(p[:,2].min()) for p in sampled),'all_finite':all(bool(np.isfinite(p).all()) for p in sampled)}
    assert item['all_finite']
    assert item['end_pose_max_difference_after_root_translation']<1e-4,item
    assert item['start_pose_difference_from_idle']<1e-4,item
    result[clip['slug']]=item
(OUT/'playback-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2),flush=True)
