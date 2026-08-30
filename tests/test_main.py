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
        visual_state = SimpleNamespace(
            scale=1.0,
            deformation=0.0,
            agitation=0.0,
            smoothness=1.0,
        )

        try:
            lines = main._build_debug_lines(
                None,
                None,
                visual_state,
                "/tmp/song.wav",
                audio,
            )
        except AttributeError as exc:
            self.fail(f"HUD acessou estado privado do backend: {exc}")

        self.assertIn("Audio: REPRODUZINDO", lines)

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


if __name__ == "__main__":
    unittest.main()
