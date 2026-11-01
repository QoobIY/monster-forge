"""Deterministic, neutral fur albedo; embedded in a single-primitive slot GLB."""
from functools import lru_cache
from io import BytesIO
import math
import numpy as np
from PIL import Image

@lru_cache(maxsize=5)
def texture(kind='bear_pelt'):
 if kind=='tiger_stripes':return tiger_stripes()
 if kind in {'wolf_pelt','animal_bear_pelt'}:return animal_pelt(kind)
 size=256;canvas=np.ones((size,size),dtype=float);rng=np.random.default_rng(317 if kind=='bear_pelt' else 911)
 # Curved, tapered strokes overlap in staggered courses; neutral values tint
 # with COLOR_0, so editing skin color still works in the constructor.
 for row in range(5):
  for j in range(42 if kind=='bear_pelt' else 54):
   x0=(j+.5*(row%2))*size/(42 if kind=='bear_pelt' else 54)+rng.uniform(-2,2)
   y0=row*size/5+rng.uniform(-15,15);length=rng.uniform(38,71) if kind=='bear_pelt' else rng.uniform(58,91)
   strength=rng.uniform(.10,.27);bend=rng.uniform(-4,4)
   for k in range(int(length)):
    t=k/length;cx=x0+bend*np.sin(t*np.pi)*.7;cy=int(y0+k)%size
    width=(1.0 if kind=='bear_pelt' else .65)*(1-t)*rng.uniform(.9,1.2)
    for off in range(-2,3):
     x=int(round(cx))+off;distance=abs(x-cx)
     darkness=strength*(1-t*.7)*max(0,1-distance/(width+1))
     canvas[cy,x%size]=min(canvas[cy,x%size],1-darkness)
 # Decorations and bare anatomy use the reserved neutral texel.
 canvas[:5,:5]=1
 image=np.uint8(np.clip(canvas*255,0,255));rgb=np.repeat(image[:,:,None],3,axis=2);out=BytesIO();Image.fromarray(rgb).save(out,format='PNG')
 return rgb,out.getvalue()

def recipe_uvs(recipe):
 uvs=[];textured=False;kind='bear_pelt'
 for c in recipe['commands']:
  if 'fur_uv' in c:
   uv=np.asarray(c['fur_uv']);f=np.asarray(c['faces']);tri=uv[f].copy()
   # Unwrap triangles crossing the cylinder seam before flattening.
   span=np.ptp(tri[:,:,0],axis=1);mask=span>.5
   tri[mask,:,0]+=tri[mask,:,0]<.5
   uvs.extend(tri.reshape(-1,2));textured=True;kind=c['fur_texture']['kind']
  else:
   from tools.creature_workshop.geometry import mesh
   _,f=mesh(c);uvs.extend([[.002,.002]]*(len(f)*3))
 return np.asarray(uvs,dtype='<f4'),kind if textured else None


def tiger_stripes():
 size=512;u=np.linspace(0,1,size)[None,:];v=np.linspace(0,1,size)[:,None]
 canvas=np.ones((size,size));taper=np.clip(np.sin(np.pi*u)**.7,0,1)
 # Narrow, irregular branches taper towards the white underside; no polygon-sized checkerboard.
 for j in range(11):
  centre=(j+.45)/11 + .011*np.sin(u*9+j*1.7)+.009*np.sin(u*19+j*.9)
  width=(.010+.007*(.5+.5*np.sin(j*2.7)))*taper
  stroke=np.clip((width-np.abs(v-centre))*350+0.5,0,1)
  canvas=np.minimum(canvas,1-stroke*.94)
  if j%3==1:
   branch=centre+.031*(u-.5);w=.006*taper
   mask=np.clip((w-np.abs(v-branch))*350+.5,0,1)*(u>.35)*(u<.72)
   canvas=np.minimum(canvas,1-mask*.94)
 canvas[:10,:10]=1
 rgb=np.repeat(np.uint8(np.clip(canvas*255,0,255))[:,:,None],3,axis=2);out=BytesIO();Image.fromarray(rgb).save(out,format='PNG');return rgb,out.getvalue()


def animal_pelt(kind):
 """Matte, directional broad painted locks; neutral albedo multiplies the coat colour."""
 size=256;canvas=np.ones((size,size),float);rng=np.random.default_rng(741 if kind=='wolf_pelt' else 219)
 for row in range(6):
  for j in range(24 if kind=='wolf_pelt' else 28):
   x0=(j+.5*(row%2))*size/(24 if kind=='wolf_pelt' else 28)+rng.uniform(-3,3);y0=row*size/6+rng.uniform(-15,15)
   length=rng.uniform(25,48) if kind=='animal_bear_pelt' else rng.uniform(35,62);width=rng.uniform(2.0,3.8);bend=rng.uniform(-4,4);strength=rng.uniform(.12,.24)
   for k in range(int(length)):
    t=k/length;cx=x0+bend*math.sin(t*math.pi);yy=int(y0+k)%size;ww=width*(1-t)**.7
    for off in range(-5,6):
     xx=int(round(cx))+off;distance=abs(xx-cx);darkness=strength*(.65+.35*math.sin(t*math.pi))*max(0,1-distance/max(ww,.2))
     canvas[yy,xx%size]=min(canvas[yy,xx%size],1-darkness)
 canvas[:5,:5]=1;rgb=np.repeat(np.uint8(np.clip(canvas*255,0,255))[:,:,None],3,axis=2);out=BytesIO();Image.fromarray(rgb).save(out,format='PNG');return rgb,out.getvalue()
