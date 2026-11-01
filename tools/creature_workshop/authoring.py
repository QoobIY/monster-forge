"""Shared geometry command builder used by the current constructor."""
from __future__ import annotations

STAGES = ["Основные массы и опоры", "Голова и анатомия", "Одежда и защитные пластины",
          "Отличительные детали", "Кисти, опоры и завершающие акценты"]


class Builder:
    def __init__(self):
        self.commands = []
        self.stage = 1

    def add(self, op, part, material, purpose, **parameters):
        def rounded(value):
            if isinstance(value, float):
                return round(value, 6)
            if isinstance(value, (list, tuple)):
                return [rounded(v) for v in value]
            return value
        self.commands.append({"id": f"c{len(self.commands)+1:03}", "stage": self.stage,
                              "op": op, "part": part, "material": material,
                              "purpose": purpose, **{k: rounded(v) for k, v in parameters.items()}})

    def oval(self, part, material, center, radii, purpose, sides=8):
        self.add("ellipsoid", part, material, purpose, center=center, radii=radii, sides=sides, rings=4)

    def tube(self, part, material, path, radii, purpose, sides=6):
        if isinstance(radii, (int, float)):
            radii = [radii] * len(path)
        self.add("sweep", part, material, purpose, path=path, radii=radii, sides=sides)

    def loft(self, part, material, stations, purpose, sides=8):
        self.add("loft", part, material, purpose, stations=stations, sides=sides)

    def plate(self, part, material, points, purpose, depth=.04):
        self.add("prism", part, material, purpose, points=points, offset=[0, 0, -depth])

    def box(self, part, material, center, size, purpose):
        self.add("box", part, material, purpose, center=center, size=size)
