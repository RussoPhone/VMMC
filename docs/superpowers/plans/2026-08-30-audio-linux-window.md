# Linux Audio and Resizable Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproduce audio reliably through PipeWire/PortAudio on Arch Linux, keep contextual analysis synchronized, and make the Pygame window maximizable.

**Architecture:** `AudioInput` owns decoding, a sample-driven output callback, sequential analysis frames, and a public playback state. `main.py` consumes only that public contract and drains available frames before drawing. `Renderer` owns resize-aware viewport geometry.

**Tech Stack:** Python 3.11+, NumPy, SoundFile/libsndfile, SoundDevice/PortAudio, Pygame, stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-30-audio-linux-window-design.md`

## Global Constraints

- Arch Linux with PipeWire/PulseAudio is a required platform.
- Audio failures must be explicit; silent fallback is not the default.
- Playback samples are sequential and preserve source channels; analysis samples are mono.
- Contextual analysis must not discard elapsed frames merely because rendering is slower.
- `main.py` must not access private backend attributes.
- New production behavior is introduced by a test observed failing first.
- Existing tracked bytecode cleanup is outside this change.

---

### Task 1: Sample-driven audio engine

**Files:**
- Create: `tests/test_audio_input.py`
- Modify: `audio/input.py`

**Interfaces:**
- Produces: `PlaybackState`, `AudioPlaybackError`, and `AudioInput(file_path, frame_duration=1/30, stream_factory=None)`.
- Produces: `AudioInput.state`, `error_message`, `play()`, `get_position_seconds()`, `get_next_frame()`, `is_finished()`, and `stop()`.
- Stream factories accept SoundDevice-compatible keyword arguments and return objects with `start()`, `stop()`, `close()`, and `active`.

- [ ] **Step 1: Write the failing callback and channel-preservation tests**

Create a real temporary stereo WAV and a `FakeOutputStream` whose `pump(frames)` calls the production callback. Assert that two pumps return consecutive source samples, output remains stereo, and the returned analysis frame equals the channel mean.

```python
class FakeOutputStream:
    def __init__(self, **kwargs):
        self.callback = kwargs["callback"]
        self.finished_callback = kwargs["finished_callback"]
        self.channels = kwargs["channels"]
        self.active = False

    def start(self):
        self.active = True

    def pump(self, frames):
        out = np.empty((frames, self.channels), dtype=np.float32)
        try:
            self.callback(out, frames, None, None)
        except sd.CallbackStop:
            self.active = False
            self.finished_callback()
        return out
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_audio_input -v`

Expected: FAIL because `AudioInput` does not accept `stream_factory`, uses mono playback, and chooses blocks from wall-clock time.

- [ ] **Step 3: Implement sequential playback and public state minimally**

Replace the wall-clock cursor with `_playback_cursor`, retain `_playback_samples` as 2D and derive `_analysis_samples` with `mean(axis=1)`. Add:

```python
class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    FINISHED = "finished"
    FAILED = "failed"

class AudioPlaybackError(RuntimeError):
    pass
```

The output callback snapshots `start = _playback_cursor`, copies `self._playback_samples[start:end]`, advances the cursor by copied samples, pads only the tail, and raises `sd.CallbackStop` at EOF. `play()` creates the stream with the source sample rate and channel count.

- [ ] **Step 4: Add failing lifecycle, no-deadlock, and drain tests**

Assert independently that:

```python
self.audio.play()
self.stream.pump(8)
self.assertEqual(self.audio.state, PlaybackState.PLAYING)
self.assertAlmostEqual(self.audio.get_position_seconds(), 8 / self.sample_rate)

frame0 = self.audio.get_next_frame()
frame1 = self.audio.get_next_frame()
self.assertEqual((frame0.frame_index, frame1.frame_index), (0, 1))
```

Use a daemon thread plus `join(0.5)` around `get_next_frame()` and assert it completes, so the old nested-lock behavior fails without hanging the suite. Cover natural EOF, start failure setting `FAILED` and raising `AudioPlaybackError`, and two consecutive `stop()` calls.

- [ ] **Step 5: Run the lifecycle tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_audio_input -v`

