"""Shared wild garments fitted to each race's actual authored limb surfaces."""
import copy
import numpy as np
from tools.creature_workshop.original_constructor import OriginalSculpt,mesh_command
from tools.creature_workshop.family_faces import orient_faces

SHOULDERS={'wild_sleeves':'Кожаные рукава и шнуровка','wild_fur':'Меховые наплечники','wild_bone':'Костяные наплечники'}
BELTS={'wild_shorts':'Дикие штаны до колен','wild_trousers':'Длинные походные штаны','wild_skirt':'Юбка из шкур и кости'}
IDS={*SHOULDERS,*BELTS}


def shell(c,part,material,padding=.021):
 v,f=mesh_command(c);v=np.asarray(v).copy()
 # Vertex normals from the actual authored surface, including bent limbs.
 normals=np.zeros_like(v)
 fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
 for k in range(3):np.add.at(normals,f[:,k],fn)
 normals/=np.maximum(np.linalg.norm(normals,axis=1),1e-9)[:,None]
 v+=normals*padding
 result={**copy.deepcopy(c),'part':part,'material':material,'op':'indexed_mesh','vertices':v.tolist(),'faces':f.tolist(),'wild_garment_revision':1,'surface_padding_metres':padding,'purpose':'Одежда по поверхности собственной расовой анатомии'}
 for key in ('face_materials','vertex_normals','vertex_color_factors','fur_uv','fur_texture','pelt_surface_revision'):result.pop(key,None)
 return result


