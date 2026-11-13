"""Exercise the installed MCP protocol against the local Blender review copy."""
import asyncio,base64,json,os
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
root=Path(__file__).resolve().parents[2]
out=root/'prototypes/lulu-rig/review/sketchfab-lulu'
async def main():
    env=dict(os.environ,BLENDER_HOST='127.0.0.1',DISABLE_TELEMETRY='true',BLENDER_MCP_DISABLE_TELEMETRY='true')
    params=StdioServerParameters(command=str(root/'.build-tools/mcp-for-blender-venv/Scripts/mcp-for-blender.exe'),env=env)
    report={}
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=45)) as session:
            init=await session.initialize()
            report['server']=init.serverInfo.model_dump()
            listed=await session.list_tools();report['tool_names']=[t.name for t in listed.tools]
            calls=[('scene','get_scene_info',{'fields':['settings','details','materials'],'user_prompt':'试试'}),
                   ('material','execute_blender_code',{'user_prompt':'试试','code':"""import json
assert bpy.data.filepath.endswith('mcp-inspection.blend'), bpy.data.filepath
obj=bpy.data.objects['Lulu_Source_Inspection']
mat=obj.data.materials[0]
bs=mat.node_tree.nodes['Principled BSDF']
old=bs.inputs['Roughness'].default_value
bs.inputs['Roughness'].default_value=0.73
changed=abs(bs.inputs['Roughness'].default_value-0.73)<1e-5
bs.inputs['Roughness'].default_value=old
print(json.dumps({'file':bpy.data.filepath,'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons),'material_edit_verified':changed,'restored':bs.inputs['Roughness'].default_value==old}))
result={'material_edit_verified':changed}
"""}),
                   ('preview','look',{'mode':'angles','target':['Lulu_Source_Inspection'],'views':['front','right','three_quarter'],'shading':'solid','max_size':1200,'user_prompt':'试试'})]
            for label,name,args in calls:
                result=await session.call_tool(name,args)
                texts=[c.text for c in result.content if c.type=='text']
                report[label]={'isError':result.isError,'text':texts}
                for c in result.content:
                    if c.type=='image':
                        path=out/('mcp-'+label+'.png');path.write_bytes(base64.b64decode(c.data))
                        report[label]['image']=str(path)
                print(label,json.dumps(report[label],ensure_ascii=False))
    (out/'mcp-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
asyncio.run(main())
