import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const folder=new URL('./review/sketchfab-lulu/',import.meta.url);
const data=await readFile(new URL('lulu-limbs-v2.glb',folder));
const gltf=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
assert.deepEqual(gltf.animations.map(c=>c.name).sort(),['HumanSteps','HumanWave','Idle']);
const meshes=[];gltf.scene.traverse(o=>{if(o.isMesh)meshes.push(o);});
const mixer=new THREE.AnimationMixer(gltf.scene);
function points(mesh){gltf.scene.updateMatrixWorld(true);if(mesh.skeleton)mesh.skeleton.update();const values=[];for(let i=0;i<mesh.geometry.attributes.position.count;i+=30){const p=mesh.getVertexPosition(i,new THREE.Vector3()).applyMatrix4(mesh.matrixWorld);assert.ok(p.toArray().every(Number.isFinite));values.push(p);}return values;}
function find(name){const m=meshes.find(o=>o.name.replace(/[^a-z0-9]/gi,'')===name);assert.ok(m,'Missing '+name);return m;}
const delta=(a,b)=>Math.max(...a.map((p,i)=>p.distanceTo(b[i])));
const report={};
for(const [name,target,threshold] of [['HumanWave','IndependentHandL',.6],['HumanSteps','IndependentLegL',.18]]){
  const clip=gltf.animations.find(c=>c.name===name),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();mixer.setTime(0);
  const mesh=find(target),start=points(mesh);let maximum=0;
  for(let frame=1;frame<=180;frame++){mixer.setTime(frame/30);maximum=Math.max(maximum,delta(start,points(mesh)));}
  const seam=delta(start,points(mesh));assert.ok(maximum>threshold,name+' must show a clearly visible limb displacement');assert.ok(seam<1e-4,name+' return-to-rest mismatch');
  report[name]={target,maximumDisplacement:maximum,minimumRequired:threshold,seam};mixer.stopAllAction();
}
const step=mixer.clipAction(gltf.animations.find(c=>c.name==='HumanSteps'));step.reset().play();mixer.setTime(0);
const left=find('IndependentLegL'),right=find('IndependentLegR'),leftRest=points(left),rightRest=points(right);
mixer.setTime(1.5);const rightSlide=delta(rightRest,points(right));mixer.setTime(4.2);const leftSlide=delta(leftRest,points(left));
assert.ok(Math.max(leftSlide,rightSlide)<1e-4,`Support leg drift: L=${leftSlide}, R=${rightSlide}`);
report.supportLegDrift={left:leftSlide,right:rightSlide};
await writeFile(new URL('limbs-v2-motion-check.json',folder),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
