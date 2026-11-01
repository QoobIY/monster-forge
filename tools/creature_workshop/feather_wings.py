"""Hand-authored feather fans: curved sections, overlapping coverts and flight feathers."""
import numpy as np
from .family_faces import orient_faces


def feather(b,name,material,start,end,width,bend=.02):
    start=np.asarray(start,float);end=np.asarray(end,float);delta=end-start
    side=np.array([-delta[1],delta[0],0.]);side/=np.linalg.norm(side)
    fractions=(0,.18,.44,.76,1);breadths=(.28,.84,1,.72,.035)
    vertices=[];centres=[]
    for t,w in zip(fractions,breadths):
        centre=start+delta*t+side*bend*4*t*(1-t)
        centre[2]+=.012*np.sin(np.pi*t);centres.append(centre)
        tangent=delta+side*bend*4*(1-2*t)
        normal=np.array([-tangent[1],tangent[0],0.]);normal/=np.linalg.norm(normal)
        for a in np.linspace(0,2*np.pi,6,endpoint=False):
            vertices.append(centre+normal*np.cos(a)*width*w*.5+np.array([0,0,np.sin(a)*max(.001,width*.12*w)]))
    faces=[]
    for ring in range(4):
        for i in range(6):
            a=ring*6+i;c=ring*6+(i+1)%6;faces.extend([[a,c,c+6],[a,c+6,a+6]])
    for i in range(1,5):faces.extend([[0,i+1,i],[24,24+i,24+i+1]])
    vertices=np.asarray(vertices);faces=np.asarray(orient_faces(vertices,np.asarray(faces)))
    b.commands.append({'id':name+'-'+str(len(b.commands)),'slot':b.slot,'stage':b.stage,
        'part':name,'material':material,'op':'indexed_mesh','vertices':vertices.tolist(),'faces':faces.tolist(),
        'feather_contour':{'schema_version':1,'sections':list(fractions),'width_profile':list(breadths),
            'curvature_metres':bend,'role':name},'purpose':'Curved lenticular feather with tapered contour and raised central keel'})


def helmet_wings(b,anchor,sign):
    first=len(b.commands)
    def p(x,y,z=.025):return [anchor[0]+sign*x,anchor[1]+y,anchor[2]+z]
    b.palette.update(angel_feather='eceadf',angel_covert='d5dbd6',angel_shadow='a7b5ba')
    b.panel3('equipment_helmet_angel_shoulder','angel_shadow',
        [p(.0,-.02),p(.10,.00),p(.21,.14),p(.27,.34),p(.23,.47),p(.16,.38),p(.08,.15)],.024)
    tips=[(.40,.15),(.44,.23),(.45,.32),(.43,.41),(.39,.49),(.33,.56),(.26,.61)]
    for i,(x,y) in enumerate(tips):
        feather(b,'equipment_helmet_angel_primary','angel_feather',p(.10+i*.017,.065+i*.034,.037),
            p(x,y,.033),.083-i*.003,bend=-sign*.028)
    for i in range(6):
        feather(b,'equipment_helmet_angel_secondary','angel_covert',p(.033+i*.025,.015+i*.044,.055),
            p(.22+i*.023,.055+i*.072,.055),.070,bend=-sign*.017)
    for i in range(7):
        feather(b,'equipment_helmet_angel_covert','angel_feather',p(.018+i*.018,.004+i*.047,.075),
            p(.11+i*.021,.045+i*.053,.075),.053,bend=-sign*.009)
    # The feather fan is a small swept-back temple ornament. Rotate the whole
    # solid assembly, including the shoulder, so layers retain their depth.
    from .geometry import mesh
    angle=np.deg2rad(65)*sign
    rotation=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
    pitch=np.deg2rad(-35)
    rotation=np.array([[1,0,0],[0,np.cos(pitch),-np.sin(pitch)],[0,np.sin(pitch),np.cos(pitch)]])@rotation
    for c in b.commands[first:]:
        v,f=mesh(c);v=(v-np.asarray(anchor))@rotation.T*.58+anchor
        c.update(op='indexed_mesh',vertices=v.tolist(),faces=f.tolist(),
            helmet_wing_fit={'schema_version':1,'scale':.58,'yaw_degrees':65*sign,'pitch_degrees':-35,'forward_axis':'+Z','direction':'backward'})


def raven_wings(b,z):
    b.palette.update(cloth='22272f',secondary='35414e',accent='465361',metal='252c34')
    for sign in (-1,1):
        def p(x,y,depth=0):return [sign*x,y,z+depth]
        # A broad bent shoulder/forearm carries the fan; no exposed metal rail.
        b.panel3('raven_wing_shoulder','cloth',[p(.14,1.76),p(.30,2.06),p(.59,2.25),p(.94,2.30),
            p(1.23,2.21),p(1.09,1.99),p(.69,1.49),p(.26,1.40)],.052)
        tips=[(1.25,1.02),(1.45,1.12),(1.62,1.31),(1.76,1.53),(1.83,1.76),(1.81,1.99),(1.70,2.17)]
        for i,(x,y) in enumerate(tips):
            feather(b,'raven_primary_feather','cloth',p(.80+i*.045,2.05+i*.018,.012),
                p(x,y,.005),.18-i*.007,bend=sign*.065)
        for i in range(8):
            feather(b,'raven_secondary_feather','cloth',p(.27+i*.102,1.92+i*.029,.020),
                p(.34+i*.116,1.00+i*.047,.015),.158,bend=sign*.030)
        for row in range(2):
            for i in range(9):
                x=.24+i*.117;y=1.89+.15*np.sin(i*np.pi/12)+row*.12
                feather(b,'raven_covert_feather','secondary' if row else 'cloth',p(x,y,.040+row*.018),
                    p(x+.105,y-.28+row*.035,.047+row*.018),.122-row*.015,bend=sign*.018)
        for i in range(4):
            feather(b,'raven_root_feather','secondary',p(.15,1.82+i*.055,.09),p(.33+i*.04,1.53+i*.10,.08),.14,bend=sign*.025)
