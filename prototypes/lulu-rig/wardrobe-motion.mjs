import * as THREE from 'three';
import {Locomotion} from './locomotion.mjs';

export const actions=Object.freeze(['idle','walk','wave','stretch','spin']);
export class WardrobeMotion {
  constructor(rig) {
    this.rig=rig;this.gait=new Locomotion();this.action='idle';this.time=0;this.age=0;this.blendAge=.5;
    this.rest=rig.skeleton.bones.map(b=>({p:b.position.clone(),q:b.quaternion.clone(),s:b.scale.clone()}));
    this.from=null;
  }
  setAction(action) {
    if(!actions.includes(action))throw new Error('Unsupported preview action');
    if(action===this.action)return;
    this.from=this.rig.skeleton.bones.map(b=>b.quaternion.clone());
    this.action=action;this.age=0;this.blendAge=0;this.gait.walk=action==='walk';
  }
  update(dt) {
    dt=Math.max(0,Math.min(dt,.05));this.time+=dt;this.age+=dt;this.blendAge+=dt;
    this.gait.update(dt);
    this.rig.skeleton.bones.forEach((b,i)=>{b.position.copy(this.rest[i].p);b.quaternion.copy(this.rest[i].q);b.scale.copy(this.rest[i].s);});
    this.rig.pose(this.gait);
    const b=this.rig.bones,t=this.age,envelope=Math.min(1,t/.45);
    if(this.action==='wave') {b.shoulder_R.rotation.z=2.05*envelope;b.elbow_R.rotation.z=(.25+.20*Math.sin(t*5))*envelope;b.wrist_R.rotation.z=.16*Math.sin(t*5+.3)*envelope;b.head.rotation.z=-.05*envelope;}
    if(this.action==='stretch') {const ease=(1-Math.cos(Math.min(1,t/.9)*Math.PI))/2;b.shoulder_L.rotation.z=-2.15*ease;b.shoulder_R.rotation.z=2.15*ease;b.spine.rotation.x=-.07*ease;b.head.rotation.x=-.08*ease;}
    if(this.action==='spin') b.root.rotation.y=t<.6?Math.PI*(t*t/.6):Math.PI*(2*t-.6);
    if(this.from && this.blendAge<.35) {const u=THREE.MathUtils.smoothstep(this.blendAge,0,.35);this.rig.skeleton.bones.forEach((bone,i)=>bone.quaternion.slerpQuaternions(this.from[i],bone.quaternion.clone(),u));}
    this.rig.model.updateMatrixWorld(true);this.rig.skeleton.update();return this;
  }
}
