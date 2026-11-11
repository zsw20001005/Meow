// World-space foot targets. A planted foot never follows the moving pelvis.
export class Locomotion {
  constructor() { this.reset(); }
  reset() {
    this.z=0; this.velocity=0; this.time=0; this.walk=false; this.speed=1;
    this.feet=[{x:-.31,y:.14,z:0,grounded:true},{x:.31,y:.14,z:0,grounded:true}];
    this.swing=null; this.next=0; this.contactTime=0; this.bob=0; this.sway=0;
  }
  update(dt) {
    for(let left=Math.min(Math.max(dt,0),.1);left>1e-9;) {const h=Math.min(left,1/120);this.advance(h);left-=h;}
    return this;
  }
  advance(dt) {
    this.time+=dt;
    const speed=Math.max(.5,Math.min(1.4,this.speed));
    const target=this.walk?.23*speed:0;
    this.velocity+=(target-this.velocity)*(1-Math.exp(-dt/.24));
    if(!this.walk&&this.velocity<.0001)this.velocity=0;
    this.z+=this.velocity*dt;
    if(this.swing) {
      const s=this.swing,f=this.feet[s.index];s.age+=dt;
      const u=Math.min(1,s.age/s.duration),ease=u*u*u*(10+u*(-15+6*u));
      f.z=s.from+(s.to-s.from)*ease;
      f.y=.14+.065*Math.sin(Math.PI*u)**2;
      f.pitch=.13*Math.sin(2*Math.PI*u)*Math.sin(Math.PI*u)**2;
      if(u>=1){f.z=s.to;f.y=.14;f.pitch=0;f.grounded=true;this.swing=null;this.contactTime=.07/speed;this.next=1-s.index;}
    } else this.contactTime=Math.max(0,this.contactTime-dt);
    if(!this.swing&&this.contactTime<=0) {
      let index=this.next;
      const settling=!this.walk&&this.velocity<.015;
      if(settling) { if(Math.abs(this.z-this.feet[1-index].z)>Math.abs(this.z-this.feet[index].z))index=1-index; }
      else if(this.z-this.feet[1-index].z>this.z-this.feet[index].z+.025)index=1-index;
      const lag=this.z-this.feet[index].z;
      if((!settling&&lag>.055)||(settling&&Math.abs(lag)>.008)) {
        const duration=(settling?.38:.43)/speed;
        const to=settling?this.z:this.z+this.velocity*duration*.75+.022;
        this.swing={index,from:this.feet[index].z,to,age:0,duration};this.feet[index].grounded=false;
      }
    }
    const u=this.swing?Math.min(1,this.swing.age/this.swing.duration):0;
    const motion=Math.sin(Math.PI*u)**2;
    this.bob=-.013*motion;
    const desired=this.swing?(this.swing.index===0?.022:-.022):0;
    this.sway+=(desired-this.sway)*(1-Math.exp(-dt/.15));
  }
}
