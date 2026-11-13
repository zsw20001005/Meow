"""Reuse genuine rendered frames only after exact geometry/pose comparisons."""
import bpy,hashlib,numpy as np,shutil,json
from pathlib import Path
root=Path(__file__).resolve().parent/'rig-review'
def fingerprint(version):
    bpy.ops.wm.open_mainfile(filepath=str(root/version/'lulu-wave-test.blend'),use_scripts=False)
    hashes={}
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        h=hashlib.sha256();a=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',a);h.update(a.tobytes())
        h.update(np.asarray(obj.matrix_world,dtype=np.float32).tobytes())
        for v in obj.data.vertices:
            h.update(np.asarray([(g.group,g.weight) for g in v.groups],dtype=np.float32).tobytes())
        for attr in obj.data.color_attributes:
            a=np.empty(len(attr.data)*4,dtype=np.float32);attr.data.foreach_get('color',a);h.update(a.tobytes())
        hashes[obj.name]=h.hexdigest()
    rig=bpy.data.objects['Lulu articulated test'];poses={}
    for curve in rig.animation_data.action.fcurves:
        poses[(curve.data_path,curve.array_index)]=np.array([curve.evaluate(f) for f in range(12,116)])
    return hashes,poses
a,pa=fingerprint('iter_04');b,pb=fingerprint('iter_05')
assert a==b,'Geometry, weights, colors or transforms changed; render all frames'
assert pa.keys()==pb.keys()
error=max(float(np.max(np.abs(pa[k]-pb[k]))) for k in pa)
assert error<1e-7,'Pose changed; render all frames'
target=root/'iter_05/frames-clean';target.mkdir(exist_ok=True)
for frame in range(12,116):
    source=root/'iter_04/frames-clean'/f'frame-{frame:04d}.png'
    assert source.exists(),str(source)
    shutil.copy2(source,target/source.name)
(root/'iter_05/render-reuse-check.json').write_text(json.dumps({'mesh_fingerprints_identical':True,'max_channel_error':error,'first_reused_frame':12,'last_reused_frame':115,'count':104},indent=2),encoding='utf-8')
print('VERIFIED_RENDER_REUSE',error,104)