Expected: FAIL on the first still-missing lifecycle behavior, with no test process hanging.

- [ ] **Step 6: Implement lifecycle and sequential analysis minimally**

Use separate playback and analysis cursors. Snapshot cursor/state under a non-reentrant lock, but never call another locking method while holding it. The finished callback sets a `threading.Event`; `get_next_frame()` emits all complete elapsed frames and a padded tail after output completion. `is_finished()` becomes true only after output completion and delivery of the tail. Move stream `stop()`/`close()` outside lock-held sections.

- [ ] **Step 7: Run audio tests and verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_audio_input -v`

Expected: all audio input tests PASS with no warnings or leaked threads.

- [ ] **Step 8: Commit the audio engine**

```bash
git add audio/input.py tests/test_audio_input.py
git commit -m "fix: make audio playback sample-driven"
```

---

### Task 2: Main-loop lifecycle and public contract

**Files:**
- Create: `tests/test_main.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: `PlaybackState`, `AudioPlaybackError`, and the public `AudioInput` methods from Task 1.
- Produces: `drain_audio_frames(audio_input, analyzer, memory)` returning the latest `(features, context)` pair or `(None, None)`.
- Produces: `_build_debug_lines(...)` that derives audio text from `audio_input.state`.
- Produces: `cli()` forwarding an optional first positional path to `main()`.

- [ ] **Step 1: Write failing public-contract tests**

Use a small fake input with two real `AudioFrame` values and no private attributes. Assert `drain_audio_frames` invokes the real analyzer/memory sequence for both frames and returns the second result. Assert `_build_debug_lines` includes `Audio: REPRODUZINDO` for `PlaybackState.PLAYING` without consulting `_mixer_available` or `_device_available`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_main -v`

Expected: FAIL because `drain_audio_frames` is absent and the HUD accesses `_mixer_available`.

- [ ] **Step 3: Implement the public integration minimally**

Add a drain loop:

```python
def drain_audio_frames(audio_input, analyzer, memory):
    latest_features = latest_context = None
    while (frame := audio_input.get_next_frame()) is not None:
        latest_features = analyzer.analyze(frame)
        latest_context = memory.update(latest_features)
    return latest_features, latest_context
```

Map public playback states to Portuguese HUD labels. On file replacement call `audio_input.stop()` first. Wrap the application lifecycle in `try/finally` so `audio_input.stop()` and `renderer.quit()` are always attempted. Catch `AudioPlaybackError`, print one actionable error, and exit non-destructively.

Keep command-line dispatch explicit:

```python
def cli():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(audio_path)

if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: Run main and audio tests and verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_main tests.test_audio_input -v`

Expected: PASS.

- [ ] **Step 5: Commit main-loop integration**

```bash
git add main.py tests/test_main.py
git commit -m "fix: integrate public audio playback state"
```

---

### Task 3: Maximizable responsive window

**Files:**
- Create: `tests/test_renderer.py`
- Modify: `renderer/renderer.py`

**Interfaces:**
- Produces: `viewport_for_size(width: int, height: int) -> tuple[tuple[int, int], float]`.
- `Renderer` consumes that helper during initialization and before every draw.

- [ ] **Step 1: Write failing viewport and window-mode tests**

Hand-check exact expectations:

```python
self.assertEqual(viewport_for_size(1000, 600), ((500, 300), 180.0))
self.assertEqual(viewport_for_size(400, 900), ((200, 450), 120.0))
```

Patch `pygame.display.set_mode`, construct `Renderer`, and assert the call is `set_mode((800, 800), pygame.RESIZABLE)`. Return a fake surface whose `get_size()` changes and assert a draw refreshes center and radius.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_renderer -v`

Expected: FAIL because the helper is absent and the mode is not resizable.

- [ ] **Step 3: Implement responsive viewport minimally**

Add:

```python
def viewport_for_size(width, height):
    return (width // 2, height // 2), min(width, height) * 0.3
```

