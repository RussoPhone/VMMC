import unittest

from audio.input import AudioPlaybackError
from audio.live_input import discover_default_monitor


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


if __name__ == "__main__":
    unittest.main()
