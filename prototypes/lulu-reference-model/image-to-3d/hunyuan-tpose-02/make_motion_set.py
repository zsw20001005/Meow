"""Independent motion prototypes with planted-foot two-bone IK and real body turns."""
import bpy,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'motion-set-01';OUT.mkdir(exist_ok=True)
sys.path.insert(0,'C:/Users/19083/.codex/skills/blender-modeler/scripts')
import render_views
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'rigged/Lulu-Tpose-Rig-Preview.blend'),use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['Lulu_Rig'];mesh=bpy.data.objects['Lulu_Body']
rig.animation_data_clear();P='mixamorig:';FPS=30
rest={b.name.removeprefix(P):b.matrix_local.copy() for b in rig.data.bones}
ankles={s:rest[s+'Foot'].translation.copy() for s in ['Left','Right']}
mid=(ankles['Left']+ankles['Right'])/2
lengths={s:((rest[s+'Leg'].translation-rest[s+'UpLeg'].translation).length,(rest[s+'Foot'].translation-rest[s+'Leg'].translation).length) for s in ['Left','Right']}
def smooth(x):
    x=min(1,max(0,x));return x*x*x*(10+x*(-15+6*x))
def envelope(t,d,fade=.6):return smooth(t/fade)*smooth((d-t)/fade)
def qz(a):return Quaternion(Vector((0,0,1)),a)
def rotation(name,*rotations):
    q=Quaternion()
    for axis,degrees in rotations:q=Quaternion(Vector(axis),math.radians(degrees))@q
    r=rest[name].to_quaternion()
    rig.pose.bones[P+name].rotation_quaternion=r.inverted()@q@r
def clear():
    rig.location=(0,0,0);rig.rotation_mode='QUATERNION';rig.rotation_quaternion=Quaternion()
    for b in rig.pose.bones:
        b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion();b.location=(0,0,0);b.scale=(1,1,1)
def pelvis(z):rig.pose.bones[P+'Hips'].location=rest['Hips'].to_3x3().inverted()@Vector((0,0,z))
def orient_bone(name,head,direction):
    b=rig.pose.bones[P+name]
    old=(rig.data.bones[P+name].tail_local-rig.data.bones[P+name].head_local).normalized()
    r=old.rotation_difference(direction.normalized()).to_matrix()@rest[name].to_3x3()
    m=r.to_4x4();m.translation=head;b.matrix=m
def leg_ik(side,target_world,foot_yaw):
    bpy.context.view_layer.update()
    inv=rig.matrix_world.inverted();target=inv@target_world
    hip=rig.pose.bones[P+side+'UpLeg'].head.copy();v=target-hip
    upper,lower=lengths[side];distance=v.length
    d=min(upper+lower-1e-5,max(abs(upper-lower)+1e-5,distance));direction=v.normalized()
    pole=Vector((0,-1,0));pole=(pole-direction*pole.dot(direction)).normalized()
    a=(upper*upper-lower*lower+d*d)/(2*d);h=math.sqrt(max(0,upper*upper-a*a))
    knee=hip+direction*a+pole*h
    orient_bone(side+'UpLeg',hip,knee-hip)
    bpy.context.view_layer.update()
    orient_bone(side+'Leg',knee,target-knee)
    bpy.context.view_layer.update()
    foot=rig.pose.bones[P+side+'Foot']
    rotation_world=qz(foot_yaw).to_matrix()@rest[side+'Foot'].to_3x3()
    m=(rig.matrix_world.to_3x3().inverted()@rotation_world).to_4x4();m.translation=target;foot.matrix=m
    bpy.context.view_layer.update()
    return {'reach_excess':max(0,distance-upper-lower),'ankle_error':(rig.matrix_world@foot.head-target_world).length}
def hermite(values,index,u,dt):
    slopes=[(b-a)/dt for a,b in zip(values,values[1:])]
    tangents=[0]+[2*slopes[i-1]*slopes[i]/(slopes[i-1]+slopes[i]) if slopes[i-1]*slopes[i]>0 else 0 for i in range(1,len(values)-1)]+[0]
    a=values[index];b=values[index+1];m0=tangents[index]*dt;m1=tangents[index+1]*dt
    return (2*u**3-3*u*u+1)*a+(u**3-2*u*u+u)*m0+(-2*u**3+3*u*u)*b+(u**3-u*u)*m1
def step_plan(turn=False):
    feet={s:ankles[s].copy() for s in ankles};yaw={s:0. for s in ankles}
    steps=[];centers=[0.]
    for i in range(13 if turn else 5):
        side='Left' if i%2==0 else 'Right'
        angle=min(i+1,12)*math.pi/6 if turn else 0.
        dest=qz(angle)@ankles[side] if turn else ankles[side]+Vector((0,-min(i+1,4)*.18,0))
        steps.append({'side':side,'feet':{s:p.copy() for s,p in feet.items()},'yaw':dict(yaw),'dest':dest,'angle':angle})
        feet[side]=dest;yaw[side]=angle
        centers.append(((feet['Left'].y+feet['Right'].y)/2-mid.y) if not turn else angle)
    return steps,feet,yaw,centers
