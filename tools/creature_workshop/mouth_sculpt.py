"""Authored lip contours and individual bevelled dental crowns."""
import numpy as np
from .family_faces import orient_faces

REVISION = 1


def _solid(b, name, material, vertices, faces, anchor_z, **metadata):
    vertices = np.asarray(vertices, dtype=float)
    faces = orient_faces(vertices, np.asarray(faces))
    b.solid('anatomy_mouth_'+name, material, vertices.tolist(), faces.tolist(),
            'Authored low-poly lip contours or bevelled dental crown',
            mouth_surface_relief={'schema_version': 1, 'anchor_z': anchor_z},
            mouth_design={'revision': REVISION, **metadata})


def _lip(b, name, width, y, z, seam, height, upper):
    xs=np.array([-1, -.78, -.48, -.22, 0, .22, .48, .78, 1])
    fullness=np.maximum(1-xs*xs, .07)
    # Two peaks and a central philtrum notch on the upper vermilion border.
    cupid=np.array([.07,.56,.87,1,.65,1,.87,.56,.07]) if upper else fullness
    inner=seam.copy()
    outer=inner+(1 if upper else -1)*height*cupid
    vertices=[]
    for row in range(5):
        for i,x in enumerate(xs):
            if row==0:yy=outer[i];zz=z+.0008
            elif row==1:yy=outer[i]*.42+inner[i]*.58;zz=z+.002+fullness[i]*(.013 if upper else .016)
            elif row==2:yy=inner[i];zz=z+.002+fullness[i]*.005
            elif row==3:yy=outer[i];zz=z-.003
            else:yy=inner[i];zz=z-.003
            vertices.append([x*width,y+yy,zz])
    faces=[];n=len(xs)
    for a,c in ((0,1),(1,2),(3,4),(0,3),(2,4)):
        for i in range(n-1):
            j=a*n+i;k=c*n+i
            faces.extend([[j,j+1,k+1],[j,k+1,k]])
    for i in (0,n-1):
        loop=[i,n+i,2*n+i,4*n+i,3*n+i]
        faces.extend([[loop[0],loop[j],loop[j+1]] for j in range(1,4)])
    _solid(b,name,'lip',vertices,faces,z,region='upper_lip' if upper else 'lower_lip',
           contours=['vermilion_border','lip_roll','oral_seam'],width_metres=width*2)


def tooth(b, x, top_y, z, width, height, index, *, lower=False, pointed=False):
    # Broad incisors, narrower lateral incisors, pointed canines. The crown
    # has chamfered corners and a front bevel, rather than a rectangular box.
    contour=np.array([[-.43,0],[.43,0],[.5,.18],[.47,.76],[.30,1],[-.30,1],[-.47,.76],[-.5,.18]])
    if pointed:contour[4:6]=[[.08,1.22],[-.08,1.22]]
    vertices=[]
    for scale,depth in ((.84,-.002),(1,.004),(.80,.010)):
        for xx,yy in contour:
            vertices.append([x+xx*width*scale,top_y+(1 if lower else -1)*yy*height,z+depth])
    faces=[]
    for ring in range(2):
        for i in range(8):
            j=(i+1)%8;a=ring*8+i;c=(ring+1)*8+i
            faces.extend([[a,ring*8+j,(ring+1)*8+j],[a,(ring+1)*8+j,c]])
    for start in (0,16):
        faces.extend([[start,start+i,start+i+1] for i in range(1,7)])
    _solid(b,f'tooth_{"lower" if lower else "upper"}_{index}','mouth_enamel',vertices,faces,z,
           region='tooth',tooth_index=index,row='lower' if lower else 'upper',
           crown='canine' if pointed else 'incisor' if index in (2,3) else 'lateral',
           width_metres=width,height_metres=height)


def mouth(b, kind, race, number, *, y=2.125, z=.23, width=None):
    b.palette.update(mouth_enamel='ded5bd',mouth_cavity='442b29')
    width=width or (.046 if kind=='small' else .087 if kind=='wide' else .067)
    if race in ('wolf','minotaur','boarfolk'):width*=1.25;z=.345;y=2.11
    if race=='elephantfolk':width=.09;z=.29
    xs=np.array([-1,-.78,-.48,-.22,0,.22,.48,.78,1])
    smile=.015 if kind in ('smile','grin','teeth') else -.009 if kind=='stern' else 0
    curve=smile*xs**2
    if kind=='crooked':curve+=xs*.009
    opening=.023 if kind=='grin' else .017 if kind=='teeth' else .012 if kind=='fangs' or race in ('orc','gargoyle') else .0018
    aperture=opening*np.maximum(1-xs**2,.04)
    upper_seam=curve+aperture*.45
    lower_seam=curve-aperture*.55
    # A recessed-looking dark opening is fitted directly to the face surface.
    outline=[[x*width,y+h,z+.001] for x,h in zip(xs,upper_seam)]
    outline.extend([[x*width,y+h,z+.001] for x,h in zip(xs[::-1],lower_seam[::-1])])
    b.panel3('anatomy_mouth_cavity','mouth_cavity',outline,.004)
    b.commands[-1].update(mouth_surface_relief={'schema_version':1,'anchor_z':z},
                          mouth_design={'revision':REVISION,'region':'oral_opening','kind':kind})
    height=.022 if kind=='full' else .007 if kind=='thin' else .012
    _lip(b,'upper_lip',width,y,z,upper_seam,height,True)
    _lip(b,'lower_lip',width,y,z,lower_seam,height*.86,False)
    if kind in ('teeth','grin','fangs') or race in ('orc','gargoyle'):
        tooth_width=width*.27
        for i,fraction in enumerate((-.73,-.45,-.15,.15,.45,.73)):
            canine=i in (0,5)
            top=y+float(np.interp(fraction,xs,upper_seam))-.001
            height=opening*(.58 if canine else .67 if i in (2,3) else .62)
            tooth(b,fraction*width,top,z,tooth_width*(.77 if canine else .90 if i in (1,4) else 1),
                  height,i,pointed=canine and kind=='fangs')
        if kind=='grin':
            for i,fraction in enumerate((-.47,-.16,.16,.47)):
                bottom=y+float(np.interp(fraction,xs,lower_seam))+.001
                tooth(b,fraction*width,bottom,z-.001,tooth_width*.82,opening*.24,i,lower=True)
        if race in ('orc','gargoyle'):
            for i,sign in enumerate((-1,1)):
                tooth(b,sign*width*.78,y-.008,z+.003,width*.25,.037+(number%3)*.005,i,lower=True,pointed=True)
    if kind=='scarred':
        b.tube('anatomy_mouth_lip_scar','shadow',[[width*.60,y-.023,z],[width*.67,y+.025,z]],[.003,.003],sides=4)
        b.commands[-1]['mouth_surface_relief']={'schema_version':1,'anchor_z':z}
    for c in b.commands:
        if c['part'].startswith('anatomy_mouth_'):c['face_feature_frame']={'mouth':y}
