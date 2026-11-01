"""Open cloth hoods authored around the selected skull, with a sewn face opening."""
import math
import numpy as np
from tools.creature_workshop.family_faces import orient_faces
from tools.creature_workshop.geometry import mesh

DESCRIPTIONS={
 'cloth_hood':'Тканевый капюшон с закрывающим лоб тканевым козырьком, боковыми отворотами и золотым растительным узором по окантовке: слегка вытянутая назад закрытая макушка, мягкие широкие складки и затылок, открытое лицо, удлинённые боковые складки, сужающиеся к шее, и прошитый край. Волосы под тканью укладываются внутрь; свободные косы сохраняются.',
 'deep_hood':'Глубокий капюшон с нависающим верхом, двойным тканевым козырьком и плетёным ромбическим узором: закрытая вытянутая макушка, цельная оболочка со складками, широкий двойной отворот, выступающий над лбом козырёк из ткани, длинные боковые складки, спадающие к шее, и тёмная подкладка. Лицо и глаза остаются открыты.'}

def author(b,kind,vertices,eye,hair):
    low,high=vertices.min(0),vertices.max(0);top=high[1];chin=low[1];cz=(low[2]+high[2])*.5
    deep=kind=='deep_hood';width=max(.18,float(np.abs(vertices[:,0]).max()))+(.085 if deep else .065)
    depth=max(.18,float((high[2]-low[2])*.5))+.085
    base=max(1.91,chin-.15)
    # One sewn outer surface, from the hanging hem to a capped crown.
    # The brow bridge shares vertices with the hood; it is not a second roof
    # suspended inside an open dome.
    brow=vertices[vertices[:,1]>=eye+.035]
    brow_z=float(brow[:,2].max()) if len(brow) else cz+depth*.65
    reach=brow_z+(.095 if deep else .068)
    opening=1.14;count=20;angles=np.linspace(opening,2*math.pi-opening,count+1)
    span=width*math.sin(opening)
    def edge(t):
        return np.array([t*span,eye+.078+(.090 if deep else .082)*(1-t*t),reach-.052*abs(t)])
    outer=[];rows=[]
    # The side panels taper into a long, uneven fabric hem. Broad pleats are
    # part of this surface and follow its drape instead of floating tubes.
    for row,(y,scale) in enumerate(((base,.68),(chin-.025,.91),(eye-.045,1.02))):
        ids=[]
        for j,a in enumerate(angles):
            u=j/count;fold=math.sin(6*math.pi*u)*(.014 if row==0 else .022)
            x=math.sin(a)*(width*scale+fold)
            z=cz+math.cos(a)*(depth*scale+fold)
            frontness=abs(2*u-1)**5
            z+=(reach-.052-(cz+depth*math.cos(opening)))*frontness
            yy=y-(.046*frontness if row==0 else .012*math.sin(4*math.pi*u))
            ids.append(len(outer));outer.append([x,yy,z])
        rows.append(ids)
    ring=[]
    for j,a in enumerate(angles):
        u=j/count;rise=math.sin(math.pi*u)**.72
        q=np.array([width*math.sin(a),edge(1)[1]+(top-.025-edge(1)[1])*rise,cz+depth*math.cos(a)])
        q[2]+=(edge(1)[2]-(cz+depth*math.cos(opening)))*abs(2*u-1)**5
        if j==0:q=edge(1)
        elif j==count:q=edge(-1)
        ring.append(len(outer));outer.append(q.tolist())
    columns=np.linspace(-1,1,9)
    for t in columns[1:-1]:ring.append(len(outer));outer.append(edge(t).tolist())
    rows.append(ring[:count+1]);faces=[]
    for arow,brow in zip(rows,rows[1:]):
        for j in range(count):
            a,c=arow[j:j+2];d,e=brow[j:j+2];faces.extend([[a,c,d],[c,e,d]])
    crown=[]
    for k in ring:
        q=np.asarray(outer[k]);frontness=max(0,(q[2]-cz)/max(reach-cz,.01))
        # A swept, gently peaked seam gives cloth a soft rearward silhouette.
        v=[q[0]*.62,top+.070-.050*frontness,cz+(q[2]-cz)*.52-.024]
        crown.append(len(outer));outer.append(v)
    for j,a in enumerate(ring):
        c=ring[(j+1)%len(ring)];d=crown[j];e=crown[(j+1)%len(ring)]
        faces.extend([[a,c,d],[c,e,d]])
    peak=len(outer);outer.append([0,top+(.155 if deep else .128),cz-.095])
    for j,a in enumerate(crown):faces.append([a,crown[(j+1)%len(crown)],peak])
    outer=np.asarray(outer);inner=outer.copy()
    inner[:,0]*=1-.019/width;inner[:,2]=cz+(inner[:,2]-cz)*(1-.019/depth)
    upper=inner[:,1]>eye+.04;inner[upper,1]-=.019
    n=len(outer);v=np.concatenate([outer,inner]);f=list(faces)+[[n+a,n+c,n+b] for a,b,c in faces]
    # Seal exactly the true outer boundary, including the front brow opening.
    from collections import Counter
    counts=Counter(tuple(sorted(e)) for tri in faces for e in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])))
    for (a,c),number in counts.items():
        if number==1:f.extend([[a,n+a,n+c],[a,n+c,c]])
    b.commands.append(dict(id='hood-shell',slot='head',stage=4,part='equipment_hood_shell',material='cloth',op='indexed_mesh',vertices=v.tolist(),faces=orient_faces(v,np.asarray(f)).tolist(),purpose='Цельная тканевая оболочка: козырёк, боковые складки и закрытая вытянутая макушка соединены общей сеткой без разрывов.'))
    front=[edge(t) for t in columns]
    # A turned-over fabric hem presents a real broad surface for embroidery.
    strips=np.asarray([[*(q+[0,.028,.005]),*(q+[0,-.015,.009])] for q in front]).reshape(-1,3)
    rear=strips.copy();rear[:,2]-=.012
    vv=np.concatenate([strips,rear]);n=len(strips);ff=[]
    for k in range(len(front)-1):
        a=k*2;c=a+2
        ff.extend([[a,c,c+1],[a,c+1,a+1],[n+a,n+c+1,n+c],[n+a,n+a+1,n+c+1],
                   [a,n+a,n+c],[a,n+c,c],[a+1,c+1,n+c+1],[a+1,n+c+1,n+a+1]])
    ff.extend([[0,1,n+1],[0,n+1,n],[n-2,2*n-2,2*n-1],[n-2,2*n-1,n-1]])
    b.commands.append(dict(id='hood-visor-fold',slot='head',stage=4,part='equipment_hood_visor_fold',material='secondary',op='indexed_mesh',vertices=vv.tolist(),faces=orient_faces(vv,np.asarray(ff)).tolist()))
    b.tube('equipment_hood_visor_edge','accent',[(q+[0,-.012,.012]).tolist() for q in front],[.005 if not deep else .007]*len(front),sides=5)
    for sign in (-1,1):
        q=edge(sign)
        fold=np.array([q+[0,.018,0],q+[sign*.030,-.045,-.015],q+[sign*.010,-.18,-.026],q+[-sign*.025,-.235,-.013],q+[-sign*.042,-.12,.008]])
        b.panel3('equipment_hood_side_lapel','secondary',fold.tolist(),.022)
        b.tube('equipment_hood_lapel_trim','accent',[(fold[k]+[0,0,.014]).tolist() for k in (0,1,2,3)],[.005,.006,.006,.003],sides=5)
        # Long embroidered stem with two angular leaves follows this fold.
        stem=[(fold[0]*.80+fold[4]*.20)+[0,0,.029],(fold[1]+fold[4])*.5+[0,0,.029],(fold[2]+fold[3])*.5+[0,0,.029]]
        b.tube('equipment_hood_leaf_stem','accent',[q.tolist() for q in stem],[.0045]*3,sides=5)
        for k in (0,1):
            a=stem[k];d=stem[k+1];mid=(a+d)*.5
            leaf=[a,mid+[sign*.019,-.007,.001],d,mid+[-sign*.013,.003,.001],a]
            b.tube('equipment_hood_leaf_outline','accent',[q.tolist() for q in leaf],[.0035]*5,sides=5)
    # Five readable interlaced diamonds on the front-facing hem, rather than
    # tiny scattered stitches. Every point uses the same curved canopy edge.
    for centre in (-.70,-.35,0,.35,.70):
        half=.10 if deep else .085
        path=[]
        for t,dy in ((centre-half,.007),(centre,.023),(centre+half,.007),(centre,-.009),(centre-half,.007)):
            path.append((edge(t)+[0,dy,.023]).tolist())
        b.tube('equipment_hood_woven_diamond','accent',path,[.0038 if deep else .0032]*len(path),sides=5)
    # Keep each lock a solid volume. Covered locks tuck beneath the cloth;
    # braid tails below the hem stay visible, as with existing fitted helmets.
    for c in hair:
        h,f=mesh(c);h=h.copy()
        if h[:,1].min()<base-.02:continue
        radial=np.linalg.norm(h[:,[0,2]]-[0,cz],axis=1);factor=min(.74,(width-.06)/max(float(radial.max()),1e-9))
        h[:,0]*=factor;h[:,2]=cz+(h[:,2]-cz)*factor
        centre=eye+.05;vertical=min(.80,(top-.04-centre)/max(float(h[:,1].max()-centre),1e-9));vertical=max(.08,vertical)
        h[:,1]=centre+(h[:,1]-centre)*vertical
        c.update(op='indexed_mesh',vertices=h.tolist(),faces=f.tolist(),helmet_hair_revision={'schema_version':1,'method':'covered locks tucked beneath hood; hanging braids preserved'})
