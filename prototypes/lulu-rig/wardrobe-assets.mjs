import * as THREE from 'three';

export const palette = Object.freeze({cream:'#f4eee0',sage:'#8baf99',blue:'#92b9d1',rose:'#db9c9b'});
export const defaults = Object.freeze({version:1,rig:'lulu-v1',top:'tee',color:'cream',shorts:'orange',glasses:'bronze',bag:false,charm:false});
export function normalizeOutfit(value={}) {
  if(!value || typeof value!=='object' || Array.isArray(value)) value={};
  return {...defaults,top:['none','tee','sweater'].includes(value.top)?value.top:defaults.top,
    color:Object.hasOwn(palette,value.color)?value.color:defaults.color,
    shorts:['orange','navy'].includes(value.shorts)?value.shorts:defaults.shorts,
    glasses:['none','bronze','dark'].includes(value.glasses)?value.glasses:defaults.glasses,
    bag:value.bag===true,charm:value.charm===true};
}

// Garments are authored for the same bind pose and share the exact skeleton.
// Switching visibility/materials never rebuilds or restarts an animation.
export function createWardrobe(rig) {
  const V=(x=0,y=0,z=0)=>new THREE.Vector3(x,y,z),meshes=[],outfits={tee:[],sweater:[]};
  const torso=p=>{const w=THREE.MathUtils.smoothstep(p.y,.85,1.7);return [[rig.bones.pelvis.index,1-w],[rig.bones.spine.index,w]];};
  const rigid=name=>()=>[[rig.bones[name].index,1]];
  const fabric=new THREE.MeshStandardMaterial({color:palette.cream,roughness:.93,side:THREE.DoubleSide});
  const rib=fabric.clone();rib.roughness=1;
  const orange=new THREE.MeshStandardMaterial({color:'#e58d2f',roughness:.8});
  const green=new THREE.MeshStandardMaterial({color:'#6a8754',roughness:.85});
  function skin(geometry,material,weights,group,name) {
    const p=geometry.attributes.position,indices=[],values=[];
    for(let i=0;i<p.count;i++) {const w=weights(V().fromBufferAttribute(p,i));for(let j=0;j<4;j++){indices.push(w[j]?.[0]??0);values.push(w[j]?.[1]??0);}}
    geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(indices,4));geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(values,4));
    const mesh=new THREE.SkinnedMesh(geometry,material);mesh.name=name;mesh.frustumCulled=false;mesh.castShadow=mesh.receiveShadow=true;
    rig.model.add(mesh);mesh.bind(rig.skeleton);meshes.push(mesh);group?.push(mesh);return mesh;
  }
  function ellipsoid(position,scale) {const g=new THREE.SphereGeometry(1,40,24);g.scale(...scale);g.translate(...position);return g;}
  function ring(y,radius,depth) {const g=new THREE.TorusGeometry(radius,.023,10,64);g.rotateX(Math.PI/2);g.scale(1,1,depth);g.translate(0,y,0);return g;}
  for(const kind of ['tee','sweater']) {
    const group=outfits[kind],loose=kind==='sweater'?.025:0;
    // Open neckline and hem; the covered body surface is hidden when dressed.
    const start=Math.acos((1.86-1.28)/(.735+loose)),end=Math.acos((.97-1.28)/(.735+loose));
    const body=new THREE.SphereGeometry(1,64,32,0,Math.PI*2,start,end-start);
    body.scale(.755+loose,.735+loose,.51+loose);body.translate(0,1.28,0);
    skin(body,fabric,torso,group,kind+'-body');
    skin(ring(.98,.69+loose,.66),rib,torso,group,kind+'-hem');
    skin(ring(1.86,.46+loose,.68),rib,torso,group,kind+'-collar');
    for(const [side,s] of [['L',-1],['R',1]]) {
      const path=new THREE.CatmullRomCurve3([V(s*.51,1.76,0),V(s*.735,1.47,.02),V(s*.80,1.13,.06),V(s*.78,.83,.13)]);
      const length=kind==='tee'?.47:.79;
      const points=Array.from({length:41},(_,i)=>path.getPointAt(i/40*length));
      const sleevePath=new THREE.CatmullRomCurve3(points);
      const arm=p=>{if(p.y>1.25){const w=THREE.MathUtils.smoothstep(1.52-p.y,0,.27);return [[rig.bones['shoulder_'+side].index,1-w],[rig.bones['elbow_'+side].index,w]];}const w=THREE.MathUtils.smoothstep(1.16-p.y,0,.20);return [[rig.bones['elbow_'+side].index,1-w],[rig.bones['wrist_'+side].index,w]];};
      skin(new THREE.TubeGeometry(sleevePath,40,.186+loose,24,false),fabric,arm,group,kind+'-sleeve-'+side);
    }
    const patch=ellipsoid([.24,1.46,.497+loose],[.064,.059,.018]);
    skin(patch,orange,torso,group,kind+'-orange-stitch');
    skin(ellipsoid([.259,1.523,.497+loose],[.028,.012,.01]),green,torso,group,kind+'-leaf-stitch');
  }
  // Rigid accessories attach to named bones, unlike deformable clothes.
  const bag=new THREE.Group();bag.name='accessory-backpack';rig.bones.spine.add(bag);bag.position.set(0,.06,-.53);
  const bagMaterial=new THREE.MeshStandardMaterial({color:'#7e9e88',roughness:.95});
  const pack=new THREE.Mesh(ellipsoid([0,0,-.09],[.38,.40,.17]),bagMaterial);pack.castShadow=true;bag.add(pack);
  const pocket=new THREE.Mesh(ellipsoid([0,-.10,-.24],[.25,.18,.06]),bagMaterial.clone());pocket.material.color.multiplyScalar(.88);bag.add(pocket);
  const straps=[];
  for(const s of [-1,1]) {
    const path=new THREE.CatmullRomCurve3([V(s*.27,1.07,-.47),V(s*.47,1.78,-.24),V(s*.47,1.83,.22),V(s*.38,1.25,.44)]);
    straps.push(skin(new THREE.TubeGeometry(path,40,.028,12,false),bagMaterial,torso,null,'bag-strap-'+s));
  }
  const charm=new THREE.Group();charm.name='accessory-tangerine';rig.bones.head.add(charm);charm.position.set(.18,1.02,0);
  const fruit=new THREE.Mesh(ellipsoid([0,0,0],[.16,.13,.15]),orange);fruit.castShadow=true;charm.add(fruit);
  const leaf=new THREE.Mesh(ellipsoid([.055,.15,0],[.075,.012,.035]),green);leaf.rotation.z=.3;charm.add(leaf);
  let current=defaults;
  function apply(value) {
    current=normalizeOutfit(value);
    for(const [kind,group] of Object.entries(outfits))group.forEach(m=>m.visible=current.top===kind);
    rig.meshes.filter(m=>m.userData.region==='torso').forEach(m=>m.visible=current.top==='none');
    fabric.color.set(palette[current.color]);rib.color.copy(fabric.color).multiplyScalar(.93);
    rig.materials.shorts.color.set(current.shorts==='orange'?'#dc7020':'#475d72');
    rig.materials.cuff.color.set(current.shorts==='orange'?'#cf651a':'#3c5065');
    rig.meshes.filter(m=>m.material===rig.materials.glasses).forEach(m=>m.visible=current.glasses!=='none');
    rig.materials.glasses.color.set(current.glasses==='dark'?'#353536':'#704820');
    bag.visible=current.bag;straps.forEach(m=>m.visible=current.bag);charm.visible=current.charm;
    return {...current};
  }
  apply(defaults);
  return {apply,get current(){return {...current};},meshes,outfits,bag,charm};
}
