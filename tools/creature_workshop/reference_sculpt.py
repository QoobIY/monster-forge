"""Geometry authoring primitives retained for the current constructor."""
from __future__ import annotations
import numpy as np
from .observed_elements import PartBuilder

def triangulate(points):
    """Ear clipping of a simple outline in its image plane, including concavities."""
    p = np.asarray(points, float)[:, :2]
    area = np.sum(p[:, 0]*np.roll(p[:, 1], -1)-p[:, 1]*np.roll(p[:, 0], -1))
    remaining = list(range(len(p))) if area > 0 else list(reversed(range(len(p))))
    triangles = []
    def cross(a, b, c):
        u, v = b-a, c-a
        return u[0]*v[1]-u[1]*v[0]
    while len(remaining) > 3:
        for j, b in enumerate(remaining):
            a, c = remaining[j-1], remaining[(j+1) % len(remaining)]
            if cross(p[a], p[b], p[c]) <= 1e-8:
                continue
            if any(all(cross(p[x], p[y], p[k]) >= -1e-8 for x, y in ((a,b),(b,c),(c,a)))
                   for k in remaining if k not in (a,b,c)):
                continue
            triangles.append([a,b,c]); remaining.pop(j)
            break
        else:
            raise ValueError("Outline must be simple and have no duplicate/collinear corners")
    triangles.append(remaining)
    return triangles


class Sculpt(PartBuilder):
    def __init__(self, identity, palette):
        super().__init__(identity, palette)
        self.traces = []
        self.transform = (0., 0., .003, 0., 0.)
        self.mirror = False

    def point(self, u, v, z):
        cx, top, scale, x, y = self.transform
        xx = x+(u-cx)*scale
        return [-xx if self.mirror else xx, y-(v-top)*scale, z]

    def solid(self, part, material, vertices, faces, purpose, **metadata):
        vertices = np.asarray(vertices, float)
        faces = np.asarray(faces, int)
        tri = vertices[faces]
        volume = np.sum(np.einsum('ij,ij->i', tri[:,0], np.cross(tri[:,1],tri[:,2])))/6
        if volume < 0:
            faces = faces[:, ::-1]
        self.add('indexed_mesh', part, material, purpose,
                 vertices=vertices.tolist(), faces=faces.tolist(), **metadata)

    def panel(self, part, material, outline, front, back, purpose, bevel=.12, bulge=.025):
        """A traced closed solid: silhouette ring, inset crown, and back cap."""
        p = np.asarray(outline, float)
        z = np.full(len(p), front) if isinstance(front, (int, float)) else np.asarray(front)
        rear = np.full(len(p), back) if isinstance(back, (int, float)) else np.asarray(back)
        area = np.sum(p[:, 0]*np.roll(p[:, 1], -1)-p[:, 1]*np.roll(p[:, 0], -1))
        if area < 0:
            p, z, rear = p[::-1], z[::-1], rear[::-1]
        center = p.mean(axis=0)
        inset = p+(center-p)*bevel
        vertices = [self.point(u,v,zz) for (u,v),zz in zip(p,z,strict=True)]
        vertices += [self.point(u,v,zz+bulge) for (u,v),zz in zip(inset,z,strict=True)]
        vertices += [self.point(u,v,zz) for (u,v),zz in zip(p,rear,strict=True)]
        n = len(p); faces = []
        for i in range(n):
            j = (i+1)%n
            faces.extend([[i,j,n+i],[j,n+j,n+i], [i,2*n+i,j],[j,2*n+i,2*n+j]])
        cap = triangulate(p)
        edges = np.roll(inset, -1, axis=0)-inset
        relative = center-inset
        convex = np.all(edges[:, 0]*relative[:, 1]-edges[:, 1]*relative[:, 0] > 1e-8)
        if convex:
            crown = len(vertices)
            vertices.append(self.point(*center, float(z.mean()+bulge*2.4)))
            for i in range(n):
                faces.append([n+i,n+(i+1)%n,crown])
        else:
            faces.extend([[n+a,n+b,n+c] for a,b,c in cap])
        faces.extend([[2*n+c,2*n+b,2*n+a] for a,b,c in cap])
        mapping = {'origin_pixel':[self.transform[0],self.transform[1]],
                   'metres_per_pixel':self.transform[2],
                   'origin_metres':[self.transform[3],self.transform[4]],
                   'mirror_x':self.mirror}
        self.solid(part, material, vertices, faces, purpose,
                   source_outline_pixels=p.tolist(), source_mapping=mapping,
                   depth_assumption={'front_metres':z.tolist(),
                                     'back_metres':back if isinstance(back, (int, float)) else rear.tolist(),
                                     'bevel_fraction':bevel,'crown_metres':bulge})
        if not self.mirror:
            self.traces.append({'slot':self.slot,'part':part,'outline_pixels':p.tolist(),
                                'mapping':mapping})

    def section(self, part, material, rows, purpose):
        """Independent contour/depth sections; no ellipsoid or cylindrical template."""
        vertices = []
        for v,left,right,front,back in rows:
            mid = (left+right)/2; width = (right-left)/2
            for u,z in ((left,front*.3),(mid-width*.72,front*.83),(mid,front),
                        (mid+width*.72,front*.83),(right,front*.3),
                        (mid+width*.72,back*.83),(mid,back),(mid-width*.72,back*.83)):
                vertices.append(self.point(u,v,z))
        self.rings(part,material,vertices,8,purpose,
                   source_sections_pixels=[list(row) for row in rows],
                   source_mapping={'origin_pixel':list(self.transform[:2]),
                                   'metres_per_pixel':self.transform[2],
                                   'origin_metres':list(self.transform[3:]),'mirror_x':self.mirror})

    def rings(self,part,material,vertices,n,purpose,**metadata):
        rows = len(vertices)//n; faces=[]
        for j in range(rows-1):
            for i in range(n):
                a=j*n+i; b=j*n+(i+1)%n
                faces.extend([[a,b,a+n],[b,b+n,a+n]])
        for i in range(1,n-1):
            faces.extend([[0,i+1,i],[(rows-1)*n,(rows-1)*n+i,(rows-1)*n+i+1]])
        self.solid(part,material,vertices,faces,purpose,**metadata)

    def face(self, rows, cx):
        vertices=[]
        for v,width,z in rows:
            for t,zz in zip((-1,-.72,-.45,-.22,0,.22,.45,.72,1),z,strict=True):
                vertices.append(self.point(cx+t*width,v,zz))
            for t,zz in ((.72,-.08),(.35,-.155),(0,-.18),(-.35,-.155),(-.72,-.08)):
                vertices.append(self.point(cx+t*width,v,zz))
        self.rings('facial_topology','skin',vertices,14,
                   'Единая лицевая сетка: виски, надбровье, глазницы, скулы, губы и челюсть; глубина задана каждой вершиной.',
                   source_face_rows=[list(r) for r in rows])

    def finish(self):
        self.commands.sort(key=lambda c:c['stage'])
        for i,c in enumerate(self.commands):
            c['id']=f'c{i+1:03}'
        recipe=self.recipe();recipe['assembly_reference']='humanoid_v1'
        recipe['reference_construction']={'revision':REVISION,'image':'reference_parts.png',
                                         'method':'manual image-plane outlines plus authored depth and facial topology',
                                         'traces':self.traces,
                                         'limits':'Depth and rear surfaces are authored assumptions; front outline is observed.'}
        validate(recipe)
        return recipe
