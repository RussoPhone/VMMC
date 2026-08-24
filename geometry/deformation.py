import math
from typing import List, Tuple

def deform_shape(shape, visual_state, time_elapsed: float) -> List[Tuple[float, float]]:
    deformation_amount = visual_state.deformation
    agitation = visual_state.agitation 
    smoothness = max(0.05, visual_state.smoothness)
    scale = visual_state.scale
    rotation = visual_state.rotation

    harmonic_mid_weight = deformation_amount * (1.0 - smoothness) * 1.5
    harmonic_high_weight = agitation * (1.0 - smoothness) * 1.0

    vertices = []
    for angle in shape.base_angles:
        wobble = (
            math.sin(angle* 3 + time_elapsed * 1.3) * deformation_amount * 0.25
            + math.sin(angle * 7 + time_elapsed * 2.7) * harmonic_mid_weight * 0.15
            + math.sin(angle * 11 + time_elapsed * 4.1) * harmonic_high_weight * 0.10
        )

        radius = max(0.15, 1.0 + wobble)

        rotated_angle = angle + rotation

        x = math.cos(rotated_angle) * radius * scale
        y = math.sin(rotated_angle) * radius * scale
        vertices.append((x, y))

    return vertices 
