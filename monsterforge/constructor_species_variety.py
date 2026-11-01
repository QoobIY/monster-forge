"""Species-specific anatomical revisions, derived from frozen source recipes."""
import copy

import numpy as np

from tools.creature_workshop.geometry import mesh
from tools.creature_workshop.original_constructor import OriginalSculpt

REVISION = 1
RACES = {'beast-elephant', 'crab', 'beetle', 'scorpion'}
LABELS = {
    'beast-elephant': ('Азиатский слон · малые уши и короткие бивни',
                       'Африканский слон · широкие уши и опущенный хобот',
                       'Мамонт · шерсть, высокий загривок и спиральные бивни'),
    'crab': ('Краб-скрипач · крупная левая клешня',
             'Рифовый краб · высокий округлый панцирь и короткие клешни',
             'Краб-паук · плоский шипастый панцирь и длинные клешни'),
    'scorpion': ('Пустынный скорпион · тонкие клешни и высокое жало',
                 'Императорский скорпион · массивные клешни и низкий хвост',
                 'Костяной скорпион · рёбра панциря и отведённое жало'),
    'beetle': ('Жук-олень · ветвистые жвалы и вытянутые надкрылья',
               'Жук-носорог · раздвоенный рог и купольный панцирь',
               'Панцирный жук · широкий щит и зубчатые надкрылья',
               'Нерубианский страж · парные рога и щитовая голова'),
}


