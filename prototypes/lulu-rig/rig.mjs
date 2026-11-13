import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';

const V=(x=0,y=0,z=0)=>new THREE.Vector3(x,y,z);
export function createLulu({wardrobe=false,texture=true}={}) {
  const model=new THREE.Group();model.name='ZhangLulu';
  const bones=[],named={};
  function bone(name,parent,x,y,z){const b=new THREE.Bone();b.name=name;b.position.set(x,y,z);(parent||model).add(b);b.index=bones.length;bones.push(b);named[name]=b;return b;}
  const root=bone('root',null,0,0,0),pelvis=bone('pelvis',root,0,.76,0),spine=bone('spine',pelvis,0,.52,0),head=bone('head',spine,0,1.06,0);
  for(const [side,sign] of [['L',-1],['R',1]]) {
    const hip=bone('hip_'+side,pelvis,sign*.31,-.18,0),knee=bone('knee_'+side,hip,0,-.22,0);bone('ankle_'+side,knee,0,-.22,0);
    const shoulder=bone('shoulder_'+side,spine,sign*.65,.38,0),elbow=bone('elbow_'+side,shoulder,sign*.13,-.36,.02);bone('wrist_'+side,elbow,0,-.31,.07);
    bone('eye_'+side,head,sign*.34,.29,.58);
  }
  model.updateMatrixWorld(true);
  const skeleton=new THREE.Skeleton(bones),parts=new Map();let region='body';
  function grainTexture(){const c=document.createElement('canvas');c.width=c.height=256;const cx=c.getContext('2d'),im=cx.createImageData(256,256);let s=1987;for(let i=0;i<im.data.length;i+=4){s=(s*1664525+1013904223)>>>0;const n=115+(s%26);im.data.set([n,n,n,255],i);}cx.putImageData(im,0,0);const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(9,9);return t;}
  const bump=texture?grainTexture():null;
  const material=(name,color,extra={})=>new THREE.MeshStandardMaterial({name,color,roughness:.68,metalness:0,bumpMap:bump,bumpScale:.006,...extra});
  const mats={yellow:material('warm golden plush','#f5bb2f'),orange:material('soft orange muzzle','#f18b0c'),shorts:material('tangerine shorts','#dc7020'),cuff:material('stitched waistband','#cf651a'),hair:material('dark chestnut hair','#30251c',{roughness:.82,bumpScale:.01}),groove:material('hair strand valleys','#241b14',{roughness:.9,bumpScale:.005}),inner:material('inner ear','#edaa31'),white:material('ivory eyes','#fff8e7',{roughness:.25,bumpMap:null}),iris:material('brown eyes','#29190d',{roughness:.16,bumpMap:null}),black:material('eye pupils','#080807',{roughness:.12,bumpMap:null}),glasses:material('bronze round glasses','#704820',{metalness:.45,roughness:.32,bumpMap:null}),mouth:material('small smile','#8b4517',{bumpMap:null}),glint:new THREE.MeshBasicMaterial({name:'eye catchlights',color:'#fffaf2'})};
  const rigid=b=>()=>[[b.index,1]];
  const torso=p=>{const w=THREE.MathUtils.smoothstep(p.y,.85,1.7);return [[pelvis.index,1-w],[spine.index,w]];};
  function add(geometry,mat,position,scale,weight,rotation){
    const matrix=new THREE.Matrix4().compose(position||V(),new THREE.Quaternion().setFromEuler(rotation||new THREE.Euler()),scale||V(1,1,1));geometry.applyMatrix4(matrix);
    const p=geometry.attributes.position,ids=[],weights=[];
    for(let i=0;i<p.count;i++){const v=V().fromBufferAttribute(p,i),w=weight(v);for(let k=0;k<4;k++){ids.push(w[k]?.[0]||0);weights.push(w[k]?.[1]||0);}}
    geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(ids,4));geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(weights,4));
    const key=wardrobe?region+':'+mat.name:mat.name;
    if(!parts.has(key))parts.set(key,{mat,region,geometries:[]});parts.get(key).geometries.push(geometry);
  }
  function ellipsoid(mat,pos,scale,b=spine,rot){add(new THREE.SphereGeometry(1,48,32),mat,V(...pos),V(...scale),typeof b==='function'?b:rigid(b),rot);}
  function tube(mat,points,r,b=head){const curve=new THREE.CatmullRomCurve3(points.map(p=>V(...p)));add(new THREE.TubeGeometry(curve,32,r,8,false),mat,null,null,rigid(b));}
  // Rounded torso and separate short trouser legs keep the silhouette compact.
  region='torso';ellipsoid(mats.yellow,[0,1.28,0],[.73,.71,.48],torso);region='body';
  ellipsoid(mats.shorts,[0,.70,-.005],[.71,.40,.46],pelvis);
  const waist=new THREE.TorusGeometry(.64,.038,12,80);add(waist,mats.cuff,V(0,.99,0),V(1,.70,1),rigid(pelvis),new THREE.Euler(Math.PI/2,0,0));
  for(const [side,s] of [['L',-1],['R',1]]) {
    const hip=named['hip_'+side],knee=named['knee_'+side],ankle=named['ankle_'+side];
    const legWeights=p=>{const a=THREE.MathUtils.smoothstep(.44-p.y,0,.20);return [[hip.index,1-a],[knee.index,a]];};
    ellipsoid(mats.shorts,[s*.32,.53,0],[.34,.24,.36],p=>[[pelvis.index,.85],[hip.index,.15]]);
    ellipsoid(mats.yellow,[s*.31,.36,0],[.18,.25,.20],legWeights);
    ellipsoid(mats.yellow,[s*.31,.14,.105],[.215,.14,.29],ankle);
    for(let toe=0;toe<3;toe++)ellipsoid(mats.yellow,[s*.31+(toe-1)*.10,.092,.313],[.064,.075,.058],ankle);
    const shoulder=named['shoulder_'+side],elbow=named['elbow_'+side],wrist=named['wrist_'+side];
    const arm=p=>{if(p.y>1.25){const w=THREE.MathUtils.smoothstep(1.52-p.y,0,.27);return [[shoulder.index,1-w],[elbow.index,w]];}const w=THREE.MathUtils.smoothstep(1.16-p.y,0,.20);return [[elbow.index,1-w],[wrist.index,w]];};
    const path=new THREE.CatmullRomCurve3([V(s*.51,1.76,0),V(s*.735,1.47,.02),V(s*.80,1.13,.06),V(s*.78,.83,.13)]);
    const limb=new THREE.TubeGeometry(path,48,.15,24,false),lp=limb.attributes.position;
    for(let row=0;row<=48;row++){const t=row/48,center=path.getPointAt(t);const cap=Math.min(1,Math.sin(Math.min(t/.12,1)*Math.PI/2),Math.sin(Math.min((1-t)/.16,1)*Math.PI/2));for(let col=0;col<=24;col++){const i=row*25+col,v=V().fromBufferAttribute(lp,i).sub(center).multiplyScalar(Math.max(.001,cap)).add(center);lp.setXYZ(i,v.x,v.y,v.z);}}
    limb.computeVertexNormals();add(limb,mats.yellow,null,null,arm);
    ellipsoid(mats.yellow,[s*.67,.98,.20],[.075,.10,.075],wrist);
  }
  // The broad muzzle, small eyes, and close-fitting glasses carry the identity.
  ellipsoid(mats.yellow,[0,2.34,0],[.83,.75,.63],head);
  ellipsoid(mats.orange,[0,2.12,.55],[.80,.435,.39],head);
  for(const [side,s] of [['L',-1],['R',1]]) {
    ellipsoid(mats.yellow,[s*.77,2.77,-.035],[.205,.285,.15],head,new THREE.Euler(0,0,-s*.32));
    ellipsoid(mats.inner,[s*.79,2.78,.088],[.117,.19,.039],head,new THREE.Euler(0,0,-s*.32));
    const eye=named['eye_'+side];
    ellipsoid(mats.white,[s*.34,2.63,.567],[.138,.167,.082],eye);
    ellipsoid(mats.iris,[s*.34,2.625,.637],[.092,.126,.047],eye);
    ellipsoid(mats.black,[s*.34,2.63,.67],[.055,.087,.025],eye);
    ellipsoid(mats.glint,[s*.34-.025,2.675,.69],[.026,.031,.012],eye);
    add(new THREE.TorusGeometry(.231,.019,12,80),mats.glasses,V(s*.34,2.65,.663),V(1,1,1),rigid(head));
    tube(mats.glasses,[[s*.565,2.65,.65],[s*.70,2.66,.52],[s*.795,2.60,.24]],.022);
  }
  tube(mats.glasses,[[-.108,2.64,.68],[0,2.675,.704],[.108,2.64,.68]],.018);
  tube(mats.mouth,[[-.062,2.005,.922],[0,1.981,.936],[.062,2.005,.922]],.014);
  // A scalloped bowl haircut; subtle radial ridges give actual 3D volume.
  const hp=[],hn=[],hu=[],hi=[],segments=128,rings=32;
  for(let j=0;j<=rings;j++)for(let i=0;i<=segments;i++){
    const phi=i/segments*Math.PI*2,front=Math.max(0,Math.cos(phi));
    const end=1.52-.37*front+.045*Math.cos(phi*17),theta=j/rings*end;
    const ridge=1+.028*Math.cos(phi*21)*Math.sin(theta)**1.5;
    hp.push(.755*Math.sin(theta)*Math.sin(phi)*ridge,2.58+.66*Math.cos(theta),.59*Math.sin(theta)*Math.cos(phi)*ridge-.015);
    hn.push(Math.sin(theta)*Math.sin(phi),Math.cos(theta),Math.sin(theta)*Math.cos(phi));hu.push(i/segments,j/rings);
    if(j<rings&&i<segments){const k=j*(segments+1)+i;hi.push(k,k+segments+1,k+1,k+1,k+segments+1,k+segments+2);}
  }
  const hair=new THREE.BufferGeometry();hair.setAttribute('position',new THREE.Float32BufferAttribute(hp,3));hair.setAttribute('normal',new THREE.Float32BufferAttribute(hn,3));hair.setAttribute('uv',new THREE.Float32BufferAttribute(hu,2));hair.setIndex(hi);hair.computeVertexNormals();add(hair,mats.hair,null,null,rigid(head));
  for(let i=0;i<21;i++){const phi=(i+.5)/21*Math.PI*2,end=1.52-.37*Math.max(0,Math.cos(phi))+.045*Math.cos(phi*17);const points=[];for(let j=0;j<=12;j++){const theta=.12+(end-.16)*j/12,ridge=1+.028*Math.cos(phi*21)*Math.sin(theta)**1.5;points.push([.756*Math.sin(theta)*Math.sin(phi)*ridge,2.58+.661*Math.cos(theta),.591*Math.sin(theta)*Math.cos(phi)*ridge-.015]);}tube(mats.groove,points,.005);}
  tube(mats.hair,[[0,3.19,0],[.025,3.30,.015],[-.055,3.39,.025],[-.10,3.40,.025]],.043);
  ellipsoid(mats.yellow,[0,.83,-.47],[.105,.105,.12],pelvis);
  const meshes=[];
  for(const [key,{mat,region:partRegion,geometries}] of parts){const merged=mergeGeometries(geometries,false);const mesh=new THREE.SkinnedMesh(merged,mat);mesh.name=key;mesh.userData.region=partRegion;mesh.castShadow=true;mesh.receiveShadow=true;mesh.frustumCulled=false;model.add(mesh);mesh.bind(skeleton);meshes.push(mesh);geometries.forEach(g=>g.dispose());}
  const helper=new THREE.SkeletonHelper(root);helper.material.depthTest=false;helper.material.transparent=true;helper.material.opacity=.7;helper.visible=false;helper.renderOrder=20;
  function orient(b,from,to){const world=new THREE.Quaternion().setFromUnitVectors(V(0,-1,0),to.clone().sub(from).normalize());const parent=b.parent.getWorldQuaternion(new THREE.Quaternion());b.quaternion.copy(parent.invert().multiply(world));model.updateMatrixWorld(true);}
  function pose(gait) {
    model.position.z=gait.z;
    pelvis.position.set(gait.sway,.71+gait.bob,0);
    spine.scale.y=1+.003*Math.sin(gait.time*2.1);
    head.rotation.z=.012*Math.sin(gait.time*1.8);
    for(const [side,s,index] of [['L',-1,0],['R',1,1]]) {
      const f=gait.feet[index],hip=named['hip_'+side],knee=named['knee_'+side],ankle=named['ankle_'+side];
      model.updateMatrixWorld(true);
      const a=hip.getWorldPosition(V()),c=V(f.x,f.y,f.z),dir=c.clone().sub(a),length=dir.length();dir.normalize();
      const half=Math.min(.21999,length/2),bend=Math.sqrt(Math.max(0,.22*.22-half*half));
      const pole=V(0,0,1).addScaledVector(dir,-dir.z).normalize();
      const b=a.clone().addScaledVector(dir,half).addScaledVector(pole,bend);
      orient(hip,a,b);orient(knee,b,c);
      const parent=knee.getWorldQuaternion(new THREE.Quaternion());ankle.quaternion.copy(parent.invert().multiply(new THREE.Quaternion().setFromAxisAngle(V(1,0,0),f.pitch||0)));
      const swing=Math.max(-.24,Math.min(.24,(f.z-gait.z)*1.4));
      named['shoulder_'+side].rotation.x=-swing;named['elbow_'+side].rotation.x=-.07;
      const blink=Math.sin(gait.time*.71)> .995? .12:1;named['eye_'+side].scale.y=blink;
    }
    model.updateMatrixWorld(true);
  }
  return {model,skeleton,bones:named,helper,pose,meshes,materials:mats};
}
