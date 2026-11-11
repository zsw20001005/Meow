import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';
import {createLulu} from './rig.mjs';
import {Locomotion} from './locomotion.mjs';

const $=s=>document.querySelector(s),viewport=$('#viewport');
const scene=new THREE.Scene();scene.background=new THREE.Color('#eee9df');scene.fog=new THREE.Fog('#eee9df',12,30);
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.VSMShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1;viewport.appendChild(renderer.domElement);
const camera=new THREE.PerspectiveCamera(34,1,.05,100);camera.position.set(2.8,2.6,7.8);
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,1.7,0);controls.enableDamping=true;controls.dampingFactor=.08;controls.minDistance=4.5;controls.maxDistance=12;controls.maxPolarAngle=Math.PI*.51;controls.minPolarAngle=.25;controls.enablePan=false;
scene.add(new THREE.HemisphereLight('#fff7e8','#bbad8f',1.4));
const key=new THREE.DirectionalLight('#fff7ea',2.5);key.position.set(-3.5,7,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-4,right:4,top:5,bottom:-3,near:.5,far:18});key.shadow.bias=-.0004;key.shadow.normalBias=.018;key.shadow.radius=4;scene.add(key);scene.add(key.target);
const rim=new THREE.DirectionalLight('#ffffff',1.1);rim.position.set(4,5,-4);scene.add(rim);
const fill=new THREE.DirectionalLight('#e1edff',.55);fill.position.set(4,2,4);scene.add(fill);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(180,180),new THREE.MeshStandardMaterial({color:'#e8e0d0',roughness:.91}));floor.rotation.x=-Math.PI/2;floor.position.y=-.006;floor.receiveShadow=true;scene.add(floor);
const grid=new THREE.GridHelper(160,160,'#d1c6b3','#d9d0bf');grid.position.y=-.004;grid.material.transparent=true;grid.material.opacity=.20;scene.add(grid);
const rig=createLulu();scene.add(rig.model);scene.add(rig.helper);const gait=new Locomotion();rig.pose(gait);
const markers=gait.feet.map(()=>{const m=new THREE.Mesh(new THREE.RingGeometry(.09,.13,40),new THREE.MeshBasicMaterial({color:'#639b69',side:THREE.DoubleSide,transparent:true,opacity:.8}));m.rotation.x=-Math.PI/2;m.position.y=.003;m.visible=false;scene.add(m);return m;});
const resize=()=>{const {width,height}=viewport.getBoundingClientRect();renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();};new ResizeObserver(resize).observe(viewport);resize();
let paused=false,previous=performance.now(),frames=0,lastZ=0;
const view=(name)=>{const z=gait.z;const positions={front:[0,2.05,8.4],side:[-8,2.5,.3],back:[0,2.6,-8.4],default:[2.8,2.6,7.8]};camera.position.set(...positions[name]);camera.position.z+=z;controls.target.set(0,1.7,z);controls.update();document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));};
$('#reset-view').onclick=()=>view('default');document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));
$('#walk').onclick=()=>{gait.walk=!gait.walk;$('#walk').innerHTML=gait.walk?'慢慢停下 <span>Ⅱ</span>':'开始走路 <span>→</span>';};
$('#pause').onclick=()=>{paused=!paused;$('#pause').textContent=paused?'继续':'暂停';};
$('#speed').oninput=e=>{gait.speed=+e.target.value;$('#speed-value').textContent=gait.speed.toFixed(1)+'×';};
$('#bones').onchange=e=>rig.helper.visible=e.target.checked;
$('#contacts').onchange=e=>markers.forEach(m=>m.visible=e.target.checked);
function bakeWalk(){
  const walk=new Locomotion(),times=[],nodes=[rig.model,...rig.skeleton.bones],values=nodes.map(()=>({position:[],quaternion:[],scale:[]}));
  walk.walk=true;
  for(let i=0;i<=360;i++){if(i>0)walk.update(1/60);if(i===240)walk.walk=false;rig.pose(walk);times.push(i/60);nodes.forEach((n,j)=>{values[j].position.push(...n.position.toArray());values[j].quaternion.push(...n.quaternion.toArray());values[j].scale.push(...n.scale.toArray());});}
  const tracks=[];nodes.forEach((n,j)=>{tracks.push(new THREE.VectorKeyframeTrack(n.name+'.position',times,values[j].position),new THREE.QuaternionKeyframeTrack(n.name+'.quaternion',times,values[j].quaternion),new THREE.VectorKeyframeTrack(n.name+'.scale',times,values[j].scale));});
  return new THREE.AnimationClip('Walk_then_settle',6,tracks);
}
$('#export').onclick=async()=>{
  const btn=$('#export');btn.disabled=true;btn.textContent='正在导出…';const wasPaused=paused;paused=true;
  try {const animation=bakeWalk();rig.skeleton.pose();rig.model.position.z=0;rig.model.updateMatrixWorld(true);const data=await new GLTFExporter().parseAsync(rig.model,{binary:true,onlyVisible:false,animations:[animation]});const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([data],{type:'model/gltf-binary'}));a.download='zhang-lulu-rig-prototype.glb';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);rig.pose(gait);}
  catch(error){console.error(error);btn.textContent='导出失败，请重试';}
  finally{paused=wasPaused;btn.disabled=false;btn.textContent='下载骨骼模型 .glb';}
};
$('#check-contact').onclick=()=>{
  const probe=new Locomotion();probe.walk=true;let slip=0,penetration=0,hover=0,last=[null,null];
  const meshes=rig.model.children.filter(n=>n.isSkinnedMesh),feet=[[],[]];
  meshes.forEach(mesh=>{const skin=mesh.geometry.attributes.skinIndex;for(let i=0;i<skin.count;i++)for(let j=0;j<2;j++)if(skin.getX(i)===rig.bones['ankle_'+(j?'R':'L')].index)feet[j].push({mesh,index:i});});
  for(let i=0;i<360;i++){probe.update(1/60);rig.pose(probe);rig.skeleton.update();
    for(let j=0;j<2;j++){let min=Infinity;for(const p of feet[j]){const v=new THREE.Vector3().fromBufferAttribute(p.mesh.geometry.attributes.position,p.index);p.mesh.applyBoneTransform(p.index,v);v.applyMatrix4(p.mesh.matrixWorld);min=Math.min(min,v.y);}penetration=Math.max(penetration,-min);if(probe.feet[j].grounded)hover=Math.max(hover,min);
      const ankle=rig.bones['ankle_'+(j?'R':'L')].getWorldPosition(new THREE.Vector3());if(last[j]?.grounded&&probe.feet[j].grounded)slip=Math.max(slip,ankle.distanceTo(last[j].position));last[j]={position:ankle,grounded:probe.feet[j].grounded};
    }
  }
  rig.pose(gait);rig.skeleton.update();
  $('#contact-result').textContent=`已检查 6 秒行走：落地滑移 ${(slip*1000).toFixed(3)} mm，最低穿地 ${(penetration*1000).toFixed(3)} mm，落地间隙 ${(hover*1000).toFixed(3)} mm（模型单位按米）。`;
};
function tick(now){const dt=Math.min((now-previous)/1000,.05);previous=now;if(!paused){gait.update(dt);rig.pose(gait);}const dz=gait.z-lastZ;lastZ=gait.z;camera.position.z+=dz;controls.target.z=gait.z;key.position.z=5+gait.z;key.target.position.set(0,1.3,gait.z);rim.position.z=-4+gait.z;fill.position.z=4+gait.z;controls.update();markers.forEach((m,i)=>{const f=gait.feet[i];m.position.set(f.x,.003,f.z+.10);m.material.color.set(f.grounded?'#639b69':'#d9a459');});$('#status').textContent=paused?'暂停 · 可旋转查看':gait.walk?'一步一步，稳稳走':gait.swing||gait.velocity>.001?'收步站稳':'自在站立';renderer.render(scene,camera);if(++frames===2)$('#loading').remove();requestAnimationFrame(tick);}
requestAnimationFrame(tick);
