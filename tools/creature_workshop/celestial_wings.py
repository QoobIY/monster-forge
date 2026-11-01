"""Layered feather and jointed membrane wing families; independent authored contours."""
import numpy as np
from .geometry import mesh
from .feather_wings import raven_wings

LABELS={'back-angel-large':'Ангельские · раскрытые','back-angel-long':'Ангельские · длинные маховые','back-angel-raised':'Ангельские · вознесённые','back-demon-large':'Демонические · широкие перепонки','back-demon-dragon':'Демонические · драконьи','back-demon-hooked':'Демонические · загнутые'}
DESCRIPTIONS={k:v+'; объёмные перекрывающиеся перья' if 'angel' in k else v+'; суставчатое плечо, пальцы, вогнутые перепонки и когти' for k,v in LABELS.items()}

def author(b,style,z):
    if style.startswith('angel-'):
        first=len(b.commands);raven_wings(b,z)
        b.palette.update(cloth='eeeade',secondary='d2d7cc',accent='b6c4c7',metal='c5ab72')
        for c in b.commands[first:]:
            v,f=mesh(c);v=v.copy();sign=-1 if v[:,0].mean()<0 else 1
            root=np.array([sign*.14,1.76,z]);local=v-root
            if style=='angel-raised':
                angle=np.deg2rad(27)*sign
                rot=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
                local=local@rot.T;local[:,0]*=1.08
            else:
                local[:,0]*=1.12 if style=='angel-large' else 1.22
                if style=='angel-long':local[:,1]*=1.17
                if 'primary' in c['part'] or 'secondary_feather' in c['part']:
                    # Extend the distal half of each feather while preserving its root.
                    for i,t in enumerate((0,.18,.44,.76,1)):
                        local[i*6:(i+1)*6,1]-=.11*t*t
            c.update(op='indexed_mesh',vertices=(local+root).tolist(),faces=f.tolist(),part=c['part'].replace('raven','angel'),wing_family=style)
        return
    profile={'demon-large':(.99,0,.05),'demon-dragon':(1.18,-.09,.19),'demon-hooked':(.85,.33,.30)}[style]
    span,rise,hook=profile
    b.palette.update(cloth='733746',secondary='4b293a',metal='342b36',accent='bea98d')
    for sign in (-1,1):
        def p(x,y,d=0):return [sign*x*span,y+rise,z+d]
        root=p(.14,1.77);elbow=p(.53,2.14,-.055);wrist=p(.94,2.36,-.095)
        b.tube('demon_wing_arm','metal',[root,elbow,wrist],[.082,.066,.049],sides=8)
        ends=[p(.39,.92,-.10),p(.86,.99,-.16),p(1.27,1.28,-.14),p(1.63,1.73,-.13),p(1.72,2.30,-.09)]
        b.panel3('demon_root_membrane','cloth',[root,elbow,wrist,ends[0]],.024)
        for i,(a,c) in enumerate(zip(ends,ends[1:])):
            # A recessed scallop, rather than a straight triangle edge.
            a=np.array(a);c=np.array(c);w=np.array(wrist)
            mid=(a+c)*.5;mid+=(w-mid)*(.19 if style!='demon-hooked' else .29)
            q1=a*.65+mid*.35;q2=c*.65+mid*.35
            b.panel3('demon_membrane_lobe','cloth' if i%2==0 else 'secondary',[w.tolist(),a.tolist(),q1.tolist(),mid.tolist(),q2.tolist(),c.tolist()],.024)
        for i,end in enumerate(ends):
            end=np.array(end);bend=np.array(wrist)*.45+end*.55;bend[2]-=.025
            b.tube('demon_wing_finger','metal',[wrist,bend.tolist(),end.tolist()],[.031,.020,.008],sides=6)
            q=end+np.array([sign*.05,.075,0]);r=q+np.array([-sign*.045,.027,.02])
            b.tube('demon_finger_claw','accent',[end.tolist(),q.tolist(),r.tolist()],[.018,.012,.002],sides=5)
        b.tube('demon_wrist_hook','accent',[wrist,p(.99,2.36+hook,-.08),p(.88,2.39+hook,-.06)],[.039,.023,.002],sides=6)
        if style=='demon-dragon':
            for t in (.28,.55,.8):
                v=np.array(elbow)*(1-t)+np.array(wrist)*t
                b.tube('demon_leading_spine','accent',[v.tolist(),(v+[sign*.01,.15,0]).tolist(),(v+[sign*.08,.11,0]).tolist()],[.027,.014,.002],sides=5)
