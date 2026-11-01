"""Marine naga equipment, fitted to immutable donor anatomy in derived parts."""
import copy
import numpy as np
from tools.creature_workshop.original_constructor import OriginalSculpt, mesh_command
from tools.creature_workshop.family_faces import orient_faces
from .constructor_face_fit import front_depth

REVISION = 3
LABELS = ['Страж кораллового рифа', 'Жемчужный панцирь', 'Воин глубоких вод', 'Хранитель ламинарии', 'Владыка приливов']

def apply(recipe, settings, slot):
    if settings['race'] != 'naga' or slot not in {'torso', 'left_arm', 'right_arm'}:
        return
    design = recipe['species_design']
    variant = design['variant'] % 5
    female = design['gender'] == 'female'
    original = recipe['commands']
    # Preserve the approved body, neck, hands and limb proportions, replacing clothes.
    keep = ('tailored_body', 'neck') if slot == 'torso' else ('fitted_sleeve', 'palm')
    anatomy = [copy.deepcopy(c) for c in original if any(c['part'].endswith(k) for k in keep)]
    if not anatomy:
        raise ValueError('Naga donor has no approved anatomy')
    for c in anatomy:
        c['material'] = 'skin'
        if c['part'].endswith('fitted_sleeve'):
            c['part'] = 'naga_exposed_arm'
        elif c['part'].endswith('tailored_body'):
            c['part'] = 'naga_upper_anatomy'
    pal = copy.deepcopy(recipe['palette'])
    pal.update(marine_shell=['327e83', 'b1c5c3', '31526f', '47776b', '4e648f'][variant],
               marine_ridge=['e39b71', 'e4d9b9', '9ab9cc', 'c2b681', 'dac27b'][variant],
               marine_fin=['428f88', '6f9cba', '486683', '598b71', '597bad'][variant],
               marine_pearl='eee5ce')
    for material, color in [('marine_shell','cloth'),('marine_ridge','accent'),('marine_fin','secondary')]:
        if settings['colors'].get(color):
            pal[material] = settings['colors'][color].lstrip('#')
    b = OriginalSculpt({'id': 'naga-marine-costume', 'palette': pal})
    b.slot = slot
    b.stage = 3
    surface = anatomy

    def fitted(name, material, xy, depth=.018):
        pts = np.array(xy, dtype=float)
        z = front_depth(surface, pts)
        if not np.isfinite(z).all():
            raise ValueError(f'Marine plate outside {slot}: {name}')
        b.panel3(name, material, np.column_stack([pts, z + .009]).tolist(), depth)
        # Project every bevel/inner vertex too; corners alone cannot fit a curved chest.
        c = b.commands[-1]
        v, f = mesh_command(c)
        fitted_z = front_depth(surface, v[:, :2])
        if not np.isfinite(fitted_z).all():
            raise ValueError('Marine bevel outside body')
        # panel3 stores outline, inset crown, rear ring, then an optional crown centre.
        # Keep all crown vertices outside the skin, not half of the vertex array.
        n = len(pts)
        offsets = np.full(len(v), -.004)
        offsets[:n] = .006
        offsets[n:2*n] = .018
        if len(v) > 3*n:
            offsets[3*n:] = .025
        v[:, 2] = fitted_z + offsets
        c.update(op='indexed_mesh', vertices=v.tolist(), faces=orient_faces(v, f).tolist())

    if slot == 'torso':
        w = .245 if female else .29
        # Five different armor constructions, rather than the same tunic recolored.
        if variant == 0:
            for row in range(4):
                y = 1.73 - row * .105
                for col in range(5):
                    x = (col - 2) * w * .32 + (.02 if row % 2 else 0)
                    fitted('reef_overlapping_scale', 'marine_shell', [[x-.048,y],[x+.048,y],[x+.053,y-.047],[x,y-.115],[x-.053,y-.047]])
        elif variant == 1:
            for s in (-1, 1):
                for j in range(6):
                    x = s * (.022 + j * .033)
                    fitted('scallop_radial_shell', 'marine_ridge' if j % 2 else 'marine_shell', [[s*.025,1.43],[x,1.75-abs(j-2)*.015],[x+s*.031,1.74-abs(j-2)*.02],[s*.052,1.41]])
        elif variant == 2:
            for row in range(4):
                y = 1.76 - row * .105
                fitted('abyss_segmented_carapace', 'marine_shell', [[-w*.79,y-.024],[0,y],[w*.79,y-.024],[w*.72,y-.07],[0,y-.112],[-w*.72,y-.07]])
                fitted('abyss_keel_ridge', 'marine_ridge', [[-.015,y-.02],[.015,y-.02],[.018,y-.086],[0,y-.10],[-.018,y-.086]])
        elif variant == 3:
            for s in (-1,1):
                for j in range(4):
                    x = s*(.035+j*.045)
                    fitted('kelp_woven_lamella', 'marine_fin' if j%2 else 'marine_shell', [[x-.020,1.75],[x+.025,1.73],[x+s*.025,1.37],[x-s*.022,1.39]])
            for j in range(4):
                y=1.70-j*.08
                fitted('kelp_horizontal_binding','marine_ridge',[[-.20,y],[.20,y-.024],[.20,y-.043],[-.20,y-.018]],.009)
        else:
            for s in (-1,1):
                fitted('tidal_royal_shell','marine_shell',[[s*.018,1.76],[s*w*.80,1.71],[s*w*.78,1.50],[s*.075,1.35],[s*.018,1.43]])
                for j in range(4):
                    x=s*(.06+j*.036)
                    fitted('tidal_radial_inlay','marine_ridge',[[x,1.70],[x+.010,1.69],[s*.055+.010,1.43],[s*.055,1.44]],.008)
        # No skirts or tabards: articulated shell girdle follows the upper tail/body.
        for s in (-1,1):
            for j in range(3):
                x=s*(.04+j*.062)
                fitted('marine_pelvic_shell','marine_shell',[[x-.028,1.30],[x+.028,1.30],[x+.030,1.22],[x,1.185],[x-.030,1.22]])
        for s in (-1,1):
            # Shoulder fins attach through the chest surface, then sweep backwards.
            x=s*(.25 if female else .29)
            length=[.18,.11,.23,.16,.20][variant]
            b.panel3('swept_pectoral_fin','marine_fin',[[x,1.73,.015],[x+s*length,1.80,-.12],[x+s*length*.77,1.62,-.18],[x,1.59,-.035]],.025)
            b.tube('pectoral_fin_ray','marine_ridge',[[x,1.69,.012],[x+s*length*.87,1.77,-.13]],[.012,.003],sides=6)
        # Small pearls sit on the chest rather than detached necklaces.
        for x in (-.085,0,.085):
            z=float(front_depth(surface,np.array([[x,1.79]]))[0])
            b.oval('chest_inset_pearl','marine_pearl',[x,1.79,z+.012],[.016,.017,.012],sides=8)
    else:
        sign = -1 if slot=='left_arm' else 1
        # Fitted scale vambrace follows the original elbow/wrist, with no cloth sleeve.
        for j in range(3 + (variant==0)):
            y=1.31-j*.068
            # Find the actual arm centre and width in this horizontal section.
            verts=np.concatenate([mesh_command(c)[0] for c in surface if c['part']=='naga_exposed_arm'])
            near=verts[np.abs(verts[:,1]-y)<.085]
            if not len(near):raise ValueError('Missing arm section')
            x=float(near[:,0].mean())
            fitted('marine_articulated_vambrace','marine_ridge' if variant==1 else 'marine_shell',[[x-.042,y],[x+.042,y],[x+.036,y-.039],[x,y-.061],[x-.036,y-.039]])
        x=sign*.73
        b.panel3('forearm_swimming_fin','marine_fin',[[x,1.31,.045],[x+sign*(.14+variant*.008),1.38,-.075],[x+sign*.10,1.12,-.08],[x+sign*.025,1.08,.045]],.018)
    commands=anatomy+b.commands
    for i,c in enumerate(commands):
        v,f=mesh_command(c)
        c.update(id=f'naga-marine-v{REVISION}-{slot}-{i}',op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,f).tolist(),ai_description_ru=LABELS[variant]+': обтекаемый панцирь морских раковин, плавники направлены назад; открытая кожа, без сухопутной одежды.')
    recipe['commands']=commands
    recipe['palette'].update(b.palette)
    recipe['naga_costume_revision']={'schema_version':1,'revision':REVISION,'variant':variant,'label_ru':LABELS[variant],'source_commands':[c['id'] for c in original]}
