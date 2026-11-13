import * as THREE from 'three';

export function bindPose(scene) {
  const skeletons=new Set();scene.traverse(o=>{if(o.isSkinnedMesh)skeletons.add(o.skeleton);});
  for(const s of skeletons)s.pose();scene.updateMatrixWorld(true);
  const bones=new Map();for(const s of skeletons)for(const b of s.bones)bones.set(b.name,b);
  return new Map([...bones].map(([name,b])=>[name,{position:b.position.clone(),quaternion:b.quaternion.clone(),scale:b.scale.clone(),parent:b.parent?.isBone?b.parent.name:null}]));
}

// Relative-to-bind transfer preserves each character's own proportions.
// This is only verified for this source family, not arbitrary humanoid rigs.
export function retarget(clips, source, target) {
  const ratios=[];
  for(const [name,s] of source){const t=target.get(name);if(!t||t.parent!==s.parent)throw new Error('不兼容的骨骼：'+name);if(s.position.length()>.05)ratios.push(t.position.length()/s.position.length());}
  ratios.sort((a,b)=>a-b);const ratio=ratios[Math.floor(ratios.length/2)];
  const converted=clips.map(clip=>new THREE.AnimationClip(clip.name,clip.duration,clip.tracks.map(track=>{
    const {nodeName,propertyName}=THREE.PropertyBinding.parseTrackName(track.name);
    const s=source.get(nodeName),t=target.get(nodeName);if(!s||!t)throw new Error('动作包含未知关节：'+nodeName);
    const next=track.clone(),n=next.getValueSize();
    if(propertyName==='quaternion'){
      const q=new THREE.Quaternion(),inverse=s.quaternion.clone().invert();
      for(let i=0;i<next.values.length;i+=n){q.fromArray(next.values,i).premultiply(inverse).premultiply(t.quaternion).normalize().toArray(next.values,i);}
    }else if(propertyName==='position'){
      for(let i=0;i<next.values.length;i+=n)for(let k=0;k<3;k++)next.values[i+k]=t.position.getComponent(k)+(next.values[i+k]-s.position.getComponent(k))*ratio;
    }else if(propertyName==='scale'){
      for(let i=0;i<next.values.length;i+=n)for(let k=0;k<3;k++)next.values[i+k]*=t.scale.getComponent(k)/s.scale.getComponent(k);
    }else throw new Error('不支持的动作通道：'+propertyName);
    return next;
  })));
  return {clips:converted,ratio};
}

export class SharedPlayback {
  constructor(scene,clips){this.mixer=new THREE.AnimationMixer(scene);this.actions=new Map(clips.map(c=>[c.name,this.mixer.clipAction(c)]));this.selected=null;this.fade=null;}
  play(name){
    if(!this.actions.has(name))throw new Error('缺少动作：'+name);
    const old=new Map([...this.actions].map(([n,a])=>[n,a.isScheduled()?a.getEffectiveWeight():0]));
    const next=this.actions.get(name);if(!next.isScheduled()||next.paused)next.reset();
    next.setEffectiveWeight(this.selected?old.get(name):1).setLoop(THREE.LoopRepeat,Infinity).play();
    this.fade={old,time:this.selected?0:.35};this.selected=name;this.update(0);
  }
  update(dt){
    if(this.fade){this.fade.time+=dt;const t=Math.min(this.fade.time/.35,1),s=t*t*(3-2*t);for(const[n,a]of this.actions){a.setEffectiveWeight((this.fade.old.get(n)||0)*(1-s)+(n===this.selected?s:0));if(t===1&&n!==this.selected)a.stop();}if(t===1)this.fade=null;}
    this.mixer.update(dt);
  }
}
