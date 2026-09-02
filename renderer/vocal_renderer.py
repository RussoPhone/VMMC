"""Pygame laboratory for voice-only lines, waves, parameters, and graphs."""

from collections import deque
import math

import numpy as np
import pygame


class VocalTrace:
    NAMES = (
        "evidence",
        "intensity",
        "pressure",
        "continuity",
        "roughness",
        "confidence",
    )

    def __init__(self, max_history=360):
        self.history = {name: deque(maxlen=max_history) for name in self.NAMES}
        self.waveforms = deque(maxlen=max_history)
        self.rejected_count = 0

    def record(self, frame):
        context = frame.context
        gate = frame.gate
        values = {
            "evidence": frame.features.vocal_evidence,
            "intensity": context.vocal_activity,
            "pressure": context.vocal_activity * context.tension,
            "continuity": context.vocal_presence * context.signature_continuity,
            "roughness": context.vocal_presence * context.signature.noisiness,
            "confidence": gate.confidence,
        }
        for name, value in values.items():
            self.history[name].append(max(0.0, min(1.0, value)))
        if gate.open_amount > 0.01:
            samples = np.asarray(frame.audio_frame.samples, dtype=float).copy()
            self.waveforms.append((samples, gate.open_amount))
        elif gate.rejected_background:
            self.rejected_count += 1


class VocalRenderer:
    COLORS = {
        "evidence": (90, 160, 255),
        "intensity": (245, 245, 255),
        "pressure": (255, 90, 135),
        "continuity": (80, 235, 190),
        "roughness": (255, 180, 75),
        "confidence": (175, 120, 255),
    }

    def __init__(self, width=1200, height=800):
        pygame.display.init()
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("VMMC Vocal Waves Laboratory")
        self.clock = pygame.time.Clock()
        self.trace = VocalTrace()
        try:
            pygame.font.init()
            self.font = pygame.font.SysFont("consolas", 15)
        except Exception:
            self.font = None

    def handle_events(self):
        return pygame.event.get()

    def draw(self, frame, record=False):
        if record and frame is not None:
            self.trace.record(frame)
        width, height = self.screen.get_size()
        self.screen.fill((4, 7, 14))
        self._grid(width, height)
        if frame is not None:
            self._wave_field(frame, width, height)
            self._spectrum(frame, width, height)
            self._graphs(width, height)
            self._labels(frame, width)
        pygame.display.flip()
        self.clock.tick(60)

    def _grid(self, width, height):
        color = (12, 24, 38)
        for x in range(0, width, 80):
            pygame.draw.line(self.screen, color, (x, 0), (x, height))
        for y in range(0, height, 80):
            pygame.draw.line(self.screen, color, (0, y), (width, y))

    def _wave_field(self, frame, width, height):
        amount = frame.gate.open_amount
        if amount <= 0.005 or not self.trace.waveforms:
            if frame.gate.rejected_background:
                pygame.draw.rect(self.screen, (55, 22, 28), (12, 12, width - 24, height - 24), 2)
            return
        samples = self.trace.waveforms[-1][0]
        if len(samples) < 2:
            return
        count = min(width - 80, len(samples))
        indices = np.linspace(0, len(samples) - 1, count).astype(int)
        normalized = samples[indices]
        peak = max(float(np.max(np.abs(normalized))), 1e-6)
        normalized = normalized / peak
        center = height * 0.38
        amplitude = height * 0.18 * amount
        pressure = frame.context.tension * frame.context.vocal_activity
        roughness = frame.context.signature.noisiness * frame.context.vocal_presence
        for harmonic in range(4, 0, -1):
            scale = 1.0 / math.sqrt(harmonic)
            offset = (harmonic - 1.0) * height * 0.045
            points = []
            for index, value in enumerate(normalized):
                x = 40 + index * (width - 80) / max(1, count - 1)
                ripple = math.sin(index * 0.08 * harmonic) * roughness * 8.0
                y = center + offset + value * amplitude * scale + ripple * amount
                y += math.sin(index * 0.012 + pygame.time.get_ticks() * 0.002) * pressure * 12
                points.append((x, y))
            color = (
                int(45 + 145 * amount / harmonic),
                int(90 + 155 * amount),
                int(125 + 125 * amount),
            )
            pygame.draw.lines(self.screen, color, False, points, max(1, 5 - harmonic))

    def _spectrum(self, frame, width, height):
        notes = np.asarray(getattr(frame.features, "cqt_notes", ()), dtype=float)
        frequencies = np.asarray(getattr(frame.features, "cqt_frequencies", ()), dtype=float)
        if len(notes) == 0 or len(notes) != len(frequencies):
            return
        mask = (frequencies >= 80) & (frequencies <= 4000)
        values = notes[mask]
        if not len(values):
            return
        peak = max(float(np.max(values)), 1e-9)
        left, top, graph_width, graph_height = 40, height * 0.60, width - 80, height * 0.10
        for index, value in enumerate(values):
            x = left + index * graph_width / len(values)
            bar = value / peak * graph_height * frame.gate.open_amount
            pygame.draw.line(self.screen, (65, 145, 185), (x, top + graph_height), (x, top + graph_height - bar), 2)

    def _graphs(self, width, height):
        left, top = 40, height * 0.75
        graph_width, graph_height = width - 80, height * 0.18
        for name, values in self.trace.history.items():
            if len(values) < 2:
                continue
            points = [
                (
                    left + index * graph_width / max(1, values.maxlen - 1),
                    top + graph_height * (1.0 - value),
                )
                for index, value in enumerate(values)
            ]
            pygame.draw.lines(self.screen, self.COLORS[name], False, points, 2)

    def _labels(self, frame, width):
        if self.font is None:
            return
        gate = frame.gate
        status = "VOICE OPEN" if gate.confirmed else (
            "BACKGROUND REJECTED" if gate.rejected_background else "LISTENING"
        )
        values = self.trace.history
        lines = [
            f"VMMC VOCAL | {status}",
            f"confidence {gate.confidence:.2f}  open {gate.open_amount:.2f}  rejected {self.trace.rejected_count}",
            "  ".join(
                f"{name} {history[-1]:.2f}"
                for name, history in values.items()
                if history
            ),
        ]
        for index, text in enumerate(lines):
            surface = self.font.render(text, True, (210, 225, 235))
            self.screen.blit(surface, (24, 22 + index * 22))

    def quit(self):
        pygame.display.quit()
