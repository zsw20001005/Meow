# Shared rig candidate review

The user authorized either using the previous download or finding a cute rigged model. Existing Lulu / Gao Miaomiao files must be retained. This prototype does not replace the desktop pet.

The previous Lulu source is a single connected STL sculpture (249,963 vertices), with no original rig, materials or animations. Prior limb separation left visible seam and shape problems. It is preserved as reference, not used as this candidate's animation base.

Selected candidates: Quaternius Sushi Restaurant Kit, Panda and Rabbit_Pink, CC0. Original glTF downloads remain under assets/sushi-original. Both have 43 skin joints, including root, shoulders, arms, finger segments, thighs and shins, plus 30 authored animations. Bone names match, but rest sizes/poses differ; validate retargeting rather than assuming identical transforms.

## iter_01

1. Imported neutral render preserves the author's stylized topology and atlas. These are alternative characters, not a high-fidelity Lulu reconstruction.
2. Importing the second animated model resets scene time. Initial grounding used a different evaluated pose and produced floating feet. Re-evaluate both at the final frame, then ground using deformed vertices.
3. Preview needs an actual shared animation file and sampled deformation checks, not merely two independent embedded animation sets.
4. No facial-expression or blanket/bed adaptation claim: source set covers body acting and cooking, not Lulu's complete interactions.
