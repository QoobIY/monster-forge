"""Small authored fittings: hollow frames, clasps, leather seams and back hardware."""
import math
import numpy as np


def frame(b,name,material,center,width,height,border=.008,depth=.012):
    x,y,z=center
    outline=np.array([[-.4,-.5],[.4,-.5],[.5,-.4],[.5,.4],[.4,.5],[-.4,.5],[-.5,.4],[-.5,-.4]])
    vertices=[]
    for zz in (z-depth*.5,z+depth*.5):
        for w,h in ((width,height),(width-2*border,height-2*border)):
            vertices.extend([[x+px*w,y+py*h,zz] for px,py in outline])
    faces=[]
    for i in range(8):
        j=(i+1)%8
        for a,c in ((0,8),(16,24),(0,16),(8,24)):
            faces.extend([[a+i,a+j,c+j],[a+i,c+j,c+i]])
    from .family_faces import orient_faces
    faces=orient_faces(np.asarray(vertices),np.asarray(faces))
    b.solid(name,material,vertices,faces.tolist(),'Chamfered hollow accessory frame',
            accessory_detail={'schema_version':1,'type':'hollow_frame'})


def belt(b,kind):
    if kind=='none':return
    b.slot='torso';y=1.115;z=.216
    frame(b,'ornament_buckle_frame','metal',[0,y,z+.015],.096,.068,.010)
    b.tube('ornament_buckle_prong','metal',[[-.032,y,z+.023],[.033,y,z+.023]],[.005,.005],sides=4)
    for sign in (-1,1):
        for x in (.095,.18):
            zz=.227*math.sqrt(max(0,1-(x/.27)**2))
            b.box('ornament_leather_keeper','leather',[sign*x,y,zz+.008],[.018,.088,.018])
        for yoff in (-.026,.026):
            b.tube('ornament_belt_stitch','accent',[[sign*.065,y+yoff,.246],[sign*.12,y+yoff,.222],[sign*.19,y+yoff,.189]],[.0025]*3,sides=4)
    if kind=='pouches':
        for sign in (-1,1):
            x=sign*.245
            b.panel3('ornament_pouch_folded_flap','leather',[[x-.065,1.18,.306],[x+.065,1.18,.306],[x+.055,1.08,.32],[x,1.055,.327],[x-.055,1.08,.32]],.012)
            frame(b,'ornament_pouch_fastener','metal',[x,1.10,.336],.037,.031,.005,.008)
            b.tube('ornament_pouch_seam','accent',[[x-.055,1.15,.322],[x-.055,1.01,.31],[x+.055,1.01,.31],[x+.055,1.15,.322]],[.0025]*4,sides=4)
    elif kind in ('flasks','scrolls','tools','book'):
        for sign in (-1,1):
            b.panel3('ornament_attachment_tab','leather',[[sign*.20-.021,1.15,.28],[sign*.20+.021,1.15,.28],[sign*.20+.021,1.07,.29],[sign*.20-.021,1.07,.29]],.01)
            b.oval('ornament_tab_rivet','metal',[sign*.20,1.135,.292],[.007,.007,.005],sides=5)
    elif kind=='gems':
        for x in (-.17,0,.17):frame(b,'ornament_gem_setting','metal',[x,1.10,.265],.072,.098,.007)


def headwear(b,kind):
    if kind=='none':return
    b.slot='head'
    if kind in ('circlet','crown','tiara'):
        for i in range(5):
            x=(i-2)*.059;z=.20-.018*abs(i-2)
            frame(b,'ornament_gem_setting','accent',[x,2.513,z+.005],.038,.044,.006,.009)
            b.oval('ornament_inset_gem','secondary',[x,2.514,z+.012],[.012,.014,.008],sides=5)
        for sign in (-1,1):
            b.tube('ornament_circlet_engraving','accent',[[sign*.03,2.479,.204],[sign*.12,2.479,.18],[sign*.19,2.479,.11]],[.003]*3,sides=4)
        if kind=='tiara':
            for sign in (-1,1):b.tube('ornament_tiara_arch','metal',[[sign*.15,2.50,.18],[sign*.075,2.54,.20],[0,2.585,.205]],[.007,.006,.004],sides=5)
    elif kind=='goggles':
        for sign in (-1,1):
            frame(b,'ornament_goggle_frame','metal',[sign*.103,2.33,.308],.112,.085,.009)
            b.box('ornament_goggle_hinge','leather',[sign*.168,2.33,.272],[.022,.031,.029])
        b.tube('ornament_goggle_strap','leather',[[-.17,2.33,.20],[-.23,2.33,.015],[0,2.33,-.17],[.23,2.33,.015],[.17,2.33,.20]],[.012]*5,sides=4)
    elif kind=='earrings':
        for sign in (-1,1):
            frame(b,'ornament_earring_hoop','metal',[sign*.235,2.21,.039],.039,.057,.005,.008)
            b.oval('ornament_earring_drop','secondary',[sign*.235,2.163,.038],[.016,.027,.012],sides=5)
    elif kind=='laurel':
        for sign in (-1,1):
            for i in range(4):
                x=sign*(.045+i*.045);y=2.525-i*.006;z=.19-i*.024
                b.panel3('ornament_laurel_blade','secondary',[[x,y,z],[x+sign*.035,y+.019,z+.003],[x+sign*.048,y+.061,z],[x+sign*.009,y+.035,z+.006]],.008)
                b.tube('ornament_leaf_vein','metal',[[x,y,z+.010],[x+sign*.03,y+.042,z+.010]],[.002,.001],sides=4)
    elif kind=='feather':
        b.tube('ornament_feather_shaft','metal',[[.21,2.50,.041],[.31,2.73,.020]],[.005,.002],sides=4)
        for i in range(5):
            p=np.array([.22+i*.016,2.54+i*.033,.042])
            b.tube('ornament_feather_barb','accent',[p.tolist(),(p+[.048,.020,0]).tolist()],[.002,.001],sides=4)
    elif kind=='gem':frame(b,'ornament_forehead_setting','metal',[0,2.445,.227],.083,.113,.009)
    elif kind=='horncaps':
        for sign in (-1,1):b.tube('ornament_cap_engraving','accent',[[sign*.17,2.50,.010],[sign*.215,2.56,.012],[sign*.245,2.60,.012]],[.004]*3,sides=4)
    elif kind=='mask':
        for sign in (-1,1):b.tube('ornament_mask_brow_trim','accent',[[sign*.018,2.357,.292],[sign*.09,2.367,.287],[sign*.165,2.35,.286]],[.004]*3,sides=4)


