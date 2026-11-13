import {AnimationMixer,LoopOnce,LoopRepeat} from 'three';
export class LuluPlayback {
  constructor(root,clips,onChange=()=>{}) {
    this.mixer=new AnimationMixer(root);this.actions=new Map(clips.map(c=>[c.name,this.mixer.clipAction(c)]));
    this.selected=null;this.onChange=onChange;this.fade=null;
    this.mixer.addEventListener('finished',e=>{if(e.action===this.actions.get(this.selected)&&this.selected!=='Idle')this.play('Idle');});
  }
  play(name) {
    if(name===this.selected)return;
    const next=this.actions.get(name);if(!next)throw new Error('缺少动作：'+name);
    const from=new Map([...this.actions].map(([n,a])=>[n,a.isScheduled()?a.getEffectiveWeight():0]));
    if(!next.isScheduled()||next.paused)next.reset();
    next.setEffectiveTimeScale(1).setEffectiveWeight(from.get(name));next.clampWhenFinished=name!=='Idle';
    next.setLoop(name==='Idle'?LoopRepeat:LoopOnce,name==='Idle'?Infinity:1).play();
    const initial=this.selected===null;this.selected=name;
    this.fade={from,time:initial?.45:0};this.applyFade(0);this.onChange(name);
  }
  applyFade(dt) {
    if(!this.fade)return;
    this.fade.time+=dt;const t=Math.min(this.fade.time/.45,1),s=t*t*(3-2*t);
    for(const [n,a] of this.actions){const w=this.fade.from.get(n)*(1-s)+(n===this.selected?s:0);a.setEffectiveWeight(w);if(t===1&&n!==this.selected)a.stop();}
    if(t===1)this.fade=null;
  }
  update(dt){this.applyFade(dt);this.mixer.update(dt);}
  seek(name,time){
    const action=this.actions.get(name);if(!action)throw new Error('缺少动作：'+name);
    for(const a of this.actions.values())a.stop();
    action.reset().setEffectiveWeight(1).setEffectiveTimeScale(1).setLoop(name==='Idle'?LoopRepeat:LoopOnce,name==='Idle'?Infinity:1).play();
    action.clampWhenFinished=name!=='Idle';action.time=Math.max(0,Math.min(time,action.getClip().duration-1e-5));
    this.selected=name;this.fade=null;this.mixer.update(0);this.onChange(name);
  }
}
