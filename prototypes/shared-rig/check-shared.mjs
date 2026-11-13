import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {bindPose,retarget,SharedPlayback} from './shared-rig.mjs';
const root=new URL('./assets/runtime/',import.meta.url);
globalThis.ProgressEvent=class extends Event { constructor(type,init={}){super(type);Object.assign(this,init);} };
// Geometry-only diagnostics remove texture references, not vertex/skin data.
async function load(name){
  const b=await readFile(new URL(name,root)),len=b.readUInt32LE(12),m=JSON.parse(b.subarray(20,20+len).toString());
  const start=20+len+8;m.buffers[0].uri='data:application/octet-stream;base64,'+b.subarray(start).toString('base64');
  delete m.images;delete m.textures;delete m.samplers;
  for(const mat of m.materials||[]){if(mat.pbrMetallicRoughness)delete mat.pbrMetallicRoughness.baseColorTexture;}
  return new GLTFLoader().parseAsync(JSON.stringify(m),'');
}
const panda=await load('Panda.glb'),rabbit=await load('Rabbit_Pink.glb'),library=await load('shared-motions.glb');
assert.equal(panda.animations.length,0);assert.equal(rabbit.animations.length,0);assert.equal(library.animations.length,30);
const reference=bindPose(panda.scene),report={sharedClips:30,characters:{}};
function points(scene){scene.updateMatrixWorld(true);const list=[];scene.traverse(o=>{if(!o.isMesh)return;o.skeleton?.update();for(let i=0;i<o.geometry.attributes.position.count;i+=3){const p=o.getVertexPosition(i,new THREE.Vector3()).applyMatrix4(o.matrixWorld);assert.ok(p.toArray().every(Number.isFinite));list.push(p);}});return list;}
function diff(a,b){return Math.max(...a.map((p,i)=>p.distanceTo(b[i])));}
for(const [name,gltf]of[['Panda',panda],['Rabbit',rabbit]]){
  const rest=bindPose(gltf.scene),transfer=retarget(library.animations,reference,rest);assert.equal(rest.size,43);
  const results={joints:rest.size,proportionScale:transfer.ratio,clips:{}};
  for(const key of ['Idle','Walk','Wave','Yes','No','Jump','Sitting_Start','Sitting_Idle','Sitting_End']){
    const clip=transfer.clips.find(c=>c.name===key),mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();mixer.setTime(0);const first=points(gltf.scene);let motion=0,minY=Infinity,maxY=-Infinity;
    for(let i=0;i<=30;i++){mixer.setTime(i*clip.duration/30);const p=points(gltf.scene);motion=Math.max(motion,diff(first,p));minY=Math.min(minY,...p.map(v=>v.y));maxY=Math.max(maxY,...p.map(v=>v.y));}
    assert.ok(motion>.001,key+' must move');assert.ok(maxY-minY<12,key+' deformation exploded');
    results.clips[key]={duration:clip.duration,maximumMotion:motion,minY,maxY,seam:diff(first,points(gltf.scene))};mixer.stopAllAction();mixer.uncacheRoot(gltf.scene);
  }
  const playback=new SharedPlayback(gltf.scene,transfer.clips);playback.play('Idle');playback.update(.4);results.switchJumps=[];
  for(const key of ['Wave','Walk','Yes','Idle']){const before=points(gltf.scene);playback.play(key);const jump=diff(before,points(gltf.scene));assert.ok(jump<1e-5,`${name} ${key} instantaneous switch jump: ${jump}`);results.switchJumps.push(jump);playback.update(.12);}
  report.characters[name]=results;
}
await writeFile(new URL('./shared-checks.json',import.meta.url),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