def apply(recipe, settings, slot):
    race = settings['race']
    if race not in RACES:
        return
    from .workshop_constructor import _transform

    variant = recipe['species_design']['variant']
    source_commands = [c['id'] for c in recipe['commands']]
    b = OriginalSculpt({'id': f'species-anatomy-v{REVISION}',
                        'palette': copy.deepcopy(recipe['palette'])})
    b.slot = slot
    b.stage = 1

    def remove(*terms):
        recipe['commands'] = [c for c in recipe['commands']
                              if not any(t in c['part'] for t in terms)]

    def deform(terms, scale, pivot):
        scale, pivot = np.array(scale), np.array(pivot)
        recipe['commands'] = [_transform(c, scale, pivot * (1 - scale),
                                         f'{race}-anatomy-v{REVISION}')
                              if any(t in c['part'] for t in terms) else c
                              for c in recipe['commands']]

    if race == 'beast-elephant':
        if slot == 'head':
            remove('scalloped_elephant_ear', 'curved_ivory_tusk',
                   'articulated_trunk', 'trunk_transverse_fold', 'trunk_tip_nostril')
            for sign in (-1, 1):
                if variant == 0:
                    outline = [[.31, 2.12, .85], [.59, 2.14, .82], [.69, 1.91, .85],
                               [.57, 1.61, .90], [.32, 1.70, .94]]
                elif variant == 1:
                    outline = [[.32, 2.19, .83], [.73, 2.32, .74], [1.12, 2.06, .75],
                               [1.06, 1.59, .82], [.73, 1.28, .88], [.34, 1.53, .95]]
                else:
                    outline = [[.31, 2.14, .83], [.52, 2.16, .78], [.61, 1.94, .83],
                               [.51, 1.72, .89], [.32, 1.76, .94]]
                b.panel3('anatomical_elephant_ear', 'skin', [[sign*x, y, z] for x,y,z in outline], .07)
                path = ([[.23,1.61,1.24],[.28,1.50,1.48],[.28,1.55,1.66]] if variant == 0 else
                        [[.23,1.61,1.24],[.37,1.44,1.64],[.47,1.44,1.97],[.49,1.58,2.17]] if variant == 1 else
                        [[.23,1.61,1.24],[.49,1.35,1.63],[.68,1.46,2.04],
                         [.62,1.81,2.25],[.40,2.02,2.12]])
                b.tube('anatomical_ivory_tusk', 'bone', [[sign*x,y,z] for x,y,z in path],
                       np.linspace(.075 if variant != 2 else .10, .003, len(path)).tolist(), sides=10)
            trunk = ([[0,1.85,1.22],[0,1.48,1.40],[0,1.08,1.51],[0,.90,1.72],[0,1.08,1.90]] if variant == 0 else
                     [[0,1.85,1.22],[0,1.45,1.40],[0,.96,1.49],[0,.49,1.55],[0,.38,1.76]] if variant == 1 else
                     [[0,1.85,1.22],[0,1.43,1.43],[0,.93,1.57],[0,.60,1.74],[0,.79,1.95]])
            b.tube('anatomical_trunk', 'skin', trunk, [.17,.14,.105,.075,.045], sides=10)
            tip = np.array(trunk[-1])
            for sign in (-1,1):
                b.oval('trunk_nostril', 'dark', (tip+[sign*.021,.01,.032]).tolist(), [.013,.013,.009], sides=6)
        if variant == 2 and slot in {'head','torso'}:
            # Wool follows the surface of the selected immutable carrier.
            b.palette['mammoth_wool'] = '594334'
            carriers = [c for c in recipe['commands'] if ('cranial' if slot=='head' else 'chest_waist') in c['part']]
            for c in carriers:
                v = mesh(c)[0]
                for i,p in enumerate(v):
                    if i % 3 or abs(p[0]) < .15 or p[1] < 1.12:
                        continue
                    end = p + [np.sign(p[0])*.035, -.16-(i%4)*.025, -.025]
                    b.tube('mammoth_hanging_wool', 'mammoth_wool', [p.tolist(), end.tolist()], [.045,.003], sides=5)
            if slot == 'torso':
                b.oval('mammoth_shoulder_hump', 'mammoth_wool', [0,1.96,.30], [.48,.42,.48], sides=10)

    elif race in {'crab', 'scorpion'}:
        if slot.endswith('_claw'):
            sign = -1 if slot.startswith('left') else 1
            recipe['commands'] = []
            size = ((1.55 if sign == -1 else .66), .98, .62)[variant] if race == 'crab' else (.60, 1.27, .88)[variant]
            reach = (1.0,.82,1.37)[variant] if race=='crab' else (1.20,.85,1.05)[variant]
            root = np.array(recipe['contract_anchors'][slot])
            elbow = np.array([sign*.72,.69,.91])
            palm = np.array([sign*(.76+.10*(reach-1)), .74, .95+.31*reach])
            b.tube('articulated_claw_arm','skin',[root.tolist(),elbow.tolist(),palm.tolist()], [.085,.11*size,.10*size],sides=8)
            b.oval('anatomical_claw_palm','skin',palm.tolist(),[.19*size,.18*size,.23*size],sides=10)
            for jaw in (-1,1):
                base = palm + [0,jaw*.13*size,.10*size]
                bend = palm + [sign*.035,jaw*.24*size,.36*reach]
                tip = palm + [0,jaw*.055*size,.59*reach]
                b.tube('opposed_claw_finger','skin',[base.tolist(),bend.tolist(),tip.tolist()],[.085*size,.065*size,.009],sides=8)
                for t in (.38,.64):
                    p = base*(1-t)+bend*t
                    b.tube('claw_gripping_tooth','bone' if variant==2 else 'skin',[p.tolist(),(p+[0,-jaw*.08*size,.025]).tolist()],[.035*size,.002],sides=5)
        if slot == 'torso':
            scale = ((1.08,.85,1.0),(.92,1.65,.92),(1.15,.68,1.1))[variant] if race=='crab' else ((.90,.88,1),(1.13,1.10,1),(1,1.05,1))[variant]
            deform(('whole_thorax','whole_abdomen','carapace_edge_tooth'),scale,[0,.68,.19])
            if variant == 2:
                for sign in (-1,1):
                    for i in range(6):
                        z=.52-i*.17
                        x=sign*(.60 if race=='crab' else .34)
                        b.tube('carapace_lateral_spine','bone' if race=='scorpion' else 'skin',[[x,.71,z],[x+sign*.25,.84,z-.06]],[.065,.002],sides=6)
        if race=='scorpion' and slot=='abdomen' and variant==2:
            for i in range(6):
                z=-.14-i*.14
                b.tube('bone_abdominal_rib','bone',[[-.32,.72,z],[0,.96,z],[.32,.72,z]],[.035,.045,.035],sides=6)
        if race=='scorpion' and slot=='tail':
            recipe['commands']=[]
            path = ([[0,.72,-.8],[0,.91,-1.16],[0,1.32,-1.39],[0,1.85,-1.30],[0,2.19,-.97],[0,2.12,-.58]] if variant==0 else
                    [[0,.72,-.8],[0,.80,-1.16],[0,1.09,-1.47],[0,1.47,-1.41],[0,1.62,-1.11],[0,1.51,-.90]] if variant==1 else
                    [[0,.72,-.8],[0,.90,-1.19],[0,1.30,-1.48],[0,1.74,-1.58],[0,1.94,-1.87],[0,1.78,-2.10]])
            radii = np.linspace(.14,.075,len(path)) * (1.15 if variant==1 else 1)
            for i in range(len(path)-1):
                b.tube('articulated_tail_segment','bone' if variant==2 else 'skin',path[i:i+2],[float(radii[i]),float(radii[i+1])],sides=8)
            p=np.array(path[-1]);end=p+[0,-.34,.17 if variant!=2 else -.17]
            b.oval('venom_bulb','skin',p.tolist(),[.12,.13,.13],sides=8)
            b.tube('curved_terminal_stinger','dark',[p.tolist(),(p+[0,-.17,.17 if variant!=2 else -.17]).tolist(),end.tolist()],[.075,.045,.002],sides=8)

    elif race == 'beetle' and variant < 3:
        if slot in {'torso','abdomen'}:
            # Keep the ventral attachment region fixed for mixed leg donors.
            for c in recipe['commands']:
                v,f=mesh(c);v=v.copy();t=np.clip((v[:,1]-.56)/.20,0,1)
                # Preserve the lateral shell triangles through which leg roots
                # enter; raising their upper endpoints would narrow the whole
                # section even below the nominal deformation threshold.
                t*=np.clip((.18-np.abs(v[:,0]))/.08,0,1)
                v[:,1]+=t*(0,.18,.06)[variant]
                v[:,0]*=1+t*(0,-.08,.26)[variant]
                c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist());c.pop('vertex_normals',None)
            if variant==2:
                for sign in (-1,1):
                    for i in range(5):
                        z=-.32-i*.12 if slot=='abdomen' else .22-i*.10
                        x=sign*(.36 if slot=='abdomen' else .28)
                        b.tube('shield_serrated_edge','skin',[[x,.69,z],[x+sign*.16,.83,z-.04]],[.055,.002],sides=6)
        if slot=='head' and variant==1:
            remove('horn')
            path=[[0,.66,.42],[0,.85,.57],[0,1.12,.76],[0,1.25,.95]]
            b.tube('rhinoceros_bifurcating_horn','skin',path,[.095,.075,.045,.018],sides=9)
            for sign in (-1,1):
                b.tube('rhinoceros_horn_fork','skin',[path[-2],path[-1],[sign*.12,1.29,1.02]],[.04,.025,.002],sides=7)
        if slot=='head' and variant==2:
            b.panel3('beetle_broad_cephalic_shield','skin',[[-.29,.72,.38],[0,.88,.36],[.29,.72,.38],[.24,.51,.53],[-.24,.51,.53]],.10)

    recipe['commands'].extend(b.commands)
    recipe['palette'].update(b.palette)
    recipe['species_anatomy_revision'] = {
        'schema_version': 1, 'revision': REVISION, 'race': race, 'variant': variant,
        'label': LABELS[race][variant], 'source_commands': source_commands,
        'source_preserved': True,
    }
