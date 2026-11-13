import {Vector3,Quaternion,SkeletonHelper} from 'three';

// Share exactly the same FK operation between interactive preview and audit.
export class LimbPose {
  constructor(root,controls){
    root.updateMatrixWorld(true);this.items=new Map();
    for(const control of controls){
      let bone;root.traverse(o=>{if(o.isBone&&o.name.replaceAll('.','')===control.name.replaceAll('.',''))bone=o;});
      if(!bone)throw new Error('缺少关节：'+control.name);
      const world=new Quaternion();bone.getWorldQuaternion(world);
      // Blender X axis remains X after glTF's Z-up -> Y-up conversion.
      const axis=new Vector3(1,0,0).applyQuaternion(world.invert());
      this.items.set(control.name,{bone,base:bone.quaternion.clone(),axis,limit:control.limit});
    }
  }
  set(name,degrees){
    const item=this.items.get(name);if(!item)throw new Error('未知关节：'+name);
    const angle=Math.max(-item.limit,Math.min(item.limit,degrees))*Math.PI/180;
    item.bone.quaternion.copy(item.base).multiply(new Quaternion().setFromAxisAngle(item.axis,angle));
  }
  reset(){for(const {bone,base} of this.items.values())bone.quaternion.copy(base);}
}

export function addLimbControls({root,scene,controls,beginManual}){
  const pose=new LimbPose(root,controls),panel=document.createElement('div');panel.className='bar';
  const label=document.createElement('label');label.textContent='单关节检查 ';const select=document.createElement('select');label.append(select);panel.append(label);
  const terms={UpperArm:'肩',Forearm:'肘',Hand:'腕',Thigh:'髋',Shin:'膝',Foot:'踝'};
  for(const c of controls){const [part,side]=c.name.split('.');const o=document.createElement('option');o.value=c.name;o.textContent=(side==='L'?'左':'右')+terms[part]+(side==='L'&&['UpperArm','Forearm','Hand'].includes(part)?'（贴脸侧）':'');select.append(o);}
  const slider=document.createElement('input');slider.type='range';slider.step=1;slider.value=0;slider.setAttribute('aria-label','关节屈伸角度');panel.append(slider);
  const value=document.createElement('output');value.textContent='0°';panel.append(value);
  const values=new Map(controls.map(c=>[c.name,0]));let manual=false;
  const limits=()=>{const c=controls.find(c=>c.name===select.value);slider.min=-c.limit;slider.max=c.limit;slider.value=values.get(c.name);value.textContent=slider.value+'°';};select.onchange=limits;limits();
  slider.oninput=()=>{if(!manual){beginManual();pose.reset();manual=true;}values.set(select.value,Number(slider.value));pose.set(select.value,Number(slider.value));value.textContent=slider.value+'°';};
  const reset=document.createElement('button');reset.textContent='关节复位';reset.onclick=()=>{beginManual();pose.reset();manual=true;for(const name of values.keys())values.set(name,0);limits();};panel.append(reset);
  const helper=new SkeletonHelper(root);helper.material.depthTest=false;helper.renderOrder=10;helper.visible=false;scene.add(helper);
  const show=document.createElement('label'),checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.onchange=()=>helper.visible=checkbox.checked;show.append(checkbox,' 显示骨骼');panel.append(show);
  document.querySelector('footer').before(panel);
  return {exitManual(){manual=false;pose.reset();for(const name of values.keys())values.set(name,0);limits();}};
}
