import os
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog

import pygame

from audio.analyzer import AudioAnalyzer
from audio.input import AudioInput, AudioPlaybackError, PlaybackState
from audio.live_input import SystemAudioInput
from expression.gesture_engine import GestureEngine
from expression.presence_tracker import PresenceTracker
from geometry.deformation import GeometryBuilder
from geometry.ecosystem_geometry import EcosystemGeometryBuilder
from geometry.shape import create_circle_shape
from memory.musical_memory import MusicalMemory
from renderer.renderer import Renderer
from state.morphology import MorphologyController
from state.ecosystem import EcosystemController


AUDIO_EXTENSIONS = [
    ("Arquivos de Áudio", "*.wav *.flac *.ogg *.mp3 *.aiff *.aif *.au *.raw *.pcm"),
    ("Todos os arquivos", "*.*"),
]
SYSTEM_AUDIO_FLAG = "--system-audio"


@dataclass(frozen=True)
class ExpressiveFrame:
    features: object
    context: object
    gestures: object
    morphology: object
    presences: object = None
    ecosystem: object = None


def select_audio_file(initial_dir: str = None) -> str | None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        file_path = filedialog.askopenfilename(
            title="Selecionar arquivo de áudio",
            initialdir=initial_dir or os.path.expanduser("~"),
            filetypes=AUDIO_EXTENSIONS,
        )
        return file_path if file_path else None
    finally:
        root.destroy()


def drain_audio_frames(audio_input, analyzer, memory):
    """Compatibility helper for consumers of the original three-stage pipeline."""
    latest_features = None
    latest_context = None
    while (frame := audio_input.get_next_frame()) is not None:
        latest_features = analyzer.analyze(frame)
        latest_context = memory.update(latest_features)
    return latest_features, latest_context


def drain_expressive_frames(
    audio_input,
    analyzer,
    memory,
    gesture_engine,
    morphology_controller,
    previous_timestamp=None,
    presence_tracker=None,
    ecosystem_controller=None,
):
    """Send every elapsed audio frame through every interpretive layer in order."""
    latest = None
    last_timestamp = previous_timestamp
    while (frame := audio_input.get_next_frame()) is not None:
        features = analyzer.analyze(frame)
        if last_timestamp is None:
            dt = 1.0 / 30.0
        else:
            dt = max(0.0, min(0.1, features.timestamp - last_timestamp))
        last_timestamp = features.timestamp
        context = memory.update(features)
        gestures = gesture_engine.update(context, dt)
        morphology = morphology_controller.update(context, gestures, dt)
        presences = (
            presence_tracker.update(context, features.timestamp)
            if presence_tracker is not None
            else None
        )
        ecosystem = (
            ecosystem_controller.update(
                presences,
                dt,
                global_cohesion=context.regimes.stability,
            )
            if ecosystem_controller is not None
            else None
        )
        latest = ExpressiveFrame(features, context, gestures, morphology, presences, ecosystem)
    return latest


def create_audio_input(source: str):
    if source == SYSTEM_AUDIO_FLAG:
        return SystemAudioInput()
    return AudioInput(source)


def source_description(source: str) -> str:
    if source == SYSTEM_AUDIO_FLAG:
        return "Áudio do sistema"
    return os.path.basename(source)


def reset_pipeline(audio_path: str, previous_audio=None):
    if previous_audio is not None:
        previous_audio.stop()
    audio_input = create_audio_input(audio_path)
    analyzer = AudioAnalyzer()
    memory = MusicalMemory()
    gestures = GestureEngine()
    morphology = MorphologyController()
    geometry = GeometryBuilder(max_fragments=6)
    shape = create_circle_shape(vertex_count=72)
    audio_input.play()
    return audio_input, analyzer, memory, gestures, morphology, geometry, shape


def main(audio_path: str = None) -> None:
    if not audio_path:
        audio_path = select_audio_file()
        if not audio_path:
            print("Nenhum arquivo selecionado. Saindo.")
            return
    if audio_path != SYSTEM_AUDIO_FLAG and not os.path.exists(audio_path):
        print(f"Erro: O arquivo '{audio_path}' não existe.")
        return

    renderer = None
    audio_input = None
    try:
        renderer = Renderer()
        (
            audio_input,
            analyzer,
            memory,
            gesture_engine,
            morphology_controller,
            geometry_builder,
            shape,
        ) = reset_pipeline(audio_path)
        start_time = time.monotonic()
        last_time = start_time
        latest = None
        presence_tracker = PresenceTracker()
        ecosystem_controller = EcosystemController()
        ecosystem_geometry = EcosystemGeometryBuilder()
        running = True
        last_dir = os.path.dirname(audio_path)

        while running:
            events = renderer.handle_events()
            if events is False:
                break
            if events is True:
                events = []
            for event in events:
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_o:
                    new_path = select_audio_file(initial_dir=last_dir)
                    if new_path:
                        last_dir = os.path.dirname(new_path)
                        (
                            audio_input,
                            analyzer,
                            memory,
                            gesture_engine,
                            morphology_controller,
                            geometry_builder,
                            shape,
                        ) = reset_pipeline(new_path, audio_input)
                        audio_path = new_path
                        start_time = time.monotonic()
                        last_time = start_time
                        latest = None
                        presence_tracker = PresenceTracker()
                        ecosystem_controller = EcosystemController()
                        ecosystem_geometry = EcosystemGeometryBuilder()

            now = time.monotonic()
            render_dt = max(0.0, min(0.1, now - last_time))
            last_time = now
            previous_timestamp = latest.features.timestamp if latest else None
            new_result = drain_expressive_frames(
                audio_input,
                analyzer,
                memory,
                gesture_engine,
                morphology_controller,
                previous_timestamp,
                presence_tracker,
                ecosystem_controller,
            )
            if new_result is not None:
                latest = new_result

            morphology = latest.morphology if latest else morphology_controller.state
            geometry = geometry_builder.build(
                shape,
                morphology,
                now - start_time,
                render_dt,
            )
            if latest and latest.ecosystem and latest.ecosystem.organisms:
                geometry = ecosystem_geometry.build(
                    latest.ecosystem,
                    now - start_time,
                    geometry,
                )
            debug_lines = _build_debug_lines(
                latest.features if latest else None,
                latest.context if latest else None,
                latest.gestures if latest else None,
                morphology,
                audio_path,
                audio_input,
                latest.ecosystem if latest else None,
            )
            renderer.draw(geometry, debug_lines)
            if audio_input.is_finished():
                running = False
    except AudioPlaybackError as exc:
        print(f"[ERRO] {exc}")
        if audio_path == SYSTEM_AUDIO_FLAG:
            print(
                "Verifique 'pactl get-default-sink', "
                "'pactl list short sources' e se o comando 'parec' está disponível."
            )
        else:
            print(
                "Verifique o dispositivo padrão com 'pactl info' e "
                f"'{sys.executable} -m sounddevice'."
            )
    finally:
        if audio_input is not None:
            audio_input.stop()
        if renderer is not None:
            renderer.quit()


