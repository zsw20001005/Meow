"""Split CC0 source assets into animation-free skins and one motion library."""
from pathlib import Path
import json, base64, struct, copy, hashlib

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'assets/runtime'
OUT.mkdir(parents=True, exist_ok=True)

def pack(document, output, motions=False):
    m = copy.deepcopy(document)
    raw = base64.b64decode(m['buffers'][0]['uri'].split(',',1)[1])
    assert len(m['buffers']) == 1
    used = set()
    if motions:
        for n in m['nodes']:
            n.pop('mesh',None);n.pop('skin',None)
        for key in ['meshes','skins','materials','textures','images','samplers']:m.pop(key,None)
        for a in m['animations']:
            for s in a['samplers']:used.update((s['input'],s['output']))
    else:
        m.pop('animations',None)
        for mesh in m['meshes']:
            for p in mesh['primitives']:
                used.update(p['attributes'].values())
                if 'indices' in p:used.add(p['indices'])
                for target in p.get('targets',[]):used.update(target.values())
        for skin in m.get('skins',[]):
            if 'inverseBindMatrices' in skin:used.add(skin['inverseBindMatrices'])
    accessors=sorted(used); amap={old:new for new,old in enumerate(accessors)}
    views=set()
    for i in accessors:
        assert 'sparse' not in m['accessors'][i]
        views.add(m['accessors'][i]['bufferView'])
    for image in m.get('images',[]):views.add(image['bufferView'])
    views=sorted(views);vmap={old:new for new,old in enumerate(views)}
    binary=bytearray();newviews=[]
    for i in views:
        v=copy.deepcopy(m['bufferViews'][i]);start=v.get('byteOffset',0)
        while len(binary)%4:binary.append(0)
        offset=len(binary);binary.extend(raw[start:start+v['byteLength']]);v['buffer']=0;v['byteOffset']=offset;newviews.append(v)
    m['accessors']=[m['accessors'][i] for i in accessors]
    for a in m['accessors']:a['bufferView']=vmap[a['bufferView']]
    m['bufferViews']=newviews
    if motions:
        for a in m['animations']:
            for s in a['samplers']:s['input']=amap[s['input']];s['output']=amap[s['output']]
    else:
        for mesh in m['meshes']:
            for p in mesh['primitives']:
                p['attributes']={k:amap[v] for k,v in p['attributes'].items()}
                if 'indices' in p:p['indices']=amap[p['indices']]
                for target in p.get('targets',[]):
                    for k in target:target[k]=amap[target[k]]
        for skin in m.get('skins',[]):skin['inverseBindMatrices']=amap[skin['inverseBindMatrices']]
    for image in m.get('images',[]):image['bufferView']=vmap[image['bufferView']]
    m['buffers']=[{'byteLength':len(binary)}]
    encoded=json.dumps(m,separators=(',',':')).encode()
    encoded+=b' '*((-len(encoded))%4);binary+=b'\0'*((-len(binary))%4)
    glb=struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary
    output.write_bytes(glb)
    return {'file':output.name,'bytes':len(glb),'sha256':hashlib.sha256(glb).hexdigest(),'animations':len(m.get('animations',[]))}

report={'author':'Quaternius','license':'CC0-1.0','source':'https://quaternius.com/packs/sushirestaurantkit.html','files':[]}
for name in ['Panda','Rabbit_Pink']:
    m=json.loads((ROOT/'assets/sushi-original'/f'{name}.gltf').read_text())
    report['files'].append(pack(m,OUT/f'{name}.glb'))
    if name=='Panda':report['files'].append(pack(m,OUT/'shared-motions.glb',True))
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
