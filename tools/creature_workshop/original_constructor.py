"""Current constructor sculpture primitives on the shared MOM bind pose."""
from __future__ import annotations
import math
import copy
import numpy as np
from .geometry import mesh
from .reference_sculpt import Sculpt

def world_bind():
    from monsterforge.runtime import bind_positions, load_bind_skeleton
    return bind_positions(load_bind_skeleton())


class OriginalSculpt(Sculpt):
    def __init__(self, design):
        pal = copy.deepcopy(design['palette'])
        rgb = np.array(list(bytes.fromhex(pal['skin'])))
        pal.update(shadow=''.join(f'{v:02x}' for v in np.round(rgb*.63).astype(int)),
                   lip=''.join(f'{v:02x}' for v in np.round(rgb*.72).astype(int)),
                   pupil='272a2b',sclera='d4d1bc',bone='cbc5ad',dark='33383b',
                   hair_light=''.join(f'{v:02x}' for v in np.minimum(np.round(np.array(list(bytes.fromhex(pal['hair'])))*1.16),255).astype(int)))
        super().__init__(design['id'], pal)
        self.design=design
        self.transform=(0,0,1,0,0)

    def panel3(self,name,material,points,depth=.035):
        front=[p[2] for p in points]
        self.panel(name,material,[[p[0],-p[1]] for p in points],front,
                   [z-depth for z in front],name.replace('_',' '),bevel=.09,bulge=.006)
        # Coordinates are authored metres, not image observations.
        self.commands[-1].pop('source_outline_pixels',None)
        self.commands[-1].pop('source_mapping',None)
        self.commands[-1]['authored_outline_metres']=points

    def tube(self,part,material,path,radii,purpose=None,sides=6):
        super().tube(part,material,path,radii,purpose or part.replace('_',' '),sides)

    def oval(self,part,material,center,radii,purpose=None,sides=8):
        super().oval(part,material,center,radii,purpose or part.replace('_',' '),sides)

    def loft(self,part,material,stations,purpose=None,sides=8):
        super().loft(part,material,stations,purpose or part.replace('_',' '),sides)

    def box(self,part,material,center,size,purpose=None):
        super().box(part,material,center,size,purpose or part.replace('_',' '))


def mesh_command(c):
    from .geometry import mesh
    return mesh(c)
