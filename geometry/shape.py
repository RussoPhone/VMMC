import math
from dataclasses import dataclass, field 
from typing import List, Tuple

@dataclass 
class Shape:
    vertex_count: int = 64
    base_angles: List[float] = field(default_factory=list)
    base_vertices: List[Tuple[float, float]] = field(default_factory=list)

    def __post_init__(self):
        if not self.base_angles:
            self.base_angles = [
                2 * math.pi * i / self.vertex_count for i in range(self.vertex_count)
            ]
            self.base_vertices = [
                (math.cos(a), math.sin(a)) for a in self.base_angles 
            ]

def create_circle_shape(vertex_count: int = 72) -> Shape:
    return Shape(vertex_count=vertex_count)
