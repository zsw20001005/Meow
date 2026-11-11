import assert from 'node:assert/strict';
import {Locomotion} from './locomotion.mjs';
const gait=new Locomotion();gait.walk=true;
let maxSlip=0,maxStep=0,maxReach=0,steps=0;
for(let i=0;i<60*24;i++) {
  if(i===600)gait.walk=false;if(i===900){gait.walk=true;gait.speed=1.4;}
  const previous=gait.feet.map(f=>({...f}));gait.update(1/60);
  gait.feet.forEach((f,j)=>{
    if(f.grounded&&previous[j].grounded)maxSlip=Math.max(maxSlip,Math.abs(f.z-previous[j].z));
    if(f.grounded&&!previous[j].grounded)steps++;
    maxStep=Math.max(maxStep,Math.hypot(f.y-previous[j].y,f.z-previous[j].z));
    maxReach=Math.max(maxReach,Math.hypot(.53+gait.bob-f.y,gait.z-f.z));
    assert(f.y>=.14-1e-9,'foot target penetrated floor');
  });
  if(i===899)assert(gait.feet.every(f=>f.grounded&&Math.abs(f.z-gait.z)<.009),'stop must finish both feet under body');
}
assert(maxSlip<1e-9,'planted foot slipped in world space');
assert(maxStep<.035,'foot position jumped between 60 Hz samples');
assert(maxReach<.44,'target unreachable by two 0.22-unit leg bones');
assert(steps>15,'continuous walking did not alternate enough steps');
console.log(JSON.stringify({passed:true,steps,maxPlantedFootSlip:maxSlip,maxFrameFootDisplacement:maxStep,maxLegReach:maxReach},null,2));
