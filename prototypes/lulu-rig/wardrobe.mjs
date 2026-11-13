import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {createLulu} from './rig.mjs';
import {createWardrobe,defaults,normalizeOutfit} from './wardrobe-assets.mjs';
import {WardrobeMotion} from './wardrobe-motion.mjs';

const $=s=>document.querySelector(s),viewport=$('#viewport');
const names={idle:'自在站立',walk:'慢慢走一走',wave:'向你挥挥手',stretch:'伸一个大懒腰',spin:'转身看看搭配'};
try {
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;viewport.appendChild(renderer.domElement);
  const scene=new THREE.Scene();scene.background=new THREE.Color('#eeeee4');scene.fog=new THREE.Fog('#eeeee4',12,24);
  const camera=new THREE.PerspectiveCamera(32,1,.05,60);camera.position.set(0,2.1,8.7);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,1.7,0);controls.enableDamping=true;controls.enablePan=false;controls.minDistance=5.5;controls.maxDistance=11;controls.minPolarAngle=.45;controls.maxPolarAngle=Math.PI*.51;
  scene.add(new THREE.HemisphereLight('#fffaec','#c8cbb4',2.0));
  const key=new THREE.DirectionalLight('#fff6e6',2.8);key.position.set(-3,6,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-4,right:4,top:5,bottom:-3,near:.5,far:18});key.shadow.normalBias=.015;key.shadow.bias=-.0002;key.shadow.radius=4;scene.add(key,key.target);
  const fill=new THREE.DirectionalLight('#e3efff',1.1);fill.position.set(4,3,3);scene.add(fill);
  const rim=new THREE.DirectionalLight('#ffffff',1.4);rim.position.set(2,5,-4);scene.add(rim);
  const floor=new THREE.Mesh(new THREE.PlaneGeometry(160,160),new THREE.MeshStandardMaterial({color:'#eeeee4',roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;floor.receiveShadow=true;scene.add(floor);
  const rig=createLulu({wardrobe:true}),wardrobe=createWardrobe(rig),motion=new WardrobeMotion(rig);scene.add(rig.model);
  let config={...defaults},paused=false;
  try {const saved=localStorage.getItem('meow.wardrobe.preview.v1');if(saved)config=normalizeOutfit(JSON.parse(saved));} catch {$('#notice').textContent='未读取到搭配，已使用默认款。';}
  function apply() {
    config=wardrobe.apply(config);
    document.querySelectorAll('[data-top]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.top===config.top));
    document.querySelectorAll('[data-color]').forEach(b=>{b.setAttribute('aria-pressed',b.dataset.color===config.color);b.disabled=config.top==='none';});
    $('#color-name').textContent={cream:'奶油白',sage:'鼠尾草绿',blue:'晴空蓝',rose:'莓果粉'}[config.color];
    for(const id of ['glasses','shorts'])$('#'+id).value=config[id];
    for(const id of ['bag','charm'])$('#'+id).checked=config[id];
  }
  apply();
  document.querySelectorAll('[data-top]').forEach(b=>b.onclick=()=>{config.top=b.dataset.top;apply();});
  document.querySelectorAll('[data-color]').forEach(b=>b.onclick=()=>{config.color=b.dataset.color;apply();});
  for(const id of ['glasses','shorts'])$('#'+id).onchange=e=>{config[id]=e.target.value;apply();};
  for(const id of ['bag','charm'])$('#'+id).onchange=e=>{config[id]=e.target.checked;apply();};
  $('#save').onclick=()=>{try {localStorage.setItem('meow.wardrobe.preview.v1',JSON.stringify(config));$('#notice').textContent='搭配已保存，下次打开预览会自动穿上。';}catch {$('#notice').textContent='浏览器没有允许保存；当前搭配仍可预览。';}};
  $('#reset').onclick=()=>{config={...defaults};apply();$('#notice').textContent='已恢复默认搭配；点击保存后替换已存搭配。';};
  function updateActionButtons(){document.querySelectorAll('[data-action]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.action===motion.action));$('#motion-status').textContent=paused?'动作已暂停':names[motion.action];}
  document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>{motion.setAction(b.dataset.action);updateActionButtons();});updateActionButtons();
  $('#pause').onclick=()=>{paused=!paused;$('#pause').textContent=paused?'继续动作':'暂停动作';$('#pause').setAttribute('aria-pressed',paused);updateActionButtons();};
  document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{const z=motion.gait.z;const p={front:[0,2.1,8.7],side:[8.7,2.3,0],back:[0,2.3,-8.7]}[b.dataset.view];camera.position.set(...p);camera.position.z+=z;controls.target.set(0,1.7,z);controls.update();document.querySelectorAll('[data-view]').forEach(v=>v.setAttribute('aria-pressed',v===b));});
  controls.addEventListener('start',()=>document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed','false')));
  const resize=()=>{const {width,height}=viewport.getBoundingClientRect();renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();};new ResizeObserver(resize).observe(viewport);resize();
  let previous=performance.now(),lastZ=0;
  function frame(now) {
    const dt=Math.min((now-previous)/1000,.05);previous=now;
    if(!paused)motion.update(dt);
    const z=motion.gait.z,dz=z-lastZ;lastZ=z;camera.position.z+=dz;controls.target.z=z;key.position.z=5+z;key.target.position.set(0,1.3,z);fill.position.z=3+z;rim.position.z=-4+z;
    controls.update();renderer.render(scene,camera);requestAnimationFrame(frame);
  }
  motion.update(0);$('#loading').remove();requestAnimationFrame(frame);
} catch(error) {$('#loading').textContent='无法启动 3D 预览，请使用开启硬件加速的桌面浏览器。';$('#notice').textContent=error.message;console.error(error);}
