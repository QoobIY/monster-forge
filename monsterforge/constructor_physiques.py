"""Three anatomical mass profiles; surface edits do not implement rig poses."""
import numpy as np
from tools.creature_workshop.geometry import mesh
from .constructor_knees import world_bind

PROFILES={
    'muscular':dict(label='Атлет · развитая мускулатура',chest=1.26,depth=1.25,waist=.98,hip=1.08,shoulder=.038,upper=1.35,forearm=1.22,thigh=1.25,calf=1.18,hand=1.03),
    'bodybuilder':dict(label='Бодибилдер · V-образный торс',chest=1.46,depth=1.43,waist=1.04,hip=1.15,shoulder=.066,upper=1.72,forearm=1.40,thigh=1.48,calf=1.29,hand=1.08),
    'strongman':dict(label='Тяжеловес · мощный корпус',chest=1.48,depth=1.52,waist=1.34,hip=1.25,shoulder=.078,upper=1.62,forearm=1.46,thigh=1.53,calf=1.35,hand=1.10),
}
DESCRIPTIONS={
    'muscular':'Атлет: развитые грудь и плечи, выраженные бицепсы, плотные предплечья и бёдра при узкой талии.',
    'bodybuilder':'Бодибилдер: широкий V-образный торс, крупные дельты, бицепсы и трицепсы, мощные бёдра и икры. Кисти и суставы сохраняют естественный размер.',
    'strongman':'Тяжеловес: широкий глубокий корпус и плотная талия, тяжёлые плечи и предплечья, массивные бёдра и икры.',
}


def apply(recipe,settings,slot):
    profile=PROFILES.get(settings['form'])
    if not profile or slot in {'head','back_attachment'}:return
    bind=world_bind()
    for c in recipe['commands']:
        v,f=mesh(c);v=v.copy();y=v[:,1]
        if slot=='torso':
            width=np.interp(y,[0,1.03,1.26,1.53,1.80,1.94,2.2],
                [profile['hip'],profile['hip'],profile['waist'],profile['chest'],profile['chest'],1,1])
            depth=np.interp(y,[0,1.06,1.28,1.52,1.80,1.95,2.2],[1,profile['hip'],profile['waist'],profile['depth'],profile['depth'],1,1])
            v[:,0]*=width;v[:,2]*=depth
        elif slot.endswith('_arm'):
            side=slot.split('_')[0];sign=-1 if side=='left' else 1
            sh,el,wr=[np.asarray(bind[side+'_'+k]) for k in ('shoulder','elbow','hand')]
            hand=any(t in c['part'] for t in ('palm','finger','thumb','hand_dorsal','hand_armor'))
            if hand:v=wr+(v-wr)*profile['hand']
            else:
                centres=[];amounts=[]
                for upper,(a,b) in enumerate(((el,wr),(sh,el))):
                    axis=b-a;t=np.clip((v-a)@axis/(axis@axis),0,1)
                    centre=a+t[:,None]*axis
                    envelope=np.interp(t,[0,.14,.36,.63,.84,1],[.35,.78,1,.85,.40,.12])
                    amount=1+(profile['upper' if upper else 'forearm']-1)*envelope
                    centres.append(centre);amounts.append(amount)
                candidates=np.stack(centres);nearest=np.linalg.norm(candidates-v,axis=2).argmin(0)
                centre=candidates[nearest,np.arange(len(v))];amount=np.stack(amounts)[nearest,np.arange(len(v))]
                v=centre+(v-centre)*amount[:,None]
                v[:,0]+=sign*profile['shoulder']*np.clip((y-wr[1])/(sh[1]-wr[1]),0,1)
        elif slot.endswith('_leg'):
            side=slot.split('_')[0];sign=-1 if side=='left' else 1
            ky=bind[side+'_knee'][1];cx=bind[side+'_knee'][0]
            # The frozen thigh has the old medial seam adjustment. Bulk around
            # that existing centre line, then apply the compact stance once.
            cx=cx-sign*.03*np.clip((y-.48)/(.68),0,1)
            amount=np.interp(y,[0,.10,.28,ky,.76,.94,1.16],
                [1,1,profile['calf'],1.07,profile['thigh'],profile['thigh'],profile['hip']])
            zc=np.interp(y,[0,.085,ky,1.16],[bind[side+'_foot'][2],bind[side+'_foot'][2],bind[side+'_knee'][2],0])
            v[:,0]=cx+(v[:,0]-cx)*amount
            v[:,2]=zc+(v[:,2]-zc)*amount
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist())
        c.pop('vertex_normals',None)
        c['physique_revision']={'schema_version':1,'profile':settings['form'],'description_ru':DESCRIPTIONS[settings['form']],
            'parameters':profile,'method':'anatomical mass about limb segments; height and floor unchanged'}
