import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const types={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.png':'image/png','.jpg':'image/jpeg','.glb':'model/gltf-binary'};
http.createServer(async(req,res)=>{
  try {
    const p=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    const target=path.resolve(root,'.'+(p==='/'?'/index.html':p));
    if(!target.startsWith(root+path.sep)){res.writeHead(403).end();return;}
    const data=await readFile(target);
    res.writeHead(200,{'Content-Type':types[path.extname(target)]||'application/octet-stream','Cache-Control':'no-store'});res.end(data);
  } catch {res.writeHead(404).end('Not found');}
}).listen(8426,'127.0.0.1',()=>console.log('Lulu rig prototype: http://127.0.0.1:8426'));
