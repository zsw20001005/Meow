"""Surface-distance segmentation with curvature barriers on the original STL."""
import bpy,heapq,json
import numpy as np
from pathlib import Path
root=Path(__file__).resolve().parent/'review/sketchfab-lulu'
bpy.ops.wm.open_mainfile(filepath=str(root/'source-normalized.blend'))
m=next(o.data for o in bpy.context.scene.objects if o.type=='MESH')
n=len(m.vertices)
p=np.empty(n*3,dtype=np.float64);m.vertices.foreach_get('co',p);p=p.reshape(-1,3)
norm=np.empty(n*3,dtype=np.float64);m.vertices.foreach_get('normal',norm);norm=norm.reshape(-1,3)
edges=np.empty(len(m.edges)*2,dtype=np.int32);m.edges.foreach_get('vertices',edges);edges=edges.reshape(-1,2)
a,b=edges.T;delta=p[b]-p[a];length=np.linalg.norm(delta,axis=1)
lap=np.zeros((n,3));np.add.at(lap,a,delta);np.add.at(lap,b,-delta)
sq=np.zeros(n);np.add.at(sq,a,length**2);np.add.at(sq,b,length**2)
curv=np.einsum('ij,ij->i',lap,norm)/np.maximum(sq,1e-12)
print('CURVATURE',np.percentile(curv,[0,5,25,50,75,90,95,99,100]))
cost=length*(1+25*np.maximum(np.maximum(curv[a],curv[b]),0)**2)
adj=[[] for _ in range(n)]
for i,j,w in zip(a,b,cost):adj[i].append((int(j),float(w)));adj[j].append((int(i),float(w)))
x,y,z=p.T
def partition(name,active,positive,negative):
    labels=np.full(n,-1,dtype=np.int8);dist=np.full(n,np.inf)
    labels[active&positive]=1;labels[active&negative]=0
    seeds=np.flatnonzero(labels>=0);dist[seeds]=0
    q=[(0,int(i)) for i in seeds];heapq.heapify(q)
    while q:
        d,i=heapq.heappop(q)
        if d!=dist[i]:continue
        for j,w in adj[i]:
            if active[j] and d+w<dist[j]:
                dist[j]=d+w;labels[j]=labels[i];heapq.heappush(q,(d+w,j))
    print(name,'positive',int(np.sum(labels==1)),'unresolved',int(np.sum(active&(labels<0))))
    return labels==1
pants=partition('shorts',z<1.06,
    ((z>.43)&(z<.68)&((y<-.29)|(y>.36)|(x>.81)))|((z>.735)&(z<.755)&((y<-.20)|(y>.40)|(x>.80))),
    (z>.86+.03*x)|(z<.095)|((((x+.72)/.07)**2+((y-.18)/.10)**2+((z-.62)/.12)**2)<1))
hat=partition('tangerine',z>2.43,
    (z>2.73)&(z<2.86)&(x<.13)&(x>-.35),
    (z<2.52)|(x>.36)|(x<-.51))
# Hand/forearm and head meet at a concave crease, used as a flood barrier.
hand=partition('raised hand',(x>.15)&(z>1.03)&(z<1.85)&(y<.10),
    ((x>.63)&(z<1.48)&(y<-.18))|((x>.42)&(x<.56)&(z>1.58)&(z<1.64)&(y<-.65)),
    (z>1.79)|((x<.27)&(z>1.45))|((y>.02)&(z>1.3)))
snout=partition('snout',(z>1.16)&(z<2.38)&(y<.02)&(~hand),
    (y<-.64)&(z>1.55)&(z<2.01+.17*x)&(x<.53)&(x>-.62),
    (z>2.19+.17*x)|(z<1.28)|(y>-.20)|(x<-.89))
eyes=[]
for ex,ez in [(-.371,2.211),(.333,2.319)]:
    r=((x-ex)/.13)**2+((z-ez)/.13)**2
    eyes.append(partition('eye',(r<3)&(y<-.25),r<.30,r>1.35))
degree=np.bincount(edges.ravel(),minlength=n)
def soften(mask,steps=20,sharpen=True):
    f=mask.astype(float)
    for _ in range(steps):
        total=np.zeros(n);np.add.at(total,a,f[b]);np.add.at(total,b,f[a])
        f=.45*f+.55*total/degree
    if sharpen:f=np.clip((f-.32)/.36,0,1)
    return f*f*(3-2*f)
np.savez_compressed(root/'surface-regions.npz',pants=soften(pants),hat=soften(hat),hand=hand,snout=soften(snout,70,False),eyeL=soften(eyes[0]),eyeR=soften(eyes[1]),curvature=curv)