def apply(recipe,settings,slot):
 upper=settings['decor']['shoulders'];lower=settings['decor']['belt']
 if upper not in SHOULDERS and lower not in BELTS:return
 source=[c for c in recipe['commands'] if not c['part'].startswith(('ornament_','wild_'))]
 palette={'skin':'9b8060','hair':'67533a','iris':'9a9566','cloth':'77684f','accent':'c6b288','metal':'8b938b','leather':'68513a','secondary':'a59676'}
 for k in palette:
  palette[k]=(settings['colors'].get(k) or '#'+recipe['palette'].get(k,palette[k])).lstrip('#')
 b=OriginalSculpt({'id':'wild-garments-v1','palette':palette});b.slot=slot;b.stage=4
 new=[]
 def add_shell(c,name,mat,padding=.024):new.append(shell(c,name,'wild_'+mat,padding))
 if slot.endswith('_arm') and upper in SHOULDERS:
  arm=[c for c in source if c['part'] in ('racial_upper_arm','racial_forearm') or 'upper_' in c['part'] or 'fore_' in c['part'] or c['part'].endswith(('_upper','_fore'))]
  # Elemental segments share their anatomy; skin commands only avoid emissive seams.
  arm=[c for c in arm if c['material'] in ('skin','dark','bone')]
  for c in arm:
   if upper=='wild_sleeves':add_shell(c,'wild_leather_sleeve','leather',.031)
   elif 'upper' in c['part']:
    from scipy.spatial import ConvexHull
    v,f=mesh_command(c);lo,hi=v[:,1].min(),v[:,1].max();cut=lo+(hi-lo)*.40
    points=list(v[v[:,1]>=cut])
    for face in f:
     tri=v[face]
     for edge in range(3):
      p0,p1=tri[edge],tri[(edge+1)%3]
      if (p0[1]<cut<=p1[1]) or (p1[1]<cut<=p0[1]):points.append(p0+(p1-p0)*((cut-p0[1])/(p1[1]-p0[1])))
    vv=np.unique(np.asarray(points),axis=0)
    if len(vv)>=4:
     ff=orient_faces(vv,ConvexHull(vv).simplices)
     partial={**c,'op':'indexed_mesh','vertices':vv.tolist(),'faces':ff.tolist()};add_shell(partial,'wild_shoulder_hide','secondary',.038)
  if arm:
   allv=np.concatenate([mesh_command(c)[0] for c in arm]);cx=float(allv[:,0].mean())
   if upper=='wild_sleeves':
    fore=[c for c in arm if 'fore' in c['part']]
    if fore:
     v=np.concatenate([mesh_command(c)[0] for c in fore]);lo,hi=v[:,1].min(),v[:,1].max()
     for y in np.linspace(lo+.06,hi-.04,4):
      band=v[np.abs(v[:,1]-y)<.07];q=band[np.argmax(band[:,2])] if len(band) else v[np.argmax(v[:,2])];x=float(q[0]);z=float(q[2])+.038
      b.tube('wild_sleeve_lace','accent',[[x-.028,y-.018,z],[x+.028,y+.018,z]],[.006,.006],sides=5)
   else:
    v=allv;top=float(v[:,1].max());band=v[v[:,1]>top-.18];center=band.mean(0);center[1]=top-.10;center[2]=float(band[:,2].max())+.029
    if upper=='wild_bone':
     for j in range(3):
      p=center+np.array([(j-1)*.054,-.052,.0]);b.tube('wild_shoulder_bone','bone',[p.tolist(),(p+np.array([0,.075,.018])).tolist(),(p+np.array([0,.163+(j%2)*.04,.025])).tolist()],[.028,.033,.005],sides=7)
    else:
     for j in range(7):
      p=center+np.array([(j-3)*.035,-.025,0]);b.tube('wild_shoulder_fur','secondary',[p.tolist(),(p+np.array([0,-.13,.029])).tolist()],[.024,.001],sides=5)
 if slot.endswith('_leg') and lower in ('wild_shorts','wild_trousers'):
  for c in source:
   name=c['part']
   if ('thigh' in name or 'shin' in name and lower=='wild_trousers' or name in ('elemental_leg_slab','ice_leg_axis','ice_leg_plate','wind_leg_axis','wind_leg_spiral','wind_leg_blade')) and c['material']=='skin' or name=='racial_thigh' or name=='racial_shin' and lower=='wild_trousers':
    if lower=='wild_shorts' and mesh_command(c)[0][:,1].mean()<.65:continue
    add_shell(c,'wild_ragged_trousers','cloth',.035)
 if slot=='torso' and lower in BELTS:
  torso=[c for c in source if c['part'] in ('racial_torso','native_waist_wrap','ancient_monolith','stone_abdomen','volcanic_abdomen','elemental_pelvis')]
  if torso:
   vv=np.concatenate([mesh_command(c)[0] for c in torso]);band=vv[(vv[:,1]>.98)&(vv[:,1]<1.23)]
   if not len(band):band=vv
   w=float(np.abs(band[:,0]).max())+.028;d=float(np.abs(band[:,2]).max())+.032
   b.loft('wild_hide_waistband','leather',[[1.045,0,0,w,d],[1.115,0,0,w,d]],sides=12)
   if lower=='wild_skirt':
    for j in range(10):
     a=2*np.pi*j/10;n=np.array([np.cos(a),0,np.sin(a)]);t=np.array([-np.sin(a),0,np.cos(a)])
     p=np.array([n[0]*w,1.085,n[2]*d]);q=p+np.array([0,-.24-(j%3)*.025,0])+n*.03
     front=np.array([p-t*.072,p+t*.072,q+t*.064,q-t*.057]);verts=np.concatenate([front+n*.008,front-n*.008])
     faces=np.array([[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]])
     b.commands.append({'id':f'wild-skirt-panel-{j}','slot':slot,'stage':4,'part':'wild_hide_skirt_panel','material':'cloth','op':'indexed_mesh','vertices':verts.tolist(),'faces':orient_faces(verts,faces).tolist(),'purpose':'Отдельная объёмная полоса шкуры вокруг расовых бёдер'})
   for s in (-1,1):
    b.tube('wild_belt_bone_clasp','bone',[[s*.078,1.12,d+.009],[s*.098,1.015,d+.015]],[.023,.014],sides=6)
    b.tube('wild_belt_tie','leather',[[s*.11,1.05,d+.014],[s*.135,.94,d+.024]],[.012,.007],sides=5)
 for c in b.commands:
  v,f=mesh_command(c);new.append({**c,'op':'indexed_mesh','vertices':v.tolist(),'faces':orient_faces(v,f).tolist(),'material':'wild_'+c['material'],'wild_garment_revision':1})
 if new:
  race=recipe.get('own_body_design',{}).get('race')
  for j,c in enumerate(new):
   c['id']=f'wild-garment-{slot}-{j}'
   if race:c['native_anatomy']=race
  recipe['commands'].extend(new);recipe['palette'].update({'wild_'+k:v for k,v in b.palette.items()});recipe['wild_garments']={'schema_version':1,'shoulders':upper,'belt':lower,'fit':'selected race-owned mesh surface'}
