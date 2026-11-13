# Iteration checks

1. **T-pose reconstruction:** actual front/side/back/three-quarter renders checked. ✅ Both arm/torso gaps and inter-leg space present; rump tail visible. Hair, muzzle, hands and glasses retained. ❌ Eyes/muzzle details remain softer than the AI reference; no texture in this stage.
2. **Automatic rig:** T-pose kept, no rest-pose unfolding of fused arms. ✅ Rest render does not show previous stretched armpit membranes. ❌ GLB contains tiny displayed bone tails and asymmetric knee estimates.
3. **Editable v2:** useful bone lengths, symmetric pivots, rest-shape delta below 1e-6. ✅ Bilateral joints move. ❌ Relaxing arms yields 146 measured edges stretched over 3x; shoulder/upper-leg artifacts visible in real pose renders.
4. **Weight v3 / normal v4:** 36 adjacency smoothing passes below neck. ✅ Relaxing-arm >3x edges reduced to 6. Clearing imported custom normals did not remove all visible joint wrinkles. ❌ Some elbow and crotch deformation remains.
5. **Blender v5:** preserve-volume armature and 12 corrective-smooth iterations at factor 0.6. ✅ Relaxing-arm >3x edges reduced to 1; shoulders and leg surface visibly smoother. Six poses rendered in front and 3/4 views; animation samples checked. ❌ Small elbow dents at 55-degree forward bend and slight shorts distortion remain. These need animation-friendly topology/correctives, not a claim of full production readiness.
6. **Presentation:** fixed camera, nine-second actual 30 fps render. Hard Workbench cast-shadow triangle on belly identified in first video frames and removed by disabling cast shadows for the final neutral studio preview. This changes presentation only, not geometry. General GLB export separately checked for 22 joints, one skin and embedded test animation; Blender-only corrections are explicitly documented as absent from GLB.

No existing application resource, old character or discarded prior model was removed or replaced.