def _build_debug_lines(
    features,
    context,
    gestures,
    morphology,
    current_file,
    audio_input,
    ecosystem=None,
) -> list:
    status_labels = {
        PlaybackState.STOPPED: "PARADO",
        PlaybackState.PLAYING: "REPRODUZINDO",
        PlaybackState.FINISHED: "FINALIZADO",
        PlaybackState.FAILED: "ERRO",
    }
    lines = [
        "VMMC | GEOMETRIA CONTEXTUAL EXPRESSIVA",
        f"Fonte: {source_description(current_file)} | Audio: {status_labels[audio_input.state]}",
        "Controles: [O] Abrir arquivo | [ESC] Sair",
    ]
    if features:
        lines.append(
            "AUDIO "
            f"energy={features.amplitude:.2f} bass={features.bass:.2f} "
            f"mid={features.mid:.2f} high={features.treble:.2f} "
            f"flux={features.spectral_flux:.2f} centroid={features.spectral_centroid:.2f} "
            f"zcr={features.zero_crossing_rate:.2f} density={features.spectral_density:.2f} "
            f"onset={'*' if features.beat else ' '}"
        )
    if context:
        lines.append(
            "CONTEXT "
            f"short={context.short_energy:.2f} medium={context.medium_energy:.2f} "
            f"trend={context.energy_trend:+.2f} activity={context.activity:.2f} "
            f"novelty={context.novelty:.2f} stability={context.stability:.2f} "
            f"tension={context.tension:.2f} persistence={context.persistence:.2f}"
        )
        lines.append(
            "LANDSCAPE "
            f"energy={context.relative.energy:+.2f} "
            f"brightness={context.relative.brightness:+.2f} "
            f"texture={context.relative.texture:+.2f} "
            f"activity={context.relative.activity:+.2f} "
            f"confidence={context.relative.confidence:.2f}"
        )
        lines.append(
            "SIGNATURE "
            f"brightness={context.signature.brightness:.2f} "
            f"noise={context.signature.noisiness:.2f} "
            f"harmonicity={context.signature.harmonicity:.2f} "
            f"attack={context.signature.attack:.2f} "
            f"density={context.signature.density:.2f} "
            f"continuity={context.signature_continuity:.2f} "
            f"prominence={context.prominence:.2f}"
        )
        lines.append(
            "REGIME "
            f"stable={context.regimes.stability:.2f} "
            f"building={context.regimes.building:.2f} "
            f"suspension={context.regimes.suspension:.2f} "
            f"rupture={context.regimes.rupture:.2f} "
            f"climax={context.regimes.climax:.2f} "
            f"release={context.regimes.release:.2f} "
            f"transition={context.regimes.transition:.2f} "
            f"cycle={context.cycle_index} phase={context.cycle_phase.value} "
            f"silence={context.silence_duration:.2f}"
        )
    if gestures:
        lines.append(
            "GESTURES "
            f"pressure={gestures.pressure:.2f} release={gestures.release:.2f} "
            f"impact={gestures.impact:.2f} suspension={gestures.suspension:.2f} "
            f"expansion={gestures.expansion:.2f} rupture={gestures.rupture:.2f}"
        )
    if ecosystem:
        maximum_fusion = max(
            (relation.fusion for relation in ecosystem.relations),
            default=0.0,
        )
        maximum_assimilation = max(
            (relation.assimilation for relation in ecosystem.relations),
            default=0.0,
        )
        lines.append(
            "ECOSYSTEM "
            f"organisms={len(ecosystem.organisms)} "
            f"relations={len(ecosystem.relations)} "
            f"fusion={maximum_fusion:.2f} "
            f"assimilation={maximum_assimilation:.2f} "
            f"core={ecosystem.core_cohesion:.2f}"
        )
    lines.append(
        "MORPHOLOGY "
        f"wave={morphology.wave:.2f} mass={morphology.mass:.2f} "
        f"shard={morphology.shard:.2f} noise={morphology.noise:.2f} "
        f"rough={morphology.roughness:.2f} elastic={morphology.elasticity:.2f} "
        f"fluid={morphology.fluidity:.2f} symmetry={morphology.symmetry:.2f}"
    )
    lines.append(
        "COLOR "
        f"hue={morphology.hue:.2f} saturation={morphology.saturation:.2f} "
        f"brightness={morphology.brightness:.2f} "
        f"stability={morphology.color_stability:.2f}"
    )
    return lines


def cli() -> None:
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(audio_path)


if __name__ == "__main__":
    cli()