def back(b,style,z):
    if style in ('pack','bedroll','books','alchemy','lantern','trophies'):
        frame(b,'pack_buckle','metal',[0,1.54,z-.293],.075,.068,.010)
        for sign in (-1,1):
            b.panel3('pack_side_pocket','secondary',[[sign*.18,1.62,z-.29],[sign*.27,1.61,z-.23],[sign*.27,1.34,z-.23],[sign*.18,1.33,z-.29]],.028)
            b.tube('pack_sewn_edge','accent',[[sign*.19,1.73,z-.318],[sign*.20,1.31,z-.31],[sign*.14,1.25,z-.31]],[.0035]*3,sides=4)
            b.oval('pack_rivet','metal',[sign*.13,1.70,z-.31],[.009,.009,.006],sides=5)
        if style=='bedroll':
            for x in (-.19,.19):
                b.tube('bedroll_leather_tie','leather',[[x,1.84,z-.13],[x,1.92,z-.247],[x,2.02,z-.13],[x,1.92,z-.015],[x,1.84,z-.13]],[.013]*5,sides=5)
                b.tube('bedroll_attachment_strap','leather',[[x,1.68,z-.289],[x,1.79,z-.28],[x,1.94,z-.25]],[.014]*3,sides=5)
    elif style=='quiver':
        start=np.array([-.14,1.17,z-.12]);end=np.array([.14,1.78,z-.12]);axis=end-start
        for t in (.15,.83,.98):
            a=start+axis*t;d=start+axis*min(t+.032,1.04)
            b.tube('quiver_leather_binding','leather',[a.tolist(),d.tolist()],[.107+.03*t]*2,sides=8)
        b.panel3('quiver_stitched_panel','secondary',[[-.23,1.28,z-.19],[-.13,1.23,z-.235],[.13,1.72,z-.25],[.03,1.77,z-.205]],.01)
    elif style in ('short','royal','split','ranger','layered'):
        bottom={'short':1.13,'royal':.22,'split':.47,'ranger':.68,'layered':.84}[style]
        for sign in (-1,1):
            b.tube('cape_sewn_fold','cloth',[[sign*.09,1.81,z-.038],[sign*.16,1.46,z-.084],[sign*.20,bottom+.10,z-.10]],[.012,.018,.011],sides=5)
            b.panel3('cape_fold_plane','cloth',[[sign*.04,1.80,z-.025],[sign*.12,1.68,z-.053],[sign*.24,bottom+.11,z-.11],[sign*.12,bottom+.07,z-.123]],.009)
        if style in ('royal','ranger'):
            for sign in (-1,1):frame(b,'cape_shoulder_clasp','metal',[sign*.14,1.84,z-.031],.044,.047,.006)
    elif style in ('feather','fan','raven','membrane','dragon','crystal','mechanical'):
        for sign in (-1,1):
            b.oval('wing_root_joint','metal',[sign*.21,1.79,z-.056],[.085,.071,.035],sides=6)
            for i in range(4):
                x=sign*(.31+i*.13);y=1.87+i*.05
                if style in ('membrane','dragon'):b.tube('wing_secondary_rib','metal',[[x,y,z-.07],[x+sign*.09,y-.25,z-.15]],[.013,.004],sides=5)
                elif style=='crystal':b.oval('wing_crystal_socket','metal',[x,y-.12,z-.07],[.044,.064,.024],sides=5)
                else:b.panel3('wing_covert_feather','accent',[[x,y,z-.072],[x+sign*.12,y+.027,z-.085],[x+sign*.14,y-.15,z-.10],[x+sign*.06,y-.18,z-.105]],.011)
    elif style in ('spikes','plates','shield'):
        for sign in (-1,1):
            for i in range(3):b.oval('dorsal_armor_rivet','metal',[sign*(.23-i*.027),1.70-i*.18,z-.091],[.012,.012,.008],sides=5)
    elif style in ('banner','twinbanner'):
        for x in ([0] if style=='banner' else [-.25,.25]):
            b.tube('standard_crossbar','metal',[[x-.055,2.575,z],[x+.415,2.575,z]],[.012,.012],sides=5)
            for i in range(4):b.tube('standard_tassel','accent',[[x+.055+i*.080,2.10,z-.025],[x+.055+i*.080,2.025,z-.025]],[.006,.002],sides=4)
