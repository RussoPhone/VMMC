# System Audio Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make VMMC analyze the computer's default audio output continuously through PipeWire/PulseAudio when invoked with `--system-audio`.

**Architecture:** A focused `SystemAudioInput` discovers the default sink monitor with `pactl`, starts `parec`, and reads mono float32 PCM on a worker thread into a sample-ordered buffer. It exposes the same public lifecycle and frame-consumption contract already used by `main.py`, so every elapsed frame still traverses analyzer, memory, gestures, morphology, and geometry in order.

**Tech Stack:** Python 3.11+, NumPy, stdlib subprocess/threading, PipeWire with `pipewire-pulse`, `pactl`, `parec`, and stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-01-system-audio-capture-design.md`

## Global Constraints

- Arch Linux with PipeWire and `pipewire-pulse` is the first supported environment.
- Live timestamps and frame indexes come from a monotonic sample cursor, never wall-clock block selection.
- The capture worker performs only blocking input and buffering; it does not analyze music or render.
- Every complete elapsed frame is delivered in order even when rendering is late.
- Live capture is mono analysis input and does not replay or retransmit captured audio.
- Failures are explicit; there is no fallback to a microphone, another source, or a local file.
- `stop()` is idempotent and never waits for a process or thread while holding the component lock.
- The live source remains active through silence and has no natural `FINISHED` state.
- Existing local-file behavior and its original-channel playback remain unchanged.
- Production behavior is written only after its focused test has been observed failing for the expected reason.

---

### Task 1: Default monitor discovery

**Files:**
- Create: `audio/live_input.py`
- Create: `tests/test_live_audio_input.py`

**Interfaces:**
- Consumes: `audio.input.AudioFrame`, `AudioPlaybackError`, and `PlaybackState`.
- Produces: `discover_default_monitor(command_runner=subprocess.run) -> str`.
- `command_runner` accepts a command list plus `capture_output=True`, `text=True`, and `check=False`, returning an object with `returncode`, `stdout`, and `stderr`.

- [ ] **Step 1: Write failing discovery tests**

Add a recording runner with literal responses and tests whose breaking mutations are using the wrong sink, accepting a missing monitor, or leaking `FileNotFoundError`:

```python
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
        runner = RecordingRunner([
            Result("alsa_output.pci-main\n"),
            Result("41\talsa_output.usb.monitor\tmodule\n"
                   "42\talsa_output.pci-main.monitor\tmodule\n"),
        ])
        self.assertEqual(
            discover_default_monitor(runner),
            "alsa_output.pci-main.monitor",
        )
        self.assertEqual(runner.commands[0][0], ["pactl", "get-default-sink"])
        self.assertEqual(runner.commands[1][0], ["pactl", "list", "short", "sources"])

    def test_rejects_absent_default_monitor(self):
        runner = RecordingRunner([Result("main\n"), Result("1\tmic\tmodule\n")])
        with self.assertRaisesRegex(AudioPlaybackError, "monitor.*main"):
            discover_default_monitor(runner)

    def test_reports_missing_pactl(self):
        runner = RecordingRunner([FileNotFoundError("pactl")])
        with self.assertRaisesRegex(AudioPlaybackError, "pactl"):
            discover_default_monitor(runner)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_live_audio_input.DefaultMonitorDiscoveryTests`

Expected: ERROR importing `audio.live_input` because the module does not exist.

- [ ] **Step 3: Implement discovery minimally**

Create `audio/live_input.py` with the public function and one private command helper:

```python
def _run_pactl(command_runner, *arguments):
    try:
        result = command_runner(
            ["pactl", *arguments], capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise AudioPlaybackError("pactl não está instalado ou não está no PATH") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or "erro sem detalhes"
        raise AudioPlaybackError(f"Falha ao consultar o PipeWire/PulseAudio: {detail}")
    return result.stdout


def discover_default_monitor(command_runner=subprocess.run):
    sink = _run_pactl(command_runner, "get-default-sink").strip()
    if not sink:
        raise AudioPlaybackError("Não foi possível descobrir o sink padrão")
    expected = f"{sink}.monitor"
    sources = _run_pactl(command_runner, "list", "short", "sources")
    names = [line.split("\t")[1] for line in sources.splitlines() if "\t" in line]
    if expected not in names:
        raise AudioPlaybackError(f"Fonte monitor não encontrada para o sink {sink}")
    return expected
```

- [ ] **Step 4: Run the discovery tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_live_audio_input.DefaultMonitorDiscoveryTests`

Expected: all three tests PASS.

- [ ] **Step 5: Commit monitor discovery**

```bash
git add audio/live_input.py tests/test_live_audio_input.py
git commit -m "feat: discover default system audio monitor"
```

---

### Task 2: Sequential PCM capture and frames

**Files:**
- Modify: `audio/live_input.py`
- Modify: `tests/test_live_audio_input.py`

**Interfaces:**
- Consumes: `discover_default_monitor(command_runner) -> str` from Task 1.
- Produces: `SystemAudioInput(frame_duration=1/30, samplerate=48000, command_runner=subprocess.run, process_factory=subprocess.Popen, thread_factory=threading.Thread)`.
- Produces public attributes `state: PlaybackState`, `error_message: str | None`, `source_label: str`.
- Produces `play() -> None`, `get_position_seconds() -> float`, `get_next_frame() -> AudioFrame | None`, `is_finished() -> bool`, and `stop() -> None`.
- The process factory receives the exact `parec` command and `stdout=subprocess.PIPE`, `stderr=subprocess.PIPE`, `bufsize=0`.

- [ ] **Step 1: Add a deterministic feedable process and failing frame test**

Use a real worker thread but an in-memory stream that blocks until test bytes are fed:

```python
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
        self.wait_calls += 1
        return self.returncode

    def kill(self):
        self.kill_calls += 1
        self.returncode = -9
        self.stdout.feed(b"")
```

Construct at `samplerate=12`, `frame_duration=1/3`, feed three literal four-sample float32 chunks, wait on a test-only polling helper, then drain the public API:

```python
audio.play()
process.stdout.feed(np.arange(4, dtype="<f4").tobytes())
self.assertTrue(wait_until(lambda: audio.get_position_seconds() == 4 / 12))
frame = audio.get_next_frame()
self.assertEqual(frame.frame_index, 0)
self.assertEqual(frame.timestamp, 0.0)
np.testing.assert_array_equal(frame.samples, np.arange(4, dtype=np.float32))
self.assertFalse(audio.is_finished())
```

- [ ] **Step 2: Run the sequential-frame test and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_live_audio_input.SystemAudioInputTests.test_pcm_frames_follow_the_sample_cursor`

Expected: FAIL because `SystemAudioInput` is not defined.

- [ ] **Step 3: Implement process startup, worker buffering, and public frame reads**

Implement the constructor state and `play()` command:

```python
command = [
    "parec", "--device", monitor, "--format", "float32le",
    "--rate", str(self.samplerate), "--channels", "1", "--raw",
]
self._process = self._process_factory(
    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
)
self.state = PlaybackState.PLAYING
self._thread = self._thread_factory(target=self._capture_loop, daemon=True)
self._thread.start()
```

In `_capture_loop`, preserve incomplete bytes across reads, decode only multiples of four with `np.frombuffer(..., dtype="<f4").copy()`, and append under the lock. Track `_captured_samples` independently of `_analysis_cursor`. `get_next_frame()` returns only complete `frame_size` slices, advances `_analysis_cursor`, and uses `start / samplerate` and `start // frame_size` for timestamp and index. `get_position_seconds()` returns `_captured_samples / samplerate`; `is_finished()` returns `False` for healthy live capture.

- [ ] **Step 4: Add failing tests for fragmented bytes and render backlog**

Feed one frame as `payload[:3]`, `payload[3:11]`, and `payload[11:]`; assert no frame exists before all bytes arrive and the final values match the literal array. Feed three complete frames before consuming and assert indexes `[0, 1, 2]`, timestamps `[0.0, 1/3, 2/3]`, and exact non-overlapping samples.

- [ ] **Step 5: Run live-input tests and verify RED for fragmentation/backlog**

Run: `.venv/bin/python -m unittest -v tests.test_live_audio_input.SystemAudioInputTests`

Expected: at least one new fragmentation or backlog assertion FAILS until residual bytes and independent cursors are implemented.

- [ ] **Step 6: Complete residual-byte and backlog handling**

Keep `_byte_remainder` local to the worker and append decoded arrays to a deque or contiguous pending array. Under one lock, make complete-frame availability depend only on `captured_samples - analysis_cursor >= frame_size`; never discard older unconsumed samples.

- [ ] **Step 7: Run capture tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_live_audio_input.SystemAudioInputTests`

Expected: sequential, fragmented, and backlog tests PASS without accessing a real device.

- [ ] **Step 8: Commit sequential capture**

```bash
git add audio/live_input.py tests/test_live_audio_input.py
git commit -m "feat: stream system audio into sequential frames"
```

---

### Task 3: Explicit failures and safe lifecycle

**Files:**
- Modify: `audio/live_input.py`
- Modify: `tests/test_live_audio_input.py`

**Interfaces:**
- Consumes and preserves every public `SystemAudioInput` interface from Task 2.
- Produces idempotent lifecycle behavior: repeated `play()` while `PLAYING` is a no-op; repeated `stop()` terminates and joins once.
- `get_next_frame()` raises `AudioPlaybackError` after buffered complete frames are drained when the worker has failed.

- [ ] **Step 1: Write failing process-start and unexpected-exit tests**

Add a process factory that raises `FileNotFoundError("parec")` and assert `play()` raises `AudioPlaybackError` containing `parec`, sets `FAILED`, and fills `error_message`. In another test, start normally, set `returncode=7`, put `b""` into stdout, wait for `FAILED`, then assert `get_next_frame()` raises an error containing `código 7`.

- [ ] **Step 2: Run failure tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_live_audio_input.SystemAudioLifecycleTests`

Expected: FAIL because startup and background failures are not yet normalized into the public error contract.

- [ ] **Step 3: Implement explicit failure propagation**

Catch `FileNotFoundError` around process creation, set `FAILED`, and raise `AudioPlaybackError("parec não está instalado ou não está no PATH")`. On unexpected EOF, read a bounded stderr detail, store a message containing the return code, and set `FAILED`. Let `get_next_frame()` emit already-buffered complete frames first, then raise `AudioPlaybackError(self.error_message)`.

- [ ] **Step 4: Write failing idempotence and no-deadlock tests**

Assert two `play()` calls create one process. Call `stop()` twice and assert one `terminate()`, one `wait()`, state `STOPPED`, and no raised exception. Run `stop()` in a daemon test thread with `join(0.5)` and assert it exits, proving the join does not occur under the capture lock.

- [ ] **Step 5: Run lifecycle tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_live_audio_input.SystemAudioLifecycleTests`

Expected: one or more idempotence or join assertions FAIL before cleanup is completed.

- [ ] **Step 6: Implement stop outside locks**

Under the lock, detach local references to process and thread and set a stop event. Outside the lock, call `terminate()`, `wait(timeout=1.0)`, use `kill()` plus a final `wait()` only on `subprocess.TimeoutExpired`, and `join(timeout=1.0)`. Set `STOPPED` unless the component was already `FAILED`; make later `stop()` calls return immediately.

- [ ] **Step 7: Run all live-input tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_live_audio_input`

Expected: discovery, buffering, failure, and lifecycle tests all PASS with no leaked threads.

- [ ] **Step 8: Commit lifecycle safety**

```bash
git add audio/live_input.py tests/test_live_audio_input.py
git commit -m "fix: make live audio lifecycle explicit and safe"
```

---

### Task 4: Application mode, source-aware HUD, and documentation

**Files:**
- Modify: `main.py`
- Modify: `tests/test_main.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `SystemAudioInput` public contract from Tasks 2 and 3.
- Produces: `SYSTEM_AUDIO_FLAG = "--system-audio"`.
- Produces: `create_audio_input(source: str)` returning `SystemAudioInput()` for the flag and `AudioInput(source)` otherwise.
- Modifies: `reset_pipeline(source, previous_audio=None)` to use the public factory.
- Modifies: `main(source=None)` so only local paths are checked with `os.path.exists`.
- Produces: `source_description(source) -> str`, returning `"Áudio do sistema"` for the flag and `os.path.basename(source)` for files.

- [ ] **Step 1: Write failing source-selection tests**

Patch both constructors and assert:

```python
with (
    patch.object(main, "SystemAudioInput", return_value=live) as live_type,
    patch.object(main, "AudioInput") as file_type,
):
    self.assertIs(main.create_audio_input("--system-audio"), live)
live_type.assert_called_once_with()
file_type.assert_not_called()
```

Add the inverse local-file assertion. Test `main.main("--system-audio")` with a renderer that immediately closes and assert `os.path.exists` is not consulted. Assert `source_description("--system-audio") == "Áudio do sistema"` and that the HUD includes that label.

- [ ] **Step 2: Run main tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_main`

Expected: FAIL because `SystemAudioInput`, `create_audio_input`, and source-aware labeling are absent.

- [ ] **Step 3: Implement source-aware composition minimally**

Import `SystemAudioInput`, add the flag and factory, and change `reset_pipeline` to call `create_audio_input(source)`. Keep the existing order: stop the previous source, construct the replacement, create fresh interpretive components, then call `play()`. Skip filesystem existence validation only for the exact flag.

Change `_build_debug_lines` to receive `current_source` and render:

```python
f"Fonte: {source_description(current_source)} | Audio: {status_labels[audio_input.state]}"
```

Keep `O` as the transition from either source to a selected local file; `reset_pipeline` performs the required stop before replacement.

- [ ] **Step 4: Add failing live-loop and background-error tests**

Use a fake live input whose `is_finished()` always returns `False` and a renderer returning one ESC event; assert the loop exits only because of ESC and calls `stop()`. Use another fake whose `get_next_frame()` raises `AudioPlaybackError("captura encerrada")`; assert renderer cleanup occurs and stdout contains the explicit error.

- [ ] **Step 5: Run main tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_main`

Expected: at least one loop-lifetime or background-error assertion FAILS until the live mode is integrated through the existing try/finally boundary.

- [ ] **Step 6: Complete live-loop integration and actionable diagnostics**

Keep the current outer `except AudioPlaybackError` and `finally`. Update the diagnostic to mention `pactl get-default-sink`, `pactl list short sources`, and availability of `parec` when the source is live, while preserving the SoundDevice diagnostic for local-file playback.

- [ ] **Step 7: Document setup and use**

In `README.md`, keep `libpulse` explicit in the Arch package command because it provides both `/usr/bin/pactl` and `/usr/bin/parec`, and add:

```bash
.venv/bin/vmmc --system-audio
```

Explain that the command listens to the default output monitor, works with Spotify/browser/game audio, remains active through silence, and can be checked with `pactl get-default-sink` plus `pactl list short sources`.

- [ ] **Step 8: Run focused integration tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_main tests.test_live_audio_input tests.test_audio_input`

Expected: all focused tests PASS and local-file regression tests remain green.

- [ ] **Step 9: Commit application integration**

```bash
git add main.py tests/test_main.py README.md
git commit -m "feat: add system audio mode"
```

---

### Task 5: Full verification

**Files:**
- Verify only: all tracked source and tests changed in Tasks 1-4.

**Interfaces:**
- Consumes the complete feature; produces verification evidence, not new behavior.

- [ ] **Step 1: Run the complete test suite**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: every test PASS with no hardware, PipeWire session, or physical audio device required.

- [ ] **Step 2: Compile every application package**

Run: `.venv/bin/python -m compileall -q audio expression geometry memory renderer state main.py`

Expected: exit status 0 and no output.

- [ ] **Step 3: Check the final diff and worktree**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; status contains only intentional plan-tracking changes, if any.

- [ ] **Step 4: Perform an optional real-session smoke test**

When a graphical PipeWire session is available, run `.venv/bin/vmmc --system-audio`, play audio through the default output, confirm the HUD reacts and memory continues through silence, then close with ESC. This is environmental confirmation; automated completion does not depend on it.
