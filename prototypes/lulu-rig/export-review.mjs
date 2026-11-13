import {writeFile,mkdir} from 'node:fs/promises';
import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';
import {createLulu} from './rig.mjs';

// The exporter uses the browser FileReader API even for geometry-only GLBs.
globalThis.FileReader=class {
  readAsArrayBuffer(blob){blob.arrayBuffer().then(value=>{this.result=value;this.onloadend?.();});}
  readAsDataURL(blob){blob.arrayBuffer().then(value=>{this.result='data:'+blob.type+';base64,'+Buffer.from(value).toString('base64');this.onloadend?.();});}
};
const name=process.argv[2]||'shape-before';
if(!/^[a-z0-9-]+$/.test(name))throw new Error('Use a simple review filename');
const rig=createLulu({texture:false});
const data=await new GLTFExporter().parseAsync(rig.model,{binary:true,onlyVisible:true});
await mkdir(new URL('./review/',import.meta.url),{recursive:true});
await writeFile(new URL('./review/'+name+'.glb',import.meta.url),Buffer.from(data));
console.log('Exported actual model: review/'+name+'.glb');
