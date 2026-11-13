// Node-only alias for the pinned browser modules; no network dependency.
export async function resolve(specifier,context,next) {
  if(specifier==='three')return {url:new URL('./vendor/three.module.js',import.meta.url).href,shortCircuit:true};
  if(specifier.startsWith('three/addons/'))return {url:new URL('./vendor/addons/'+specifier.slice(13),import.meta.url).href,shortCircuit:true};
  return next(specifier,context);
}
