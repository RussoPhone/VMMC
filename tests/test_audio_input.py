import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

import audio.input as audio_input

AudioInput = audio_input.AudioInput


class FakeOutputStream:
    def __init__(self, *, fail_start=False, **kwargs):
        self.callback = kwargs["callback"]
        self.finished_callback = kwargs["finished_callback"]
        self.channels = kwargs["channels"]
        self.fail_start = fail_start
        self.active = False
        self.stop_calls = 0
        self.close_calls = 0

    def start(self):
        if self.fail_start:
            raise RuntimeError("stream start failed")
        self.active = True

    def stop(self):
        self.stop_calls += 1
        self.active = False

    def close(self):
        self.close_calls += 1
        self.active = False

    def pump(self, frames):
        out = np.full((frames, self.channels), np.nan, dtype=np.float32)
        try:
            self.callback(out, frames, None, None)
        except sd.CallbackStop:
            self.active = False
            self.finished_callback()
        return out


class AudioInputTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.sample_rate = 12
        left = np.arange(12, dtype=np.float32) / 20.0
        right = -left
        self.stereo = np.column_stack((left, right))
        self.audio_path = Path(self.temp_dir.name) / "stereo.wav"
        sf.write(self.audio_path, self.stereo, self.sample_rate, subtype="FLOAT")
        self.streams = []

    def stream_factory(self, **kwargs):
        stream = FakeOutputStream(**kwargs)
        self.streams.append(stream)
        return stream

    def make_audio(self):
        try:
            audio = AudioInput(
                str(self.audio_path),
                frame_duration=1.0 / 3.0,
                stream_factory=self.stream_factory,
            )
            self.addCleanup(audio.stop)
            return audio
        except TypeError as exc:
            self.fail(f"AudioInput ainda não aceita stream_factory: {exc}")

    def test_exposes_public_playback_contract(self):
        self.assertTrue(hasattr(audio_input, "AudioPlaybackError"))
        self.assertTrue(hasattr(audio_input, "PlaybackState"))

    def test_stereo_callback_and_analysis_frames_are_sequential(self):
        audio = self.make_audio()
        audio.play()
        stream = self.streams[0]

        rendered = []
        frames = []
        for _ in range(3):
            rendered.append(stream.pump(4))
            frame = audio.get_next_frame()
            self.assertIsNotNone(frame)
            frames.append(frame)

        np.testing.assert_allclose(np.vstack(rendered), self.stereo, atol=1e-6)
        self.assertEqual([frame.frame_index for frame in frames], [0, 1, 2])
        for index, frame in enumerate(frames):
            start = index * 4
            expected_mono = self.stereo[start : start + 4].mean(axis=1)
            np.testing.assert_allclose(frame.samples, expected_mono, atol=1e-6)
        self.assertEqual(audio.state, audio_input.PlaybackState.FINISHED)
        self.assertTrue(audio.is_finished())
        self.assertIsNone(audio.get_next_frame())

    def test_get_next_frame_does_not_deadlock(self):
        audio = self.make_audio()
        audio.play()
        self.streams[0].pump(4)
        result = []

        worker = threading.Thread(target=lambda: result.append(audio.get_next_frame()), daemon=True)
        worker.start()
        worker.join(0.5)

        self.assertFalse(worker.is_alive(), "get_next_frame ficou bloqueado no lock")
        self.assertEqual(result[0].frame_index, 0)

    def test_multiple_elapsed_frames_are_drained_in_order(self):
        audio = self.make_audio()
        audio.play()
        self.streams[0].pump(12)

        frames = []
        while (frame := audio.get_next_frame()) is not None:
            frames.append(frame)

        self.assertEqual([frame.frame_index for frame in frames], [0, 1, 2])
        self.assertTrue(audio.is_finished())

    def test_position_comes_from_submitted_samples(self):
        audio = self.make_audio()
        audio.play()
        self.streams[0].pump(4)

        self.assertAlmostEqual(audio.get_position_seconds(), 4 / self.sample_rate)

    def test_start_failure_is_explicit(self):
        streams = []

        def failing_factory(**kwargs):
            stream = FakeOutputStream(fail_start=True, **kwargs)
            streams.append(stream)
            return stream

        try:
            audio = AudioInput(
                str(self.audio_path),
                frame_duration=1.0 / 3.0,
                stream_factory=failing_factory,
            )
        except TypeError as exc:
            self.fail(f"AudioInput ainda não aceita stream_factory: {exc}")

        with self.assertRaisesRegex(audio_input.AudioPlaybackError, "stream start failed"):
            audio.play()

        self.assertEqual(audio.state, audio_input.PlaybackState.FAILED)
        self.assertIn("stream start failed", audio.error_message)
        self.assertEqual(streams[0].close_calls, 1)

    def test_stop_is_idempotent(self):
        audio = self.make_audio()
        audio.play()
        stream = self.streams[0]

        audio.stop()
        audio.stop()

        self.assertEqual(audio.state, audio_input.PlaybackState.STOPPED)
        self.assertEqual(stream.stop_calls, 1)
        self.assertEqual(stream.close_calls, 1)


if __name__ == "__main__":
    unittest.main()
