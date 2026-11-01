"""Small closed head mesh with explicit facial patches and an anatomical nape.

Edges follow the orbital rim, cheek ridge, nasolabial fold and mandible. No
horizontal row lattice, image triangulation, subdivision or animation solver.
"""
import hashlib
from pathlib import Path
import numpy as np
from tools.creature_workshop.family_faces import orient_faces

REVISION=2

def head(width=.21,jaw=.85,length=1.,nose=.05,eye_y=2.367,mouth_y=2.165):
    vertices=[];names={};faces=[];regions=[]
    def add(name,p):
        x,y,z=p;x*=width/.21
        x*=1-(1-jaw)*.65*float(np.clip((2.26-y)/.18,0,1))
        y=2.335+(y-2.335)*length
        names[name]=len(vertices);vertices.append([x,y,z]);return names[name]
    # Every diagonal below is authored. The left side uses the same indices
    # mirrored, so tessellation cannot choose a different facial plane there.
    def patch(label,points,triangles):
        ids=[names[n] for n in points]
        for tri in triangles:
            faces.append([ids[i] for i in tri]);regions.append(label)
    def quad(label,points):patch(label,points,((0,1,2),(0,2,3)))
    center={'top':(0,2.585,-.018),'forehead':(0,2.49,.180),'glabella':(0,2.414,.18456),'bridge':(0,2.355,.209),'tip':(0,2.278,.239+nose*.15),'base':(0,2.254,.211),'philtrum':(0,2.195,.199),'mouth':(0,mouth_y,.198),'lip':(0,mouth_y-.030,.196),'chin':(0,2.075,.184),'bottom':(0,2.025,.129)}
    for n,p in center.items():add(n,p)
    outline={}
    for side,sign in (('r',1),('l',-1)):
        pts={'crown':(.10,2.555,.082),'forehead_side':(.18,2.480,.145),'forehead_inner':(.085,2.490,.177025),'temple':(.198,2.430,.125),'cheek_edge':(.207,2.278,.073),'jaw_edge':(.186,2.170,.082),'jaw_angle':(.150,2.080,.084),'chin_side':(.080,2.025,.126),'fold':(.081,2.241,.188),'cheek_plane':(.145,2.260,.164),'cheek_lower':(.130,2.180,.168),'alar':(.033,2.269,.218),'tip_side':(.022,2.278,.233+nose*.15),'nasal_side':(.036,2.300,.216),'mouth_corner':(.076,mouth_y,.188),'chin_plane':(.065,2.065,.171),'lip_side':(.071,2.110,.187)}
        inner=((.050,.001,.185),(.070,.019,.186),(.098,.027,.184),(.126,.019,.178),(.148,0,.164),(.128,-.019,.177),(.098,-.027,.184),(.070,-.018,.187))
        outer=((.039,.033,.184035),(.078,.058,.18117),(.121,.058,.181),(.161,.042,.158),(.194,0,.104),(.161,-.061,.168),(.096,-.065,.186),(.040,-.038,.194))
        for i,(x,dy,z) in enumerate(inner):pts['i'+str(i)]=(x,eye_y+dy,z)
        for i,(x,dy,z) in enumerate(outer):pts['o'+str(i)]=(x,eye_y+dy,z)
        pts['socket']=(.098,eye_y,.178)
        for n,(x,y,z) in pts.items():add(side+n,(sign*x,y,z))
        s=lambda n:side+n
        for i in range(8):
            j=(i+1)%8
            a,b,c,d=map(names.get,(s('o'+str(i)),s('o'+str(j)),s('i'+str(j)),s('i'+str(i))))
            faces.extend([[a,b,c],[a,c,d]]);regions.extend(['orbital_rim']*2)
            faces.append([names[s('socket')],names[s('i'+str(i))],names[s('i'+str(j))]]);regions.append('orbital_floor')
        patch('cranial_forehead',['top',s('crown'),s('forehead_side'),s('forehead_inner'),'forehead'],((0,1,4),(1,3,4),(1,2,3)))
        patch('forehead',[s('forehead_inner'),s('forehead_side'),s('temple'),s('o3'),s('o2'),s('o1')],((0,1,2),(0,2,3),(0,3,4),(0,4,5)))
        patch('glabella',['forehead',s('forehead_inner'),s('o1'),s('o0'),'glabella'],((0,1,4),(1,2,3),(1,3,4)))
        patch('lateral_brow',[s('temple'),s('o4'),s('o3')],((0,1,2),))
        patch('nasal_bridge',['glabella',s('o0'),s('o7'),s('nasal_side'),s('tip_side'),'tip','bridge'],((0,1,6),(1,2,6),(2,3,6),(3,4,5),(3,5,6)))
        patch('nasal_cheek',[s('o7'),s('o6'),s('fold'),s('alar'),'base','tip',s('tip_side'),s('nasal_side')],((0,1,2),(0,2,7),(2,3,7),(3,4,6),(4,5,6),(3,6,7)))
        patch('temple',[s('o4'),s('cheek_edge'),s('o5')],((0,1,2),))
        quad('zygomatic',[s('o6'),s('o5'),s('cheek_plane'),s('fold')])
        patch('zygomatic',[s('o5'),s('cheek_edge'),s('jaw_edge'),s('cheek_lower'),s('cheek_plane')],((0,1,4),(1,2,3),(1,3,4)))
        quad('zygomatic',[s('fold'),s('cheek_plane'),s('cheek_lower'),s('mouth_corner')])
        patch('mandible',[s('mouth_corner'),s('cheek_lower'),s('jaw_edge'),s('jaw_angle'),s('chin_plane'),s('lip_side')],((0,1,5),(1,4,5),(1,3,4),(1,2,3)))
        patch('nasolabial',[s('fold'),s('mouth_corner'),'mouth','philtrum','base',s('alar')],((0,1,3),(1,2,3),(0,3,5),(3,4,5)))
        quad('lip',[s('mouth_corner'),s('lip_side'),'lip','mouth'])
        quad('mental',[s('lip_side'),s('chin_plane'),'chin','lip'])
        patch('chin',[s('chin_plane'),s('jaw_angle'),s('chin_side'),'bottom','chin'],((0,1,2),(0,2,4),(2,3,4)))
        outline[side]=['bottom',s('chin_side'),s('jaw_angle'),s('jaw_edge'),s('cheek_edge'),s('o4'),s('temple'),s('forehead_side'),s('crown'),'top']
    boundary=outline['r']+list(reversed(outline['l'][1:-1]))
    # Jaw turns inward into the nape. Occiput rounds outward around ear height,
    # instead of extending a constant rear plane down to the chin.
    ys=np.array([2.025,2.08,2.17,2.28,2.37,2.43,2.48,2.555,2.585])
    zs=np.array([.065,.025,-.065,-.133,-.157,-.159,-.140,-.080,-.030])
    back=[]
    for n in boundary:
        x,y,z=vertices[names[n]];base_y=2.335+(y-2.335)/length
        rear=float(np.interp(base_y,ys,zs));yy=y+(.055 if base_y<2.10 else 0)
        back.append(len(vertices));vertices.append([x*.88,yy,rear])
    for i,n in enumerate(boundary):
        j=(i+1)%len(boundary);a,b=names[n],names[boundary[j]];c,d=back[j],back[i]
        faces.extend([[a,b,c],[a,c,d]]);regions.extend(['cranial_side']*2)
    # A second small ring makes broad skull planes instead of one back spike.
    center=np.array([0,2.365,-.174]);inner_back=[]
    for i in back:
        p=center+(np.asarray(vertices[i])-center)*.55
        p[2]=float(np.interp((p[1]-2.335)/length+2.335,ys,zs))-.006
        inner_back.append(len(vertices));vertices.append(p.tolist())
    for i in range(len(back)):
        j=(i+1)%len(back);faces.extend([[back[i],back[j],inner_back[j]],[back[i],inner_back[j],inner_back[i]]]);regions.extend(['occiput']*2)
    pole=len(vertices);vertices.append(center.tolist())
    for i in range(len(back)):faces.append([inner_back[i],inner_back[(i+1)%len(back)],pole]);regions.append('occiput')
    v=np.asarray(vertices);f=orient_faces(v,np.asarray(faces))
    return v,f,{'schema_version':1,'revision':REVISION,'method':'manually authored vertices and diagonals, mirrored orbital/cheek/nasal/lip quads; curved occiput and nape','landmarks':names,'face_regions':regions,'parameters':{'width':width,'jaw':jaw,'length':length,'nose':nose,'eye_y':eye_y,'mouth_y':mouth_y},'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

def flatten_nose(recipe):
    """Reserve the nose surface for one separately selected nose component."""
    from .constructor_face_fit import surfaces
    for command in surfaces(recipe):
        topology=command.get('head_topology',command.get('authored_primitive',{}).get('head_topology',{}))
        if topology.get('revision')!=REVISION:continue
        v=np.asarray(command['vertices']).copy()
        for name,index in topology['landmarks'].items():
            if name in ('bridge','tip','base') or name[1:] in ('alar','nasal_side','tip_side'):
                v[index,2]=.198
        command['vertices']=v.tolist();command['nose_surface_revision']=REVISION
        command.pop('vertex_normals',None)
    return recipe

def upgrade(recipe):
    """New derived mesh; frozen donor GLB/recipe stays intact."""
    from .constructor_face_fit import surfaces
    from tools.creature_workshop.geometry import mesh
    for command in surfaces(recipe):
        if command.get('head_topology') or command.get('authored_primitive',{}).get('head_topology'):continue
        old,old_faces=mesh(command);w=float(np.max(np.abs(old[:,0])))
        lower=old[(old[:,1]>2.05)&(old[:,1]<2.12)]
        jaw=float(np.clip((np.max(np.abs(lower[:,0])) if len(lower) else w*.78)/w,.45,1))
        length=float(np.clip(np.ptp(old[:,1])/.56,.85,1.2))
        v,f,meta=head(w,jaw,length)
        if 'face_materials' in command:
            old_centers=old[old_faces].mean(axis=1);new_centers=v[f].mean(axis=1)
            nearest=((new_centers[:,None,:]-old_centers[None,:,:])**2).sum(axis=2).argmin(axis=1)
            command['face_materials']=[command['face_materials'][i] for i in nearest]
        command.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),head_topology=meta,authored_landmarks={'eye_y':2.335+(2.367-2.335)*length,'mouth_y':2.335+(2.165-2.335)*length,'brow_y':2.335+(2.400-2.335)*length})
        command.pop('vertex_normals',None)
    flatten_nose(recipe)
    # Only the central scalp shell: leave braids, ponytails and authored locks.
    for command in recipe['commands']:
        if command['part'].split('_')[-2:]!=['hair','crown'] or command.get('scalp_fit_revision'):continue
        v,f=mesh(command);v=v.copy();v[v[:,2]<0,2]*=.75
        command.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),scalp_fit_revision=REVISION)
        command.pop('vertex_normals',None)
    return recipe
