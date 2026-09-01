from dataclasses import dataclass
from typing import List, Tuple


Point = Tuple[float, float]
Color = Tuple[int, int, int]


@dataclass(frozen=True)
class Fragment:
    vertices: Tuple[Point, ...]
    color: Color


@dataclass(frozen=True)
class GeometrySnapshot:
    body_vertices: List[Point]
    fragments: List[Fragment]
    fill_color: Color
    outline_color: Color
