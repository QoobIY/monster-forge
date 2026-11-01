"""Hand-shaped beard masses with broad flowing facets, not a cone under the chin."""
import numpy as np


def sideburns(b,kind,z=.23):
    for sign in (-1,1):
        if kind=='sideburns':
            # Narrow shaped sideburns turn forward along the cheek instead of
            # hanging as straight rectangular beams beside the ears.
            b.loft('beard_swept_sideburn','hair',[
                [2.106,sign*.155,z-.045,.008,.011],
                [2.153,sign*.175,z-.052,.022,.023],
                [2.210,sign*.192,z-.075,.026,.028],
                [2.281,sign*.198,z-.103,.022,.025],
                [2.340,sign*.190,z-.126,.013,.020]],sides=7)
            b.loft('beard_sideburn_lock','hair_light',[
                [2.135,sign*.173,z-.028,.008,.009],
                [2.188,sign*.197,z-.047,.013,.013],
                [2.265,sign*.205,z-.084,.009,.013]],sides=5)
        else:
            # Mutton chops spread across the lower cheek and jaw; the mouth
            # and central chin remain open, so this is a different silhouette.
            outline=[[.182,2.337,z-.124],[.211,2.331,z-.109],
                [.214,2.247,z-.072],[.223,2.184,z-.018],
                [.192,2.117,z+.014],[.141,2.085,z+.032],
                [.076,2.072,z+.046],[.065,2.113,z+.048],
                [.135,2.153,z+.024],[.164,2.213,z-.051]]
            b.panel3('beard_mutton_cheek','hair',[[sign*x,y,depth] for x,y,depth in outline],.028)
            for i in range(3):
                x=.115+i*.029
                b.loft('beard_mutton_falling_lock','hair_light' if i==1 else 'hair',[
                    [2.067+i*.014,sign*(x-.019),z+.041-i*.013,.014,.014],
                    [2.123+i*.009,sign*x,z+.042-i*.014,.023,.024],
                    [2.185+i*.018,sign*(x+.009),z+.011-i*.018,.014,.013]],sides=6)


def sculpt(b,kind,z=.23):
    long=kind=='long'
    # Columns alternate broad lock ridges and shallow valleys. Row contours
    # follow the cheek, jaw and falling locks, rather than horizontal squares.
    columns=np.array([-1,-.80,-.63,-.43,-.22,0,.22,.43,.63,.80,1])
    rows=[(.151,2.132,.075,.245),(.169,2.075,.058,.302),
          (.150,2.025,.040,.318),(.126,1.955 if long else 1.982,.035,.304),
          (.091,1.857 if long else 1.947,.038,.277)]
    if long:rows.append((.044,1.766,.032,.248))
    front=[]
    for row,(width,y,lift,depth) in enumerate(rows):
        for col,u in enumerate(columns):
            # Broad rounded lower lobes: a long beard has three blunt ends,
            # while the full beard has a wide, scalloped jaw silhouette.
            scallop=(.010 if col%2 else -.004) if row==len(rows)-1 else 0
            ridge=.010 if col in (2,4,6,8) else -.003 if col in (3,7) else 0
            front.append([float(u*width),float(y+lift*abs(u)**1.5+scallop),
                          float(depth-.105*abs(u)**1.4+ridge+z-.23)])
    front=np.asarray(front);back=front.copy();back[:,2]-=.040
    vertices=np.concatenate([front,back]);count=len(front);faces=[];width=len(columns)
    for row in range(len(rows)-1):
        for col in range(width-1):
            a=row*width+col;c=a+width
            # Alternating diagonals track the left/right sweep of the beard.
            cell=[[a,a+1,c],[a+1,c+1,c]] if col<width//2 else [[a,a+1,c+1],[a,c+1,c]]
            faces.extend(cell);faces.extend([[v+count for v in t[::-1]] for t in cell])
    boundary=list(range(width))+[r*width+width-1 for r in range(1,len(rows))]
    boundary+=list(range(count-2,count-width-1,-1))+[r*width for r in range(len(rows)-2,0,-1)]
    for a,c in zip(boundary,boundary[1:]+boundary[:1]):faces.extend([[a,a+count,c+count],[a,c+count,c]])
    b.commands.append(dict(id='beard-flow',slot=b.slot,stage=b.stage,part='beard_flow_'+kind,
        material='hair',op='indexed_mesh',vertices=vertices.tolist(),faces=faces,
        beard_flow={'schema_version':1,'kind':kind,'rows':len(rows),'columns':width,
                    'description':'cheek-to-jaw contours, broad falling locks and blunt layered tips'}))
    # Large overlapping locks give the beard its own falling silhouette and
    # longitudinal creases. They end in broad facets, never needle tips.
    for i in (-2,-1,0,1,2):
        x=i*.044;end=i*(.030 if long else .039)
        tip=(1.748 if long else 1.909)+abs(i)*(.024 if long else .026)
        mid=1.916 if long else 2.012
        front_z=.327-abs(i)*.019+z-.23
        b.loft('beard_falling_lock','hair_light' if abs(i)==1 else 'hair',[
            [tip,end,.254-abs(i)*.010+z-.23,.015,.016],
            [tip+.050,end,.278-abs(i)*.010+z-.23,.024,.023],
            [mid,x*.93,front_z,.033,.025],
            [2.105+abs(i)*.012,x,.301-abs(i)*.018+z-.23,.026,.014]],sides=6)
    for sign in (-1,1):
        b.loft('beard_cheek_lock','hair',[[2.10,sign*.155,z-.045,.025,.032],
             [2.20,sign*.178,z-.090,.034,.035],[2.28,sign*.188,z-.112,.024,.027],
             [2.335,sign*.184,z-.125,.013,.018]],sides=6)
