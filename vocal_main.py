"""Voice-only experimental entry point for VMMC."""

import sys
from dataclasses import dataclass

from audio.analyzer import AudioAnalyzer
from audio.input import AudioInput
from audio.live_input import SystemAudioInput
from expression.vocal_gate import VocalGate
from memory.musical_memory import MusicalMemory


SYSTEM_AUDIO_FLAG = "--system-audio"


@dataclass(frozen=True)
class VocalFrame:
    audio_frame: object
    features: object
    context: object
    gate: object


def drain_vocal_frames(
    audio_input,
    analyzer,
    memory,
    gate,
    previous_timestamp=None,
):
    latest = None
    last_timestamp = previous_timestamp
    while (audio_frame := audio_input.get_next_frame()) is not None:
        features = analyzer.analyze(audio_frame)
        dt = (
            1.0 / 30.0
            if last_timestamp is None
            else max(0.0, min(0.1, features.timestamp - last_timestamp))
        )
        last_timestamp = features.timestamp
        context = memory.update(features)
        gate_state = gate.update(features, context, dt)
        latest = VocalFrame(audio_frame, features, context, gate_state)
    return latest


def create_audio_input(source):
    return SystemAudioInput() if source == SYSTEM_AUDIO_FLAG else AudioInput(source)


def cli():
    source = sys.argv[1] if len(sys.argv) > 1 else None
    main(source)


def main(source=None):
    raise NotImplementedError("vocal renderer is added in the next task")


if __name__ == "__main__":
    cli()
