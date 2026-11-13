import assert from 'node:assert/strict';
import * as THREE from 'three';
import {createLulu} from './rig.mjs';
import {createWardrobe,defaults,normalizeOutfit} from './wardrobe-assets.mjs';
import {WardrobeMotion,actions} from './wardrobe-motion.mjs';

const rig=createLulu({wardrobe:true,texture:false}),wardrobe=createWardrobe(rig),motion=new WardrobeMotion(rig);
assert.equal(normalizeOutfit(null).top,'tee');
assert.deepEqual(normalizeOutfit({top:'remote-script',color:'not-a-color',bag:'true',glasses:'broken'}),defaults);
for(const mesh of wardrobe.meshes) {
  assert.equal(mesh.skeleton,rig.skeleton,'garment must use the original skeleton');
  const ids=mesh.geometry.attributes.skinIndex,weights=mesh.geometry.attributes.skinWeight;
  for(let i=0;i<ids.count;i++) {let sum=0;for(let j=0;j<4;j++){const id=ids.getComponent(i,j);assert(id>=0 && id<rig.skeleton.bones.length);sum+=weights.getComponent(i,j);}assert(Math.abs(sum-1)<1e-6);}
}
console.log('PASS every garment uses the same skeleton, valid joints and normalized weights');
function vertex(mesh,index) {const v=new THREE.Vector3().fromBufferAttribute(mesh.geometry.attributes.position,index);mesh.applyBoneTransform(index,v);return mesh.localToWorld(v);}
motion.update(0);
const sleeve=wardrobe.outfits.tee.find(m=>m.name==='tee-sleeve-R'),samples=Array.from({length:20},(_,i)=>Math.floor(i/20*sleeve.geometry.attributes.position.count)),rest=samples.map(i=>vertex(sleeve,i));
motion.setAction('wave');for(let i=0;i<60;i++)motion.update(1/60);
assert(Math.max(...samples.map((i,j)=>vertex(sleeve,i).distanceTo(rest[j])))>.3,'sleeve must deform with a raised arm');
const before=rig.skeleton.bones.map(b=>b.matrixWorld.toArray()),age=motion.age;
wardrobe.apply({...defaults,top:'sweater',bag:true,charm:true,glasses:'none'});
assert.equal(motion.age,age);assert.deepEqual(rig.skeleton.bones.map(b=>b.matrixWorld.toArray()),before);
assert.equal(wardrobe.outfits.tee.every(m=>!m.visible),true);assert.equal(wardrobe.outfits.sweater.every(m=>m.visible),true);
assert.equal(rig.meshes.filter(m=>m.userData.region==='torso').every(m=>!m.visible),true);
assert.equal(rig.meshes.filter(m=>m.material===rig.materials.glasses).every(m=>!m.visible),true);
console.log('PASS switching clothes mid-wave preserves the pose and animation time; covered torso is hidden');
for(const action of actions) {
  motion.setAction(action);
  for(let f=0;f<180;f++) {
    motion.update(1/60);
    if(f%20===0)for(const mesh of wardrobe.meshes)for(let i=0;i<mesh.geometry.attributes.position.count;i+=73)assert(vertex(mesh,i).toArray().every(Number.isFinite),action+' finite garment deformation');
    if(f%30===0) {
      const head=rig.bones.head.localToWorld(wardrobe.charm.position.clone());
      assert(head.distanceTo(wardrobe.charm.getWorldPosition(new THREE.Vector3()))<1e-8);
      const spine=rig.bones.spine.localToWorld(wardrobe.bag.position.clone());
      assert(spine.distanceTo(wardrobe.bag.getWorldPosition(new THREE.Vector3()))<1e-8);
    }
  }
}
console.log('PASS idle/walk/wave/stretch/turn keep garment vertices finite and accessories fixed to their attachment bones');
wardrobe.apply({...defaults,top:'none'});
assert.equal(rig.meshes.filter(m=>m.userData.region==='torso').every(m=>m.visible),true);
assert.equal(wardrobe.meshes.every(m=>!m.visible),true);
const legacy=createLulu({texture:false});assert.equal(legacy.meshes.length,13);
console.log('PASS undressing restores body visibility; original prototype keeps its 13 meshes');
