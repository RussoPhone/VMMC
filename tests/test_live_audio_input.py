import io
import queue
import time
import unittest

import numpy as np

from audio.input import AudioPlaybackError, PlaybackState
from audio.live_input import SystemAudioInput, discover_default_monitor


class Result:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class RecordingRunner:
    def __init__(self, results):
        self.results = iter(results)
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append((command, kwargs))
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


class FeedableStream:
    def __init__(self):
        self._chunks = queue.Queue()

    def feed(self, chunk):
        self._chunks.put(chunk)

    def read(self, size):
        del size
        chunk = self._chunks.get(timeout=1.0)
        if isinstance(chunk, Exception):
            raise chunk
        return chunk


class FakeProcess:
    def __init__(self):
        self.stdout = FeedableStream()
        self.stderr = io.BytesIO()
        self.terminate_calls = 0
        self.wait_calls = 0
        self.kill_calls = 0
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminate_calls += 1
        self.returncode = 0
        self.stdout.feed(b"")

    def wait(self, timeout=None):
        del timeout
        self.wait_calls += 1
        return self.returncode

    def kill(self):
        self.kill_calls += 1
        self.returncode = -9
        self.stdout.feed(b"")


def wait_until(predicate, timeout=0.5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.001)
    return False


class DefaultMonitorDiscoveryTests(unittest.TestCase):
    def test_returns_monitor_for_default_sink_only(self):
        runner = RecordingRunner(
            [
                Result("alsa_output.pci-main\n"),
                Result(
                    "41\talsa_output.usb.monitor\tmodule\n"
                    "42\talsa_output.pci-main.monitor\tmodule\n"
                ),
            ]
        )

        monitor = discover_default_monitor(runner)

        self.assertEqual(monitor, "alsa_output.pci-main.monitor")
        self.assertEqual(runner.commands[0][0], ["pactl", "get-default-sink"])
        self.assertEqual(
            runner.commands[1][0], ["pactl", "list", "short", "sources"]
        )

    def test_rejects_absent_default_monitor(self):
        runner = RecordingRunner(
            [Result("main\n"), Result("1\tmicrophone\tmodule\n")]
        )

        with self.assertRaisesRegex(AudioPlaybackError, "monitor.*main"):
            discover_default_monitor(runner)

    def test_reports_missing_pactl(self):
        runner = RecordingRunner([FileNotFoundError("pactl")])

        with self.assertRaisesRegex(AudioPlaybackError, "pactl"):
            discover_default_monitor(runner)


class SystemAudioInputTests(unittest.TestCase):
    def setUp(self):
        self.process = FakeProcess()
        self.process_calls = []

    def process_factory(self, command, **kwargs):
        self.process_calls.append((command, kwargs))
        return self.process

    def make_audio(self):
        runner = RecordingRunner(
            [
                Result("main\n"),
                Result("1\tmain.monitor\tmodule\n"),
            ]
        )
        audio = SystemAudioInput(
            frame_duration=1.0 / 3.0,
            samplerate=12,
            command_runner=runner,
            process_factory=self.process_factory,
        )
        self.addCleanup(audio.stop)
        return audio

    def test_pcm_frames_follow_the_sample_cursor(self):
        audio = self.make_audio()
        samples = np.arange(4, dtype=np.float32)

        audio.play()
        self.process.stdout.feed(samples.astype("<f4").tobytes())

        self.assertTrue(
            wait_until(lambda: audio.get_position_seconds() == 4 / 12),
            "capture worker did not publish the samples",
        )
        frame = audio.get_next_frame()
        self.assertEqual(frame.frame_index, 0)
        self.assertEqual(frame.timestamp, 0.0)
        np.testing.assert_array_equal(frame.samples, samples)
        self.assertEqual(audio.state, PlaybackState.PLAYING)
        self.assertFalse(audio.is_finished())
        self.assertEqual(
            self.process_calls[0][0],
            [
                "parec",
                "--device",
                "main.monitor",
                "--format",
                "float32le",
                "--rate",
                "12",
                "--channels",
                "1",
                "--raw",
            ],
        )

    def test_fragmented_pcm_bytes_are_preserved_until_a_frame_is_complete(self):
        audio = self.make_audio()
        samples = np.array([0.25, -0.5, 0.75, -1.0], dtype=np.float32)
        payload = samples.astype("<f4").tobytes()

        audio.play()
        self.process.stdout.feed(payload[:3])
        self.process.stdout.feed(payload[3:11])
        self.assertTrue(wait_until(lambda: audio.get_position_seconds() == 2 / 12))
        self.assertIsNone(audio.get_next_frame())

        self.process.stdout.feed(payload[11:])
        self.assertTrue(wait_until(lambda: audio.get_position_seconds() == 4 / 12))
        np.testing.assert_array_equal(audio.get_next_frame().samples, samples)

    def test_every_backlogged_frame_is_delivered_in_order(self):
        audio = self.make_audio()
        samples = np.arange(12, dtype=np.float32)

        audio.play()
        self.process.stdout.feed(samples.astype("<f4").tobytes())
        self.assertTrue(wait_until(lambda: audio.get_position_seconds() == 1.0))

        frames = []
        while (frame := audio.get_next_frame()) is not None:
            frames.append(frame)

        self.assertEqual([frame.frame_index for frame in frames], [0, 1, 2])
        self.assertEqual([frame.timestamp for frame in frames], [0.0, 1 / 3, 2 / 3])
        np.testing.assert_array_equal(
            np.concatenate([frame.samples for frame in frames]), samples
        )

if __name__ == "__main__":
    unittest.main()
