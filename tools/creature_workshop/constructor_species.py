"""Authorized non-humanoid authoring contracts; no substitute animation solver.

The MOM SDK currently supplies humanoid_v1 only. These static modular layouts
export parts, fixed join anchors and provenance, and explicitly do not claim
SDK skinning or runtime animation support.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from pathlib import Path
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces
from tools.creature_workshop.geometry import compile_recipe,export_glb,validate
from monsterforge.paths import ROOT,STYLE_PATH

OUTPUT=ROOT/'media/constructor/species/v2'
CONFIG=ROOT/'config/constructor_species_v2.json'
QUAD=('head','torso','front_left_leg','front_right_leg','hind_left_leg','hind_right_leg','tail')
SPIDER=('head','torso','abdomen',*[f'{s}_leg_{i}' for s in ('left','right') for i in range(1,5)])
FLY=('head','torso','left_wing','right_wing','left_leg','right_leg','tail')
CONTRACTS={
 'quadruped_authoring_v1':QUAD,'arachnid_authoring_v1':SPIDER,
 'scorpion_authoring_v1':(*SPIDER,'left_claw','right_claw','tail'),
 'avian_authoring_v1':FLY,'chiropteran_authoring_v1':FLY,
 'dragon_authoring_v1':(*QUAD,'left_wing','right_wing')}
SPECIES={
 'beast-wolf':('Волки · четвероногие','quadruped_authoring_v1','wolf'),
 'beast-boar':('Дикие кабаны','quadruped_authoring_v1','boar'),
 'beast-bear':('Медведи','quadruped_authoring_v1','bear'),
 'beast-stag':('Олени','quadruped_authoring_v1','stag'),
 'spider':('Пауки','arachnid_authoring_v1','spider'),
 'scorpion':('Скорпионы','scorpion_authoring_v1','scorpion'),
 'sky-bird':('Крылатые птицы','avian_authoring_v1','bird'),
 'sky-bat':('Летучие мыши','chiropteran_authoring_v1','bat'),
 'sky-dragon':('Крылатые драконы','dragon_authoring_v1','dragon')}
PALETTES=[('748177','b9b09a'),('9c6954','ccb276'),('697b8d','acc2c6'),('504d65','a394bc'),('939b87','d0d1b6'),('566b60','c7ac73'),('8c7c56','bc965e'),('496c70','9bbbac'),('af9c80','e2d0a5'),('713e45','bf8857')]
