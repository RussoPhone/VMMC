import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

import main
from audio.input import AudioFrame, AudioPlaybackError, PlaybackState


class FakeAudioInput:
    def __init__(self, frames=(), state=PlaybackState.PLAYING):
        self.frames = list(frames)
        self.state = state

    def get_next_frame(self):
        return self.frames.pop(0) if self.frames else None


class RecordingAnalyzer:
    def __init__(self):
        self.seen = []

    def analyze(self, frame):
        self.seen.append(frame.frame_index)
        return f"features-{frame.frame_index}"


class RecordingMemory:
    def __init__(self):
        self.seen = []

    def update(self, features):
        self.seen.append(features)
        return f"context-{features}"


class MainAudioIntegrationTests(unittest.TestCase):
    def test_exposes_frame_drain_helper(self):
        self.assertTrue(hasattr(main, "drain_audio_frames"))

    def test_drains_every_available_frame_in_order(self):
        frames = [
            AudioFrame(np.zeros(4), 0.0, 12, 0),
            AudioFrame(np.ones(4), 1.0 / 3.0, 12, 1),
        ]
        audio = FakeAudioInput(frames)
        analyzer = RecordingAnalyzer()
        memory = RecordingMemory()

        features, context = main.drain_audio_frames(audio, analyzer, memory)

        self.assertEqual(analyzer.seen, [0, 1])
        self.assertEqual(memory.seen, ["features-0", "features-1"])
        self.assertEqual(features, "features-1")
        self.assertEqual(context, "context-features-1")

    def test_hud_uses_public_playback_state(self):
        audio = FakeAudioInput(state=PlaybackState.PLAYING)
        morphology = SimpleNamespace(
            wave=0.5,
            mass=0.5,
            shard=0.0,
            noise=0.0,
            roughness=0.0,
            elasticity=0.5,
            fluidity=0.5,
            symmetry=1.0,
            hue=0.5,
            saturation=0.5,
            brightness=0.5,
            color_stability=1.0,
        )

        try:
            lines = main._build_debug_lines(
                None,
                None,
                None,
                morphology,
                "/tmp/song.wav",
                audio,
            )
        except AttributeError as exc:
            self.fail(f"HUD acessou estado privado do backend: {exc}")

        self.assertIn("Audio: REPRODUZINDO", "\n".join(lines))

    def test_reset_pipeline_stops_previous_audio(self):
        previous = Mock()
        replacement = Mock()
        with patch.object(main, "AudioInput", return_value=replacement):
            pipeline = main.reset_pipeline("song.wav", previous)

        previous.stop.assert_called_once_with()
        replacement.play.assert_called_once_with()
        self.assertIs(pipeline[0], replacement)

    def test_main_quits_renderer_when_playback_start_fails(self):
        renderer = Mock()
        with (
            patch.object(main.os.path, "exists", return_value=True),
            patch.object(main, "Renderer", return_value=renderer),
            patch.object(
                main,
                "reset_pipeline",
                side_effect=AudioPlaybackError("device busy"),
            ),
            redirect_stdout(StringIO()) as output,
        ):
            main.main("song.wav")

        renderer.quit.assert_called_once_with()
        self.assertIn("device busy", output.getvalue())

    def test_system_audio_flag_builds_live_input(self):
        live = Mock()
        with (
            patch.object(main, "SystemAudioInput", return_value=live) as live_type,
            patch.object(main, "AudioInput") as file_type,
        ):
            result = main.create_audio_input("--system-audio")

        self.assertIs(result, live)
        live_type.assert_called_once_with()
        file_type.assert_not_called()

    def test_local_path_builds_file_input(self):
        file_input = Mock()
        with (
            patch.object(main, "SystemAudioInput") as live_type,
            patch.object(main, "AudioInput", return_value=file_input) as file_type,
        ):
            result = main.create_audio_input("song.wav")

        self.assertIs(result, file_input)
        file_type.assert_called_once_with("song.wav")
        live_type.assert_not_called()

    def test_system_audio_source_skips_file_existence_check(self):
        renderer = Mock()
        renderer.handle_events.return_value = False
        audio = Mock()
        pipeline = (audio, Mock(), Mock(), Mock(), Mock(), Mock(), Mock())
        with (
            patch.object(main.os.path, "exists", side_effect=AssertionError("file check")),
            patch.object(main, "Renderer", return_value=renderer),
            patch.object(main, "reset_pipeline", return_value=pipeline),
        ):
            main.main("--system-audio")

        audio.stop.assert_called_once_with()
        renderer.quit.assert_called_once_with()

    def test_system_audio_has_source_aware_label(self):
        self.assertEqual(main.source_description("--system-audio"), "Áudio do sistema")

    def test_live_source_runs_until_escape_instead_of_natural_finish(self):
        renderer = Mock()
        renderer.handle_events.return_value = [
            SimpleNamespace(type=main.pygame.KEYDOWN, key=main.pygame.K_ESCAPE)
        ]
        audio = Mock(state=PlaybackState.PLAYING)
        audio.get_next_frame.return_value = None
        audio.is_finished.return_value = False
        morphology = Mock()
        morphology.state = SimpleNamespace(
            wave=0.5,
            mass=0.5,
            shard=0.0,
            noise=0.0,
            roughness=0.0,
            elasticity=0.5,
            fluidity=0.5,
            symmetry=1.0,
            hue=0.5,
            saturation=0.5,
            brightness=0.5,
            color_stability=1.0,
        )
        pipeline = (audio, Mock(), Mock(), Mock(), morphology, Mock(), Mock())
        with (
            patch.object(main, "Renderer", return_value=renderer),
            patch.object(main, "reset_pipeline", return_value=pipeline),
        ):
            main.main("--system-audio")

        audio.is_finished.assert_called_once_with()
        audio.stop.assert_called_once_with()
        renderer.quit.assert_called_once_with()

    def test_background_capture_failure_is_reported_and_cleans_up(self):
        renderer = Mock()
        renderer.handle_events.return_value = []
        audio = Mock(state=PlaybackState.FAILED)
        audio.get_next_frame.side_effect = AudioPlaybackError("captura encerrada")
        pipeline = (audio, Mock(), Mock(), Mock(), Mock(), Mock(), Mock())
        with (
            patch.object(main, "Renderer", return_value=renderer),
            patch.object(main, "reset_pipeline", return_value=pipeline),
            redirect_stdout(StringIO()) as output,
        ):
            main.main("--system-audio")

        self.assertIn("captura encerrada", output.getvalue())
        self.assertIn("pactl get-default-sink", output.getvalue())
        self.assertIn("parec", output.getvalue())
        audio.stop.assert_called_once_with()
        renderer.quit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
