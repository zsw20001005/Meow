import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {LuluPlayback} from './motion-playback.mjs';
import {addLimbControls} from './limb-controls.mjs';
const $=s=>document.querySelector(s),stage=$('#stage');
const performanceMode=new URLSearchParams(location.search).get('mode')==='performance';
const limbsMode=new URLSearchParams(location.search).get('mode')==='limbs';
const humanMode=new URLSearchParams(location.search).get('mode')==='human';
const names=humanMode?{Idle:'站立放松',HumanWave:'抬手招呼',HumanSteps:'交替抬腿'}:limbsMode?{Idle:'放松待机',Arms:'双臂活动',Legs:'左右屈膝',Steps:'交替抬脚',Greeting:'表情与打招呼'}:performanceMode?{Idle:'放松待机',Greeting:'注意到你，开心打招呼',Smile:'微笑表情',Curious:'好奇表情'}:{Idle:'自在呼吸',Blink:'眨眨眼',Nod:'点点头',Look:'左右看看',Wave:'向你轻挥手'};
if(performanceMode||limbsMode||humanMode){
  document.title=humanMode?'张噜噜 · 完整动作试验':limbsMode?'张噜噜 · 四肢关节':'张噜噜 · 表演样片';$('h1').textContent=document.title;
  const bar=document.querySelector('.bar[aria-label="动作"]');bar.replaceChildren();
  for(const [name,label] of Object.entries(names)){const b=document.createElement('button');b.dataset.action=name;b.textContent=label;b.disabled=true;bar.append(b);}
}
try {
  const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.shadowMap.enabled=humanMode;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;stage.prepend(renderer.domElement);
  const scene=new THREE.Scene();scene.background=new THREE.Color('#ebe6dc');
  const camera=new THREE.PerspectiveCamera(32,1,.05,40);camera.position.set(0,1.8,7.4);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,1.5,0);controls.enableDamping=true;controls.minDistance=4.3;controls.maxDistance=10;controls.enablePan=false;
  scene.add(new THREE.HemisphereLight(0xfff8ed,0xc9bda7,2));
  for(const [pos,power,color] of [[[-3,6,5],2.5,0xfff5e5],[[4,3,4],1.1,0xe7f0ff],[[1,5,-4],1.3,0xffffff]]){const l=new THREE.DirectionalLight(color,power);l.position.set(...pos);if(humanMode&&pos[0]<0){l.castShadow=true;l.shadow.mapSize.set(1024,1024);l.shadow.normalBias=.02;}scene.add(l);}
  const floor=new THREE.Mesh(new THREE.CircleGeometry(2.1,80),new THREE.MeshStandardMaterial({color:'#ded5c5',roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.018;floor.receiveShadow=humanMode;scene.add(floor);
  const gltf=await new GLTFLoader().loadAsync('./review/sketchfab-lulu/'+(humanMode?'lulu-limbs-v2.glb':limbsMode?'lulu-limbs-v1.glb':performanceMode?'lulu-performance-v1.glb':'lulu-motion-v1.glb'));scene.add(gltf.scene);
  if(humanMode)gltf.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
  let paused=false,previous=performance.now();
  const refresh=()=>{document.querySelectorAll('[data-action]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.action===playback.selected)));$('#status').textContent=paused?'已暂停':names[playback.selected];};
  const playback=new LuluPlayback(gltf.scene,gltf.animations,refresh);
  let limbControls,demoCheckbox,demoIndex=1;
  if(humanMode){
    const row=document.createElement('div');row.className='bar';const label=document.createElement('label');demoCheckbox=document.createElement('input');demoCheckbox.type='checkbox';demoCheckbox.checked=true;label.append(demoCheckbox,' 连续演示完整动作');row.append(label);
    const replay=document.createElement('button');replay.textContent='重播当前动作';replay.onclick=()=>{playback.seek(playback.selected==='Idle'?'HumanWave':playback.selected,0);paused=false;$('#pause').textContent='暂停';$('#pause').setAttribute('aria-pressed','false');refresh();};row.append(replay);document.querySelector('footer').before(row);
  }
  if(limbsMode){
    const response=await fetch('./review/sketchfab-lulu/limbs-v1-spec.json');if(!response.ok)throw new Error('关节配置加载失败');const spec=await response.json();
    limbControls=addLimbControls({root:gltf.scene,scene,controls:spec.controls,beginManual:()=>{paused=true;playback.seek('Idle',0);$('#pause').textContent='继续';$('#pause').setAttribute('aria-pressed','true');refresh();}});
  }
  for(const name of Object.keys(names))if(!playback.actions.has(name))throw new Error('缺少动作：'+name);
  for(const b of document.querySelectorAll('[data-action]')){b.disabled=false;b.onclick=()=>{limbControls?.exitManual();if(demoCheckbox)demoCheckbox.checked=false;paused=false;$('#pause').textContent='暂停';$('#pause').setAttribute('aria-pressed','false');playback.play(b.dataset.action);refresh();};}
  $('#pause').disabled=false;$('#pause').onclick=()=>{if(paused)limbControls?.exitManual();paused=!paused;$('#pause').textContent=paused?'继续':'暂停';$('#pause').setAttribute('aria-pressed',String(paused));refresh();};
  let scrub;
  if(performanceMode){
    const row=document.createElement('div');row.className='bar';
    const replay=document.createElement('button');replay.textContent='重播完整表演';replay.onclick=()=>{playback.seek('Greeting',0);paused=false;$('#pause').textContent='暂停';$('#pause').setAttribute('aria-pressed','false');refresh();};row.append(replay);
    const label=document.createElement('label');label.textContent='逐帧检查 ';scrub=document.createElement('input');scrub.type='range';scrub.min=0;scrub.max=6;scrub.step=1/30;scrub.value=0;scrub.setAttribute('aria-label','打招呼表演时间');label.append(scrub);row.append(label);
    scrub.oninput=()=>{paused=true;playback.seek('Greeting',Number(scrub.value));$('#pause').textContent='继续';$('#pause').setAttribute('aria-pressed','true');refresh();};
    const old=document.createElement('a');old.href='motion.html';old.textContent='上一版对照';row.append(old);document.querySelector('footer').before(row);
  }
  for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>{camera.position.set(...({front:[0,1.8,7.4],quarter:[3.5,2,6.6],side:[7.4,1.8,0]}[b.dataset.view]));controls.target.set(0,1.5,0);controls.update();};
  const resize=()=>{const {width,height}=stage.getBoundingClientRect();renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();};new ResizeObserver(resize).observe(stage);resize();
  playback.play(humanMode?'HumanWave':limbsMode?'Arms':performanceMode?'Greeting':'Idle');$('#loading').remove();
  function frame(now){const dt=Math.min((now-previous)/1000,.05);previous=now;if(!paused&&!document.hidden){playback.update(dt*Number($('#speed').value));if(demoCheckbox?.checked&&playback.selected==='Idle'&&playback.actions.get('Idle').time>1){playback.play(['HumanWave','HumanSteps'][demoIndex++%2]);}}if(scrub&&!paused&&playback.selected==='Greeting')scrub.value=playback.actions.get('Greeting').time;controls.update();renderer.render(scene,camera);requestAnimationFrame(frame);}requestAnimationFrame(frame);
} catch(error){$('#loading').textContent='预览未能加载：'+error.message;$('#status').textContent='加载失败';console.error(error);}