Pass `pygame.RESIZABLE` to `set_mode`. Before mapping vertices in `draw()`, call `self.screen.get_size()`, update `width`, `height`, `center`, and `radius_px`, then render normally.

- [ ] **Step 4: Run renderer and complete tests and verify GREEN**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit window behavior**

```bash
git add renderer/renderer.py tests/test_renderer.py
git commit -m "feat: make visualizer window resizable"
```

---

### Task 4: Reproducible setup and agent context

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `AGENTS.md`
- Modify: `.gitignore`

**Interfaces:**
- Produces console command: `vmmc [audio_path]` mapped to `main:cli`.
- Produces test command: `python -m unittest discover -s tests -v`.
- Produces Project Memory ID: `vmmc` without absolute paths in repository files.

- [ ] **Step 1: Declare runtime metadata**

Create PEP 621 metadata with `requires-python = ">=3.11"`, dependencies `numpy>=2,<3`, `soundfile>=0.13,<1`, `sounddevice>=0.5,<1`, and `pygame>=2.6,<3`. Configure setuptools to package `main.py` and the existing package directories, and expose `vmmc = "main:cli"`.

- [ ] **Step 2: Write the concise README**

Document the contextual-memory idea, Arch packages, venv/install commands, `vmmc arquivo.wav`, file-dialog mode, `[O]`/`[ESC]`, module flow, tests, and PipeWire troubleshooting commands `pactl info` and `python -m sounddevice`.

- [ ] **Step 3: Write agent orientation**

Create `AGENTS.md` with the central product invariant, component boundaries, audio concurrency rules, verification commands, and the managed Project Memory block using `Project ID: vmmc`. Do not include machine-specific paths.

- [ ] **Step 4: Ignore generated files**

Add `.venv/`, `venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, build artifacts, and Aider local state to `.gitignore`. Do not delete or stage pre-existing tracked bytecode changes.

- [ ] **Step 5: Verify editable installation without dependency downloads**

Run: `.venv/bin/python -m pip install -e . --no-deps`

Expected: editable package installs. Run `.venv/bin/python -c "import main, audio.input, renderer.renderer; assert callable(main.cli)"` as the noninteractive entry-point check.

- [ ] **Step 6: Run the complete test suite**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 7: Commit setup and documentation**

```bash
git add pyproject.toml README.md AGENTS.md .gitignore
git commit -m "docs: add reproducible Arch Linux setup"
```

---

### Task 5: Final verification and durable handoff

**Files:**
- Modify outside repository: Project Memory `Current State.md`, `Handoff.md`, `Coverage.md`

**Interfaces:**
- Consumes all prior tasks.
- Produces verified completion evidence and future-agent handoff.

- [ ] **Step 1: Run static and automated verification**

Run:

```bash
.venv/bin/python -m compileall -q audio geometry memory renderer state main.py
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

Expected: exit status 0 for every command and no warnings from project code.

- [ ] **Step 2: Run the synthetic pipeline smoke test**

Run: `.venv/bin/python -m unittest tests.test_audio_input.AudioInputTests.test_stereo_callback_and_analysis_frames_are_sequential -v`

Expected: PASS. This test creates a real stereo WAV, executes the production callback through the deterministic stream, drains every analysis frame, and verifies ordering, channel handling, final state, and frame count without requiring an audio server.

- [ ] **Step 3: Inspect repository state**

Run: `git status --short` and `git log -6 --oneline`.

Expected: only known pre-existing/generated bytecode changes remain unstaged; implementation and documentation commits are present.

- [ ] **Step 4: Update durable project memory**

Update the configured `vmmc` Project Memory notes with only verified results, exact commands, remaining real-device validation if any, and links to the design/spec files by repository-relative path. Do not claim an audible device test unless it completed successfully.

- [ ] **Step 5: Commit any final repository-only correction found by verification**

If verification requires a repository correction, introduce it with a failing regression test, rerun all checks, and commit only those repository files. If no correction is needed, do not create an empty commit.