plans={False:step_plan(False),True:step_plan(True)}
specs=[('idle','Lulu_Idle',4.),('look','Lulu_LookAround',4.8),('wave','Lulu_Wave',4.8),('walk','Lulu_WalkSteps',4.25),('turn','Lulu_StepTurn360',6.2)]
manifest={'fps':FPS,'source':str(ROOT/'rigged/Lulu-Tpose-Rig-Preview.blend'),'notes':'Gray-model motion prototypes. No facial animation. Walk has forward root motion; turn is actual rotating skeleton with alternating steps and a fixed camera. Blender-only deformation corrections retained.','clips':[]}
for slug,name,duration in specs:
    action=bpy.data.actions.new(name);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    for modifier in mesh.modifiers:modifier.show_viewport=False
    n=round(duration*FPS);maxreach=0.;maxerr=0.;maxslide=0.;lastplants={};sample_frames=set(round(1+i*n/6) for i in range(7));expected={}
    for f in range(1,n+2):
        scene.frame_set(f)
        t=(f-1)/FPS;clear();pelvis(-.045)
        rotation('LeftArm',((0,1,0),45));rotation('RightArm',((0,1,0),-45))
        targets={s:p.copy() for s,p in ankles.items()};footyaw={s:0. for s in ankles};planted=set(ankles)
        phase=2*math.pi*t/duration
        if slug=='idle':
            breath=math.sin(phase)
            rig.pose.bones[P+'Spine1'].scale=(1+.014*breath,1+.012*breath,1+.014*breath)
            rotation('LeftArm',((0,1,0),45+1.3*breath));rotation('RightArm',((0,1,0),-45-1.3*breath))
        elif slug=='look':
            e=envelope(t,duration)
            yaw=22*math.sin(phase)*e
            rotation('Neck',((0,0,1),yaw*.3));rotation('Head',((0,0,1),yaw*.7),((0,1,0),3*math.sin(phase)*e))
        elif slug=='wave':
            e=envelope(t,duration,.85)
            rotation('LeftArm',((0,1,0),45-30*e))
            rotation('LeftForeArm',((0,1,0),-65*e))
            rotation('LeftHand',((0,1,0),12*math.sin(2*math.pi*1.25*t)*e))
            rotation('Head',((0,1,0),-3*e))
        else:
            turn=slug=='turn';steps,finalfeet,finalyaw,centers=plans[turn];dt=.40 if turn else .65
            elapsed=t-.5;total=len(steps)*dt
            if elapsed<=0:pass
            elif elapsed>=total:
                targets={s:p.copy() for s,p in finalfeet.items()};footyaw=dict(finalyaw)
                if turn:rig.rotation_quaternion=qz(2*math.pi)
                else:rig.location.y=centers[-1]
            else:
                i=min(len(steps)-1,int(elapsed/dt));u=(elapsed-i*dt)/dt;step=steps[i];s=step['side'];a=smooth(u)
                targets={side:p.copy() for side,p in step['feet'].items()};footyaw=dict(step['yaw'])
                targets[s]=step['feet'][s].lerp(step['dest'],a)
                targets[s].z+=.085*math.sin(math.pi*u)**2
                footyaw[s]=step['yaw'][s]+(step['angle']-step['yaw'][s])*a
                planted.discard(s)
                pelvis(-.045-.012*math.sin(math.pi*u)**2)
                if turn:
                    angle=hermite(centers,i,u,dt);rig.rotation_quaternion=qz(angle)
                else:
                    rig.location.y=hermite(centers,i,u,dt)
                    rig.location.x=(-1 if s=='Left' else 1)*.018*math.sin(math.pi*u)**2
                    swing=8*math.sin(math.pi*u)*(-1 if s=='Left' else 1)
                    rotation('LeftArm',((0,1,0),45),((1,0,0),swing))
                    rotation('RightArm',((0,1,0),-45),((1,0,0),-swing))
            if turn:
                # Neck anticipates the direction of the next step, then settles.
                rotation('Head',((0,0,1),4*envelope(t,duration)))
        bpy.context.view_layer.update()
        for s in ankles:
            q=leg_ik(s,targets[s],footyaw[s]);maxreach=max(maxreach,q['reach_excess']);maxerr=max(maxerr,q['ankle_error'])
            pos=rig.matrix_world@rig.pose.bones[P+s+'Foot'].head
            if s in planted and s in lastplants:maxslide=max(maxslide,(pos-lastplants[s]).length)
            if s in planted:lastplants[s]=pos.copy()
            else:lastplants.pop(s,None)
        for b in rig.pose.bones:
            b.keyframe_insert('rotation_quaternion',frame=f);b.keyframe_insert('location',frame=f);b.keyframe_insert('scale',frame=f)
        rig.keyframe_insert('location',frame=f);rig.keyframe_insert('rotation_quaternion',frame=f)
        expected[f]={s:pos.copy() for s,pos in targets.items()}
    for fc in action.fcurves:
        for key in fc.keyframe_points:key.interpolation='LINEAR'
    scene.frame_start=1;scene.frame_end=n
    clip={'slug':slug,'action':name,'frames':n,'duration':n/FPS,'loop':slug in ('idle','look','wave','turn'),'max_ik_reach_excess':maxreach,'max_ankle_target_error':maxerr,'max_planted_ankle_step':maxslide,'root_motion':slug=='walk'}
    manifest['clips'].append(clip)
    for modifier in mesh.modifiers:modifier.show_viewport=True
    playback_error=0.
    for frame in sorted(sample_frames):
        scene.frame_set(frame);bpy.context.view_layer.update()
        for s in ankles:playback_error=max(playback_error,(rig.matrix_world@rig.pose.bones[P+s+'Foot'].head-expected[frame][s]).length)
        y=rig.location.y
        render_views.run(str(OUT/'checks-v2'/slug/f'{frame:04d}'),mode='clay',res=400,color_by='material',names=[mesh.name],focus=((-1.6,y-1.2,-.1),(1.6,y+1.2,3.1)),views=[('three_quarter',25,6,True)])
    clip['sampled_playback_ankle_error']=playback_error
    print('CLIP',json.dumps(clip),flush=True)
rig.animation_data.action=bpy.data.actions['Lulu_Idle'];scene.frame_start=1;scene.frame_end=120;scene.frame_set(1)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Lulu-Five-Motions.blend'))
print('MOTION_SET_SAVED',flush=True)
