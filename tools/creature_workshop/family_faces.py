"""Consistent outward triangle orientation for constructor meshes."""
import numpy as np

def orient_faces(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Orient generated primitive caps consistently before baking a closed mesh."""
    faces = faces.copy()
    edges = {}
    for i, face in enumerate(faces):
        for a, b in zip(face, np.roll(face, -1), strict=True):
            edges.setdefault(tuple(sorted((a, b))), []).append(i)
    if any(len(v) != 2 for v in edges.values()):
        raise ValueError("Template must have two triangles at every edge")
    seen = set()
    for root in range(len(faces)):
        if root in seen:
            continue
        queue = [root]
        seen.add(root)
        while queue:
            i = queue.pop()
            for a, b in zip(faces[i], np.roll(faces[i], -1), strict=True):
                neighbor = next(j for j in edges[tuple(sorted((a, b)))] if j != i)
                if neighbor in seen:
                    continue
                ring = faces[neighbor]
                if any(x == a and y == b for x, y in zip(ring, np.roll(ring, -1), strict=True)):
                    faces[neighbor] = ring[::-1]
                seen.add(neighbor)
                queue.append(neighbor)
    tri = vertices[faces]
    if np.sum(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2]))) < 0:
        faces = faces[:, ::-1]
    return faces
