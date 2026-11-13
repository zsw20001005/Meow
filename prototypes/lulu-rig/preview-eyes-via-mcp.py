"""Load the eye revision as a separate collection and inspect it through MCP."""
import asyncio,base64,json,os,argparse
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
root=Path(__file__).resolve().parents[2];out=root/'prototypes/lulu-rig/review/sketchfab-lulu'
parser=argparse.ArgumentParser();parser.add_argument('--model',default='lulu-eyes-v1.blend')
args=parser.parse_args()
code="""import json
from mathutils import Vector
assert bpy.data.filepath.endswith('mcp-inspection.blend'), 'Unexpected user scene; not changing it.'
name='Lulu Eye Review'
existing=bpy.data.collections.get(name)
if existing:
    for o in list(existing.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(existing)
collection=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(collection)
with bpy.data.libraries.load(MODEL,link=False) as (src,dst):dst.objects=list(src.objects)
for obj in dst.objects:
    if obj is not None:collection.objects.link(obj)
old=bpy.data.objects.get('Lulu_Source_Inspection')
if old:old.hide_set(True)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.region_3d.view_location=Vector((0,0,2.1))
            area.spaces.active.region_3d.view_distance=3.5
            area.tag_redraw()
print(json.dumps({'collection':name,'objects':[o.name for o in collection.objects],'source_hidden':old.hide_get() if old else None}))
result={'loaded':True}
""".replace('MODEL',repr(str(out/args.model)))
async def main():
    params=StdioServerParameters(command=str(root/'.build-tools/mcp-for-blender-venv/Scripts/mcp-for-blender.exe'),env=dict(os.environ,BLENDER_HOST='127.0.0.1',DISABLE_TELEMETRY='true',BLENDER_MCP_DISABLE_TELEMETRY='true'))
    async with stdio_client(params) as (r,w):
        async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=55)) as session:
            await session.initialize()
            loaded=await session.call_tool('execute_blender_code',{'code':code,'user_prompt':'不能完全依赖这个模型，这个眼睛很无神，我希望你参考现有的ai生成的眼睛重构一下眼睛'})
            text=[c.text for c in loaded.content if c.type=='text'];print(json.dumps(text,ensure_ascii=False))
            if loaded.isError or not any('"loaded"' in s or '"collection"' in s for s in text):raise RuntimeError('Scene update was not confirmed')
            preview=await session.call_tool('look',{'mode':'viewport','shading':'material','max_size':1200})
            for c in preview.content:
                if c.type=='image':(out/'eyes-mcp-viewport.png').write_bytes(base64.b64decode(c.data))
                elif c.type=='text':print(c.text)
asyncio.run(main())
