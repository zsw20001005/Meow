import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {LuluPlayback} from './motion-playback.mjs';
import {LimbPose} from './limb-controls.mjs';
const performanceMode=process.argv.includes('--performance');
const limbsMode=process.argv.includes('--limbs');
const data=await readFile(new URL('./review/sketchfab-lulu/'+(limbsMode?'lulu-limbs-v1.glb':performanceMode?'lulu-performance-v1.glb':'lulu-motion-v1.glb'),import.meta.url));
const gltf=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
assert.deepEqual(gltf.animations.map(c=>c.name).sort(),limbsMode?['Arms','Curious','Greeting','Idle','Legs','Smile','Steps']:performanceMode?['Curious','Greeting','Idle','Smile']:['Blink','Idle','Look','Nod','Wave']);
const meshes=[];gltf.scene.traverse(o=>{if(o.isMesh)meshes.push(o);});
function snapshot(){gltf.scene.updateMatrixWorld(true);for(const m of meshes)if(m.skeleton)m.skeleton.update();const points=[];for(const m of meshes){const count=m.geometry.attributes.position.count;for(let i=0;i<count;i+=Math.max(1,Math.floor(count/160))){const p=m.getVertexPosition(i,new THREE.Vector3()).applyMatrix4(m.matrixWorld);assert.ok(p.toArray().every(Number.isFinite));points.push(p);}}return points;}
const distance=(a,b)=>Math.max(...a.map((p,i)=>p.distanceTo(b[i])));
const report={clips:{},transitions:[]};
for(const clip of gltf.animations){
  const mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();mixer.setTime(0);const start=snapshot();
  let maximum=0;for(let i=1;i<=16;i++){mixer.setTime(clip.duration*i/16);maximum=Math.max(maximum,distance(start,snapshot()));}
  mixer.setTime(clip.duration);const seam=distance(start,snapshot());assert.ok(seam<1e-4,clip.name+' loop seam '+seam);assert.ok(maximum>.0001,clip.name+' is static');
  report.clips[clip.name]={duration:clip.duration,maxMotion:maximum,seam};mixer.stopAllAction();mixer.uncacheRoot(gltf.scene);
}
const playback=new LuluPlayback(gltf.scene,gltf.animations);playback.play('Idle');playback.update(.9);
for(const name of limbsMode?['Arms','Legs','Steps','Arms','Idle']:performanceMode?['Greeting','Smile','Curious','Greeting','Idle']:['Wave','Look','Nod','Blink','Idle']){playback.update(.08);const before=snapshot();playback.play(name);playback.update(0);const jump=distance(before,snapshot());assert.ok(jump<1e-5,'Switch pose jump: '+name+' '+jump);report.transitions.push({to:name,jump});}
playback.play(limbsMode?'Steps':performanceMode?'Greeting':'Nod');for(let i=0;i<480;i++)playback.update(1/60);assert.equal(playback.selected,'Idle');
if(performanceMode||limbsMode){
  const iris=meshes.find(m=>m.morphTargetDictionary?.GazeRight!==undefined),mouth=meshes.find(m=>m.morphTargetDictionary?.Smile!==undefined);
  const value=(m,name)=>m.morphTargetInfluences[m.morphTargetDictionary[name]];
  playback.seek('Greeting',.5);const gaze=value(iris,'GazeRight'),earlySmile=value(mouth,'Smile');
  playback.seek('Greeting',2.3);const smile=value(mouth,'Smile');
  assert.ok(gaze>.5&&earlySmile<.01&&smile>.9,'Gaze and smile must have separate performance beats');
  report.performance={earlyGaze:gaze,earlySmile,heldSmile:smile};
}
if(limbsMode){
  const spec=JSON.parse(await readFile(new URL('./review/sketchfab-lulu/limbs-v1-spec.json',import.meta.url),'utf8'));
  playback.seek('Idle',0);const pose=new LimbPose(gltf.scene,spec.controls),rest=snapshot();report.joints={};
  for(const control of spec.controls){
    pose.reset();pose.set(control.name,control.limit);const motion=distance(rest,snapshot());
    assert.ok(motion>.001,control.name+' does not deform the mesh');report.joints[control.name]=motion;
  }
  pose.reset();assert.ok(distance(rest,snapshot())<1e-6,'Manual joint reset must restore pose');
}
await writeFile(new URL('./review/sketchfab-lulu/'+(limbsMode?'limbs-v1-check.json':performanceMode?'performance-v1-check.json':'motion-v1-check.json'),import.meta.url),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
