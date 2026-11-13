import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {bindPose,retarget,SharedPlayback} from './shared-rig.mjs';
const host=document.querySelector('#stage'),status=document.querySelector('#status');
const scene=new THREE.Scene();scene.background=new THREE.Color('#eeeae1');
const camera=new THREE.PerspectiveCamera(34,1,.1,100);camera.position.set(0,3.1,11);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;host.prepend(renderer.domElement);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.target.set(0,1.5,0);orbit.enableDamping=true;orbit.minDistance=5;orbit.maxDistance=16;orbit.maxPolarAngle=Math.PI*.52;
scene.add(new THREE.HemisphereLight(0xfff6e6,0x8e9a85,2.1));
const key=new THREE.DirectionalLight(0xfff8ed,3);key.position.set(-4,7,6);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-5,right:5,top:5,bottom:-5});key.shadow.normalBias=.025;scene.add(key);
const rim=new THREE.DirectionalLight(0xdcecff,1.6);rim.position.set(5,4,-3);scene.add(rim);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(80,80),new THREE.MeshStandardMaterial({color:'#eeeae1',roughness:1}));floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;scene.add(floor);
const actors=[],loader=new GLTFLoader();let paused=false,ready=false;
for(const b of document.querySelectorAll('button'))b.disabled=true;
try{
  const [panda,rabbit,motions]=await Promise.all(['Panda.glb','Rabbit_Pink.glb','shared-motions.glb'].map(f=>loader.loadAsync('/assets/runtime/'+f)));
  const reference=bindPose(panda.scene);
  for(const[name,gltf,x]of[['Panda',panda,-1.6],['Rabbit',rabbit,1.6]]){
    const rest=bindPose(gltf.scene),{clips}=retarget(motions.animations,reference,rest),playback=new SharedPlayback(gltf.scene,clips);playback.play('Idle');playback.update(0);
    const box=new THREE.Box3().setFromObject(gltf.scene,true),scale=3/(box.max.y-box.min.y);
    const display=new THREE.Group();display.add(gltf.scene);gltf.scene.scale.multiplyScalar(scale);gltf.scene.position.y-=box.min.y*scale;display.position.x=x;scene.add(display);
    gltf.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;for(const mat of Array.isArray(o.material)?o.material:[o.material]){mat.roughness=.7;mat.metalness=0;}}});
    const helper=new THREE.SkeletonHelper(gltf.scene);helper.visible=false;scene.add(helper);actors.push({name,display,playback,helper});
  }
  status.textContent='熊猫与兔子正在播放同一份动作数据 · 43 个骨骼节点';ready=true;for(const b of document.querySelectorAll('button'))b.disabled=false;
}catch(e){status.textContent='加载失败：'+e.message;console.error(e);}
document.querySelector('#actions').onclick=e=>{const name=e.target.dataset.action;if(!name||!ready)return;actors.forEach(a=>a.playback.play(name));document.querySelectorAll('[data-action]').forEach(b=>b.classList.toggle('active',b.dataset.action===name));};
document.querySelector('#pause').onclick=e=>{paused=!paused;e.target.textContent=paused?'继续':'暂停';};
document.querySelector('#character').onchange=e=>{for(const a of actors){a.display.visible=e.target.value==='both'||a.name===e.target.value;a.display.position.x=e.target.value==='both'?(a.name==='Panda'?-1.6:1.6):0;}};
document.querySelector('#bones').onchange=e=>actors.forEach(a=>a.helper.visible=e.target.checked&&a.display.visible);
new ResizeObserver(()=>{camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();renderer.setSize(host.clientWidth,host.clientHeight);}).observe(host);
const clock=new THREE.Clock();renderer.setAnimationLoop(()=>{const dt=Math.min(clock.getDelta(),.05);if(!paused)actors.forEach(a=>a.playback.update(dt*Number(document.querySelector('#speed').value)));actors.forEach(a=>a.helper.visible=document.querySelector('#bones').checked&&a.display.visible);orbit.update();renderer.render(scene,camera);});
