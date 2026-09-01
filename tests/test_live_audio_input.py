import io
import queue
import subprocess
import threading
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
        self.assertIs(self.process_calls[0][1]["stderr"], subprocess.PIPE)

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


class SystemAudioLifecycleTests(unittest.TestCase):
    def runner(self):
        return RecordingRunner(
            [Result("main\n"), Result("1\tmain.monitor\tmodule\n")]
        )

    def test_missing_parec_is_an_explicit_start_failure(self):
        def missing_parec(command, **kwargs):
            del command, kwargs
            raise FileNotFoundError("parec")

        audio = SystemAudioInput(
            command_runner=self.runner(), process_factory=missing_parec
        )

        with self.assertRaisesRegex(AudioPlaybackError, "parec"):
            audio.play()

        self.assertEqual(audio.state, PlaybackState.FAILED)
        self.assertIn("parec", audio.error_message)

    def test_unexpected_capture_exit_is_reported_after_buffered_frames(self):
        process = FakeProcess()
        process.stderr = io.BytesIO(b"backend disconnected")
        audio = SystemAudioInput(
            frame_duration=1.0 / 3.0,
            samplerate=12,
            command_runner=self.runner(),
            process_factory=lambda command, **kwargs: process,
        )
        self.addCleanup(audio.stop)
        samples = np.arange(4, dtype=np.float32)

        audio.play()
        process.stdout.feed(samples.astype("<f4").tobytes())
        self.assertTrue(wait_until(lambda: audio.get_position_seconds() == 4 / 12))
        process.returncode = 7
        process.stdout.feed(b"")
        self.assertTrue(wait_until(lambda: audio.state is PlaybackState.FAILED))

        np.testing.assert_array_equal(audio.get_next_frame().samples, samples)
        with self.assertRaisesRegex(
            AudioPlaybackError, "código 7.*backend disconnected"
        ):
            audio.get_next_frame()

    def test_play_and_stop_are_idempotent(self):
        process = FakeProcess()
        process_calls = []

        def process_factory(command, **kwargs):
            process_calls.append((command, kwargs))
            return process

        audio = SystemAudioInput(
            command_runner=self.runner(), process_factory=process_factory
        )

        audio.play()
        audio.play()
        audio.stop()
        audio.stop()

        self.assertEqual(len(process_calls), 1)
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.wait_calls, 1)
        self.assertEqual(audio.state, PlaybackState.STOPPED)

    def test_stop_does_not_deadlock_while_capture_is_blocked(self):
        process = FakeProcess()
        audio = SystemAudioInput(
            command_runner=self.runner(),
            process_factory=lambda command, **kwargs: process,
        )
        audio.play()

        worker = threading.Thread(target=audio.stop, daemon=True)
        worker.start()
        worker.join(0.5)

        self.assertFalse(worker.is_alive(), "stop ficou bloqueado no lock")
        self.assertEqual(audio.state, PlaybackState.STOPPED)

    def test_stop_kills_capture_process_that_ignores_terminate(self):
        class HangingProcess(FakeProcess):
            def wait(self, timeout=None):
                self.wait_calls += 1
                if self.kill_calls == 0:
                    raise subprocess.TimeoutExpired("parec", timeout)
                return self.returncode

        process = HangingProcess()
        audio = SystemAudioInput(
            command_runner=self.runner(),
            process_factory=lambda command, **kwargs: process,
        )
        audio.play()

        audio.stop()

        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.kill_calls, 1)
        self.assertEqual(process.wait_calls, 2)

    def test_thread_start_failure_cleans_up_capture_process(self):
        class FailingThread:
            def start(self):
                raise RuntimeError("thread unavailable")

        process = FakeProcess()
        audio = SystemAudioInput(
            command_runner=self.runner(),
            process_factory=lambda command, **kwargs: process,
            thread_factory=lambda **kwargs: FailingThread(),
        )

        with self.assertRaisesRegex(AudioPlaybackError, "thread unavailable"):
            audio.play()

        self.assertEqual(audio.state, PlaybackState.FAILED)
        self.assertIn("thread unavailable", audio.error_message)
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.wait_calls, 1)

    def test_blocked_stderr_reader_does_not_delay_eof_failure(self):
        class BlockingStderr:
            def __init__(self):
                self.read_called = threading.Event()
                self.release = threading.Event()

            def read(self, size):
                del size
                self.read_called.set()
                self.release.wait(1.0)
                return b"late detail"

        process = FakeProcess()
        process.stderr = BlockingStderr()
        process.returncode = 9
        audio = SystemAudioInput(
            command_runner=self.runner(),
            process_factory=lambda command, **kwargs: process,
        )
        try:
            audio.play()
            self.assertTrue(process.stderr.read_called.wait(0.1))
            process.stdout.feed(b"")

            self.assertTrue(
                wait_until(lambda: audio.state is PlaybackState.FAILED, timeout=0.1),
                "EOF did not become an explicit failure promptly",
            )
        finally:
            process.stderr.release.set()
            audio.stop()

    def test_concurrent_play_calls_create_only_one_capture_process(self):
        processes = []
        start_barrier = threading.Barrier(3)

        def command_runner(command, **kwargs):
            del kwargs
            if command[1:] == ["get-default-sink"]:
                return Result("main\n")
            return Result("1\tmain.monitor\tmodule\n")

        def process_factory(command, **kwargs):
            del command, kwargs
            process = FakeProcess()
            processes.append(process)
            time.sleep(0.05)
            return process

        audio = SystemAudioInput(
            command_runner=command_runner,
            process_factory=process_factory,
        )
        errors = []

        def start_audio():
            start_barrier.wait()
            try:
                audio.play()
            except Exception as exc:
                errors.append(exc)

        workers = [threading.Thread(target=start_audio) for _ in range(2)]
        for worker in workers:
            worker.start()
        start_barrier.wait()
        for worker in workers:
            worker.join(0.5)

        try:
            self.assertEqual(errors, [])
            self.assertEqual(len(processes), 1)
        finally:
            audio.stop()
            for process in processes:
                if process.returncode is None:
                    process.terminate()

if __name__ == "__main__":
    unittest.main()
