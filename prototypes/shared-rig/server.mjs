import http from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url)),vendor=path.resolve(root,'../lulu-rig/vendor');
const types={'.html':'text/html; charset=utf-8','.mjs':'text/javascript','.js':'text/javascript','.json':'application/json','.glb':'model/gltf-binary','.png':'image/png'};
http.createServer(async(req,res)=>{try{const url=decodeURIComponent(new URL(req.url,'http://localhost').pathname),base=url.startsWith('/vendor/')?vendor:root,relative=url.startsWith('/vendor/')?url.slice(8):url==='/'?'index.html':url.slice(1),target=path.resolve(base,relative);if(!target.startsWith(base+path.sep)){res.writeHead(403).end();return;}const data=await readFile(target);res.writeHead(200,{'Content-Type':types[path.extname(target)]||'application/octet-stream','Cache-Control':'no-store'});res.end(data);}catch{res.writeHead(404).end('Not found');}}).listen(8432,'127.0.0.1',()=>console.log('Shared rig preview: http://127.0.0.1:8432/'));
