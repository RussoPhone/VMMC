import math
from dataclasses import dataclass

@dataclass
class VisualState:
    scale: float = 1.0
    deformation: float = 0.0
    rotation: float = 0.0
    smoothness: float = 1.0
    agitation: float = 0.0

class VisualStateController:
    def __init__(self, response_speed: float = 3.0, rotation_speed_scale: float = 1.2):
        self.response_speed = response_speed 
        self.rotation_speed_scale = rotation_speed_scale
        self.state = VisualState()

    def update(self, context, dt: float) -> VisualState:
        target_scale = 1.0 + context.energy * 0.6 + max(0.0, context.energy_trend) * 0.4
        target_deformation = context.tension
        target_agitation = min(1.0, context.activity * 1.5 + context.tension * 0.5)
        target_smoothness = max(0.1, 1.0 - context.tension * 0.7)

        alpha = 1.0 - math.exp(-self.response_speed * dt)

        s = self.state
        s.scale += (target_scale - s.scale) * alpha
        s.deformation += (target_deformation - s.deformation) * alpha
        s.agitation += (target_agitation - s.agitation) * alpha
        s.smoothness += (target_smoothness - s.smoothness) * alpha 

        rotation_speed = 0.2 + context.activity * self.rotation_speed_scale
        s.rotation += rotation_speed * dt

        return s
