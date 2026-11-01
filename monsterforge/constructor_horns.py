"""Six skull-mounted horn silhouettes; decorative anatomy on the head slot."""
import math
import numpy as np
from .constructor_surface_fit import triangles,radial_hit

LABELS={'demon_ram_horns':'Демонические · витые бараньи','demon_swept_horns':'Демонические · загнутые назад','demon_forked_horns':'Демонические · раздвоенные','angel_lyre_horns':'Ангельские · лира','angel_antler_horns':'Ангельские · ветвистые','angel_crown_horns':'Ангельские · венец'}
DESCRIPTIONS={
 'demon_ram_horns':'Парные тёмные бараньи рога: широкое основание на висках, объёмный закрученный контур назад и вниз, сужающийся кончик и поперечные рёбра.',
 'demon_swept_horns':'Парные демонические рога: массивное основание, высокий подъём и длинный изгиб назад, острые светлые концы и редкие поперечные рёбра.',
 'demon_forked_horns':'Парные раздвоенные демонические рога: толстый общий ствол, две асимметричные восходящие ветви с острыми концами.',
 'angel_lyre_horns':'Парные светлые ангельские рога: плавный изгиб наружу и затем внутрь, высокий симметричный силуэт лиры, золотые основания.',
 'angel_antler_horns':'Парные ангельские рога: светлые ветвистые стволы с тремя разновысокими отростками, тонкие золотые концы.',
 'angel_crown_horns':'Ангельский венец из рогов: три восходящих светлых зубца на каждой стороне, общий височный корень, золотые рёбра.'}

def author(b,kind,skin,vertices,settings):
    top=float(vertices[:,1].max());cz=float((vertices[:,2].min()+vertices[:,2].max())*.5);tri=triangles(skin)
    angel=kind.startswith('angel_')
    b.palette['horn']=(settings['colors']['secondary'] or ('#e7e0c8' if angel else '#44363f')).lstrip('#')
    b.palette['horn_tip']=(settings['colors']['accent'] or ('#c5a454' if angel else '#baa58d')).lstrip('#')
    for sign in (-1,1):
        y=top-.13;direction=np.array([sign*math.sin(1.20),0,math.cos(1.20)])
        origin=np.array([0,y,cz]);hit=radial_hit(tri,origin,direction)
        radius=hit if hit is not None else float(np.abs(vertices[:,0]).max())
        anchor=origin+direction*(radius-.009)
        def p(x,dy,z):return (anchor+[sign*x,dy,z]).tolist()
        if kind=='demon_ram_horns':
            path=[p(0,0,0),p(.10,.11,-.04),p(.22,.14,-.14),p(.28,.04,-.23),p(.24,-.09,-.27),p(.15,-.13,-.22),p(.115,-.045,-.16)];radii=[.073,.077,.068,.054,.039,.024,.002]
        elif kind=='demon_swept_horns':
            path=[p(0,0,0),p(.085,.13,-.035),p(.13,.30,-.11),p(.12,.44,-.25),p(.075,.49,-.40)];radii=[.072,.067,.049,.027,.002]
        elif kind=='demon_forked_horns':
            path=[p(0,0,0),p(.09,.13,-.025),p(.14,.28,-.055),p(.21,.43,-.10),p(.24,.47,-.15)];radii=[.075,.067,.042,.021,.002]
            b.tube('equipment_horn_fork','horn',[p(.105,.19,-.038),p(.06,.34,.005),p(.08,.45,-.015)],[.043,.022,.002],sides=7)
        elif kind=='angel_lyre_horns':
            path=[p(0,0,0),p(.085,.10,-.035),p(.14,.24,-.075),p(.10,.40,-.055),p(-.02,.49,-.01)];radii=[.048,.043,.032,.019,.002]
        elif kind=='angel_antler_horns':
            path=[p(0,0,0),p(.075,.13,-.025),p(.11,.29,-.04),p(.17,.45,-.075)];radii=[.050,.041,.025,.002]
            for start,end in (((.065,.13,-.023),(-.03,.31,.01)),((.102,.25,-.039),(.25,.34,-.09))):
                a=p(*start);c=p(*end);mid=((np.asarray(a)+c)*.5+np.array([0,.02,0])).tolist();b.tube('equipment_horn_antler_branch','horn',[a,mid,c],[.025,.018,.002],sides=7)
        else:
            path=[p(0,0,0),p(.08,.10,-.045),p(.13,.26,-.04),p(.095,.35,-.025)];radii=[.053,.050,.030,.002]
            for dx,dy,dz in ((-.075,.33,.045),(.23,.27,-.12)):
                b.tube('equipment_horn_crown_prong','horn',[p(.065,.09,-.04),p(dx*.65,dy*.68,dz*.6),p(dx,dy,dz)],[.034,.026,.002],sides=7)
        b.tube('equipment_horn_main','horn',path,radii,sides=8)
        b.oval('equipment_horn_root','horn_tip' if angel else 'horn',anchor.tolist(),[.071,.060,.055] if not angel else [.055,.047,.043],sides=8)
        # Relief collars on the horns themselves, not rings covering body seams.
        path=np.asarray(path)
        for index in range(1,len(path)-1):
            centre=path[index];axis=path[min(index+1,len(path)-1)]-path[index-1];axis/=np.linalg.norm(axis)
            side=np.cross(axis,[0,0,1]);side/=np.linalg.norm(side);normal=np.cross(axis,side)
            r=radii[index]*1.06;ring=[(centre+(side*math.cos(a)+normal*math.sin(a))*r).tolist() for a in np.linspace(0,2*math.pi,9)]
            b.tube('equipment_horn_ridge','horn_tip' if angel else 'horn',ring,[.005 if angel else .007]*len(ring),sides=4)
        b.tube('equipment_horn_tip','horn_tip',[path[-2].tolist(),path[-1].tolist()],[radii[-2]*1.01,.002],sides=8)
