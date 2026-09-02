# Adaptive Musical Listening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give VMMC a local, real-time adaptive listening layer that learns each music's own landscape and exposes relative detail, compact sound signatures, protagonism, contextual regimes, and a 12-second silence cycle.

**Architecture:** `AudioAnalyzer` adds only instantaneous/short-frame DSP evidence. A new `AdaptiveLandscape` owns robust multi-scale normalization, while `MusicalMemory` combines that landscape with its existing temporal state to derive signatures, prominence, regime weights, and musical-cycle state. The current gesture, morphology, geometry, and renderer contracts remain intact; the new context is observable in the HUD and becomes the stable input for the later ecology milestone.

**Tech Stack:** Python 3.11+, NumPy 2.x, stdlib dataclasses/enum/deque/statistics, Pygame HUD, and stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-01-musical-form-ecosystem-design.md`

## Global Constraints

- This plan implements only Marco 1: adaptive listening; it does not create persistent secondary bodies.
- All analysis runs locally in real time without internet, neural models, or external music APIs.
- Instantaneous DSP remains in `audio/analyzer.py`; long musical context remains in `memory/`.
- Every elapsed audio frame still crosses memory in order even when rendering is late.
- Relative importance is learned from the music's own history, not fixed genre or loudness expectations.
- Sound identity remains probabilistic; no instrument or voice label is presented as certainty.
- Regimes coexist as continuous weights rather than mutually exclusive labels.
- Twelve continuous seconds of contextual silence end a cycle; 11.99 seconds do not.
- Continuous transitions never reset the cycle merely because the sound changes strongly.
- Every new behavior begins with a test observed failing for the intended reason.
- Every independently reviewed alteration receives its own commit using the project's `feat:`, `fix:`, `test:`, or `docs:` style.

---

### Task 1: Instantaneous timbre and envelope evidence

**Files:**
- Modify: `audio/analyzer.py`
- Modify: `tests/test_contextual_pipeline.py`

**Interfaces:**
- Extends `AudioFeatures` with normalized floats `spectral_flatness`, `harmonicity`, `attack_strength`, and `spectral_spread`, each defaulting to `0.0` for compatibility with constructed fixtures.
- `AudioAnalyzer.analyze(frame) -> AudioFeatures` remains the only public analyzer entry point.
- `AudioAnalyzer` may remember the immediately previous RMS amplitude and spectrum, but no longer musical history.

- [ ] **Step 1: Write failing timbre tests with hand-derived relationships**

Add tests where the production breaks caught are returning constants, reversing tone/noise texture, and failing to detect a sudden envelope rise:

```python
def test_tone_is_more_harmonic_and_less_flat_than_seeded_noise(self):
    samplerate = 48_000
    count = 1_600
    times = np.arange(count) / samplerate
    tone = 0.2 * np.sin(2.0 * np.pi * 440.0 * times)
    noise = np.random.default_rng(7).normal(0.0, 0.2, count)

    tone_features = AudioAnalyzer().analyze(
        AudioFrame(tone, 0.0, samplerate, 0)
    )
    noise_features = AudioAnalyzer().analyze(
        AudioFrame(noise, 0.0, samplerate, 0)
    )

    self.assertGreater(tone_features.harmonicity, noise_features.harmonicity + 0.25)
    self.assertLess(tone_features.spectral_flatness, noise_features.spectral_flatness - 0.25)


def test_sudden_rise_has_more_attack_than_steady_level(self):
    analyzer = AudioAnalyzer()
    quiet = self._tone_frame(amplitude=0.02, timestamp=0.0, frame_index=0)
    loud = self._tone_frame(amplitude=0.4, timestamp=1 / 30, frame_index=1)
    steady = self._tone_frame(amplitude=0.4, timestamp=2 / 30, frame_index=2)

    analyzer.analyze(quiet)
    attack = analyzer.analyze(loud)
    sustained = analyzer.analyze(steady)

    self.assertGreater(attack.attack_strength, sustained.attack_strength + 0.4)
```

Extend the existing finite/normalized test to include all four new fields and assert that a low tone has less normalized `spectral_spread` than seeded broadband noise.

- [ ] **Step 2: Run the focused analyzer tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_contextual_pipeline.ContextualPipelineTests`

Expected: FAIL with missing `AudioFeatures` attributes such as `harmonicity` and `attack_strength`.

- [ ] **Step 3: Implement the minimum DSP evidence**

Add fields and calculations using an epsilon of `1e-12`:

```python
@dataclass
class AudioFeatures:
    # existing fields stay in their current order
    spectral_flatness: float = 0.0
    harmonicity: float = 0.0
    attack_strength: float = 0.0
    spectral_spread: float = 0.0
```

Compute flatness from positive spectrum magnitudes with geometric mean divided by arithmetic mean. Derive harmonicity as the clamped complement of flatness for this DSP-only first milestone. Compute spectral spread as the magnitude-weighted standard deviation around the centroid, normalized by Nyquist. Compute attack as `clamp((rms - previous_rms) * 8.0)` and store current RMS only after deriving the result. Silence returns finite zeroes.

- [ ] **Step 4: Run analyzer tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_contextual_pipeline.ContextualPipelineTests`

Expected: all analyzer and contextual compatibility tests PASS.

- [ ] **Step 5: Commit instantaneous evidence**

```bash
git add audio/analyzer.py tests/test_contextual_pipeline.py
git commit -m "feat: extract adaptive timbre evidence"
```

---

### Task 2: Music-relative adaptive landscape

**Files:**
- Create: `memory/adaptive_landscape.py`
- Create: `tests/test_adaptive_landscape.py`

**Interfaces:**
- Produces immutable `RelativeFeatures(energy, brightness, texture, activity, confidence)` with the first four values clamped to `[-1.0, 1.0]` and confidence to `[0.0, 1.0]`.
- Produces `AdaptiveLandscape(short_rate=0.12, long_rate=0.015, novelty_hold=0.65)`.
- Produces `AdaptiveLandscape.update(features) -> RelativeFeatures` and `reset() -> None`.
- Produces read-only `AdaptiveLandscape.energy_baseline: float`, the clamped long-term energy mean, for contextual-silence decisions in Task 5.
- Consumes `AudioFeatures` fields only; it does not import gesture, morphology, geometry, or renderer code.

- [ ] **Step 1: Write failing landscape tests**

Use literal `AudioFeatures` fixtures and prove adaptation is relative:

```python
def test_same_detail_is_stronger_after_calm_than_intense_history(self):
    calm = AdaptiveLandscape()
    intense = AdaptiveLandscape()
    for index in range(180):
        calm.update(features(index / 30, amplitude=0.05, centroid=0.2))
        intense.update(features(index / 30, amplitude=0.75, centroid=0.7))

    detail = features(6.0, amplitude=0.25, centroid=0.45, flux=0.15)
    calm_relative = calm.update(detail)
    intense_relative = intense.update(detail)

    self.assertGreater(calm_relative.energy, intense_relative.energy + 0.35)
    self.assertGreater(calm_relative.brightness, intense_relative.brightness + 0.35)


def test_steady_intensity_stops_being_novel_to_landscape(self):
    landscape = AdaptiveLandscape()
    first = landscape.update(features(0.0, amplitude=0.6, flux=0.5))
    current = first
    for index in range(1, 240):
        current = landscape.update(features(index / 30, amplitude=0.6, flux=0.5))

    self.assertGreater(current.confidence, 0.8)
    self.assertLess(abs(current.energy), 0.1)
    self.assertLess(abs(current.activity), 0.1)
```

Add reset coverage: after `reset()`, the same sample again has low confidence and neutral relative deviations. Assert every output remains finite and within its documented range.

- [ ] **Step 2: Run landscape tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_adaptive_landscape`

Expected: ERROR importing `memory.adaptive_landscape` because the module does not exist.

- [ ] **Step 3: Implement robust multi-scale normalization**

Implement one private running statistic per dimension (`energy`, `brightness`, `texture`, `activity`) with short and long exponentially weighted mean/variance. Map source values as:

```python
values = {
    "energy": features.amplitude,
    "brightness": features.spectral_centroid,
    "texture": 0.5 * features.spectral_flatness + 0.5 * features.spectral_density,
    "activity": 0.6 * features.spectral_flux + 0.4 * features.attack_strength,
}
```

Before updating a statistic, compute `z = (value - long_mean) / max(sqrt(long_variance), 0.05)` and expose `tanh(z / 2)`. Blend toward the short deviation only after 30 samples. When the maximum absolute relative value exceeds `novelty_hold`, multiply the long update rate by `0.2`, preventing a new event from immediately becoming its own baseline. Confidence is `clamp(sample_count / 180.0)`. `energy_baseline` returns the energy statistic's long mean or `0.0` before the first sample. `reset()` reconstructs empty statistics and count.

- [ ] **Step 4: Run landscape tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_adaptive_landscape`

Expected: all landscape tests PASS deterministically.

- [ ] **Step 5: Commit the adaptive landscape**

```bash
git add memory/adaptive_landscape.py tests/test_adaptive_landscape.py
git commit -m "feat: learn each music adaptive landscape"
```

---

### Task 3: Sound signatures and contextual protagonism

**Files:**
- Modify: `memory/musical_memory.py`
- Modify: `tests/test_musical_context.py`

**Interfaces:**
- Consumes `AdaptiveLandscape.update(features) -> RelativeFeatures` from Task 2.
- Produces immutable `SoundSignature(brightness, noisiness, harmonicity, attack, density)` with normalized `[0.0, 1.0]` fields.
- Extends `MusicalContext` with `relative: RelativeFeatures`, `signature: SoundSignature`, `signature_continuity: float`, and `prominence: float`.
- `MusicalMemory.update(features) -> MusicalContext` remains backward compatible for gesture and morphology consumers.

- [ ] **Step 1: Write failing signature and prominence tests**

Extend the test fixture helper to set flatness, harmonicity, attack, and spread. Add:

```python
def test_returning_signature_recovers_continuity(self):
    memory = MusicalMemory()
    first = None
    for index in range(60):
        first = memory.update(self._features(
            index / 30, energy=0.3, centroid=0.2, flatness=0.1,
            harmonicity=0.9, density=0.2,
        ))
    contrasting = memory.update(self._features(
        2.0, energy=0.3, centroid=0.8, flatness=0.8,
        harmonicity=0.2, density=0.8,
    ))
    returned = memory.update(self._features(
        2.0 + 1 / 30, energy=0.3, centroid=0.2, flatness=0.1,
        harmonicity=0.9, density=0.2,
    ))

    self.assertLess(contrasting.signature_continuity, 0.5)
    self.assertGreater(returned.signature_continuity, contrasting.signature_continuity + 0.3)


def test_subtle_event_can_be_prominent_in_calm_music(self):
    memory = MusicalMemory()
    for index in range(180):
        memory.update(self._features(index / 30, energy=0.03, centroid=0.2))
    context = memory.update(self._features(
        6.0, energy=0.18, flux=0.2, centroid=0.5, attack=0.3,
    ))
    self.assertGreater(context.prominence, 0.55)
```

Add a companion assertion showing the same event has lower prominence after an already intense, bright history. Assert an uncertain/neutral signature still yields finite `prominence` and all new outputs stay normalized.

- [ ] **Step 2: Run musical-memory tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_musical_context.MusicalContextTests`

Expected: FAIL because `MusicalContext` has no `signature`, `signature_continuity`, or `prominence`.

- [ ] **Step 3: Integrate the landscape and signature memory**

Construct `self._landscape = AdaptiveLandscape()` and a bounded deque of the last 360 `SoundSignature` values. Build signatures directly from current DSP evidence:

```python
signature = SoundSignature(
    brightness=_clamp(features.spectral_centroid),
    noisiness=_clamp(features.spectral_flatness),
    harmonicity=_clamp(features.harmonicity),
    attack=_clamp(features.attack_strength),
    density=_clamp(features.spectral_density),
)
```

Define signature distance as the mean absolute field difference. Continuity is the maximum `1.0 - distance` against the previous 90 signatures, with `0.0` for an empty history. Compute prominence from positive relative evidence, existing novelty, persistence, attack, and continuity:

```python
prominence = _clamp(
    max(0.0, relative.energy) * 0.25
    + max(0.0, relative.brightness) * 0.10
    + max(0.0, relative.texture) * 0.15
    + max(0.0, relative.activity) * 0.20
    + novelty * 0.15
    + signature.attack * 0.10
    + signature_continuity * 0.05
)
```

Do not use a semantic instrument label. Append the current signature only after calculating continuity, then return all new public fields on `MusicalContext`.

- [ ] **Step 4: Run memory and downstream tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_musical_context tests.test_gesture_engine tests.test_morphology`

Expected: all tests PASS; existing gesture and morphology behavior remains compatible.

- [ ] **Step 5: Commit signatures and protagonism**

```bash
git add memory/musical_memory.py tests/test_musical_context.py
git commit -m "feat: derive contextual sound protagonism"
```

---

### Task 4: Continuous regime weights and prepared crescendos

**Files:**
- Modify: `memory/musical_memory.py`
- Modify: `tests/test_musical_context.py`

**Interfaces:**
- Produces immutable `RegimeWeights(stability, building, suspension, rupture, climax, release, transition)` with every value normalized to `[0.0, 1.0]`.
- Extends `MusicalContext` with `regimes: RegimeWeights`.
- Regime fields coexist; no enum or winner-takes-all label is introduced.

- [ ] **Step 1: Write failing contextual-regime tests**

Create two histories ending at the same energy: one gradually rises for six seconds, the other stays calm and receives one isolated spike. Assert:

```python
self.assertGreater(prepared.regimes.building, isolated.regimes.building + 0.2)
self.assertGreater(prepared.tension, isolated.tension)
```

Then feed a sharp timbral/energy break and assert `rupture` and `transition` exceed stable-history values by `0.3`. Feed stable low-activity frames after high tension and assert `release` grows while `climax` falls. These tests catch using only current amplitude or making regimes mutually exclusive.

- [ ] **Step 2: Run regime tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_musical_context.MusicalContextTests`

Expected: FAIL because `MusicalContext` has no `regimes` field.

- [ ] **Step 3: Implement smoothed coexisting regime evidence**

Store previous prominence, signature, tension, and regime weights. Derive targets from existing context plus adaptive values:

```python
targets = RegimeWeights(
    stability=_clamp(stability * (1.0 - novelty)),
    building=_clamp(max(0.0, energy_trend) + max(0.0, activity_trend) * 0.6),
    suspension=_clamp(persistence * (1.0 - activity) * 0.8),
    rupture=_clamp(novelty * 0.6 + max(0.0, prominence - previous_prominence)),
    climax=_clamp(tension * prominence),
    release=_clamp(max(0.0, previous_tension - tension) * 2.0 + persistence * (1.0 - energy) * 0.3),
    transition=_clamp((1.0 - signature_continuity) * 0.6 + novelty * 0.4),
)
```

Smooth every target with attack rate `0.18` and release rate `0.04`, except rupture attack `0.35`. Preserve simultaneous nonzero weights. Return an immutable `RegimeWeights` snapshot in each context.

- [ ] **Step 4: Run regime and contextual pipeline tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_musical_context tests.test_contextual_pipeline tests.test_gesture_engine`

Expected: all tests PASS, including the prepared-crescendo distinction.

- [ ] **Step 5: Commit contextual regimes**

```bash
git add memory/musical_memory.py tests/test_musical_context.py
git commit -m "feat: interpret continuous musical regimes"
```

---

### Task 5: Twelve-second silence and musical-cycle lifecycle

**Files:**
- Modify: `memory/adaptive_landscape.py`
- Modify: `memory/musical_memory.py`
- Modify: `tests/test_musical_context.py`

**Interfaces:**
- Produces `CyclePhase(Enum)` values `LISTENING`, `QUIETING`, and `ENDED`.
- Extends `MusicalContext` with `cycle_phase: CyclePhase`, `cycle_index: int`, and `silence_duration: float`.
- `MusicalMemory(silence_end_seconds=12.0, absolute_silence_floor=0.01)` exposes those thresholds as constructor values for deterministic boundary tests.
- `AdaptiveLandscape.reset()` from Task 2 begins the next music's independent landscape.

- [ ] **Step 1: Write failing exact-boundary tests**

After three seconds of active fixtures, feed silence at explicit timestamps:

```python
before = memory.update(self._features(14.99, energy=0.0, flux=0.0))
boundary = memory.update(self._features(15.0, energy=0.0, flux=0.0))

self.assertEqual(before.cycle_phase, CyclePhase.QUIETING)
self.assertAlmostEqual(before.silence_duration, 11.99, places=2)
self.assertEqual(boundary.cycle_phase, CyclePhase.ENDED)
self.assertEqual(boundary.silence_duration, 12.0)
```

Add tests proving: low-level noise at or below `absolute_silence_floor` does not restart the timer; a real new sound after `ENDED` increments `cycle_index`, returns `LISTENING`, resets landscape confidence, and does not retain the previous signature history; a large continuous timbral change without silence remains the same cycle index.

- [ ] **Step 2: Run cycle tests and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_musical_context.MusicalContextTests`

Expected: FAIL because `CyclePhase`, `cycle_phase`, `cycle_index`, and `silence_duration` do not exist.

- [ ] **Step 3: Implement contextual silence tracking**

Compute a contextual floor as `absolute_silence_floor` while landscape confidence is at most `0.5`, otherwise `max(absolute_silence_floor, landscape.energy_baseline * 0.08)`. Treat a frame as musical activity when amplitude exceeds that floor, or when spectral flux exceeds `0.05` while amplitude exceeds `absolute_silence_floor * 0.5`. Store `_silence_started_at`, `_cycle_index`, and `_cycle_phase`.

On the first silent frame, set the start timestamp and `QUIETING`. Derive duration from feature timestamps, never wall clock. At duration `>= silence_end_seconds`, set `ENDED`. While ended, keep returning the final context without resetting repeatedly.

When real activity arrives after `ENDED`, increment the cycle index and call one focused `_reset_cycle_state()` that clears history, signature history, smoothed activity, tension, persistence, regimes, and landscape. Process the new frame as the first sample of `LISTENING`. Strong changes during `LISTENING` never call this reset.

- [ ] **Step 4: Run exact cycle and regression tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_musical_context tests.test_contextual_pipeline tests.test_expressive_pipeline`

Expected: all tests PASS; the 12.00/11.99 boundary is exact from sample-derived timestamps.

- [ ] **Step 5: Commit the musical cycle**

```bash
git add memory/adaptive_landscape.py memory/musical_memory.py tests/test_musical_context.py
git commit -m "feat: close musical cycles after contextual silence"
```

---

### Task 6: Public observability and documentation

**Files:**
- Modify: `main.py`
- Modify: `tests/test_expressive_pipeline.py`
- Modify: `README.md`

**Interfaces:**
- Consumes all Task 3-5 public `MusicalContext` fields.
- `_build_debug_lines(...)` adds `LANDSCAPE`, `SIGNATURE`, and `REGIME` groups without reading private memory attributes.
- Existing `AUDIO`, `CONTEXT`, `GESTURES`, `MORPHOLOGY`, and `COLOR` groups remain present.

- [ ] **Step 1: Write failing HUD tests**

Extend the existing context fixture with real `RelativeFeatures`, `SoundSignature`, `RegimeWeights`, `CyclePhase.QUIETING`, `cycle_index=2`, `silence_duration=4.5`, `signature_continuity=0.7`, and `prominence=0.8`. Assert the joined output contains:

```python
for heading in ("LANDSCAPE", "SIGNATURE", "REGIME"):
    self.assertIn(heading, text)
self.assertIn("cycle=2", text)
self.assertIn("silence=4.50", text)
self.assertIn("prominence=0.80", text)
```

The fixture exposes only public context fields, so any private-memory access fails the test.

- [ ] **Step 2: Run the HUD test and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_expressive_pipeline.ExpressivePipelineTests.test_debug_output_exposes_each_pipeline_layer`

Expected: FAIL because the three new HUD groups are absent.

- [ ] **Step 3: Render public adaptive context minimally**

Append compact lines in `_build_debug_lines`:

```python
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
    f"continuity={context.signature_continuity:.2f} "
    f"prominence={context.prominence:.2f}"
)
lines.append(
    "REGIME "
    f"build={context.regimes.building:.2f} "
    f"rupture={context.regimes.rupture:.2f} "
    f"transition={context.regimes.transition:.2f} "
    f"cycle={context.cycle_index} phase={context.cycle_phase.value} "
    f"silence={context.silence_duration:.2f}"
)
```

- [ ] **Step 4: Document the adaptive-listening milestone**

Add a README section explaining that VMMC learns each music's relative landscape, uses probabilistic DSP signatures rather than guaranteed instrument recognition, preserves continuous transitions, and starts a new ecosystem after 12 seconds of contextual silence. Do not claim multiple visual bodies exist yet.

- [ ] **Step 5: Run HUD and main integration tests and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_expressive_pipeline tests.test_main`

Expected: all tests PASS and existing debug headings remain visible.

- [ ] **Step 6: Commit observability and docs**

```bash
git add main.py tests/test_expressive_pipeline.py README.md
git commit -m "docs: expose adaptive musical listening"
```

---

### Task 7: Full verification

**Files:**
- Verify only: all files changed in Tasks 1-6.

**Interfaces:**
- Consumes the completed Marco 1 and produces verification evidence, not additional behavior.

- [ ] **Step 1: Run the complete deterministic suite**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: every test PASS without physical audio hardware, internet, or a neural model.

- [ ] **Step 2: Compile all application packages**

Run: `.venv/bin/python -m compileall -q audio expression geometry memory renderer state main.py`

Expected: exit status 0 and no output.

- [ ] **Step 3: Check tracked changes and commit history**

Run: `git diff --check && git status --short && git log --oneline -8`

Expected: no whitespace errors, a clean worktree, and separate commits for DSP evidence, landscape, protagonism, regimes, cycle lifecycle, and observability.

- [ ] **Step 4: Perform an optional graphical smoke test**

In a graphical PipeWire session, run `.venv/bin/vmmc --system-audio`, play a calm piece followed by a continuous transition, and inspect `LANDSCAPE`, `SIGNATURE`, and `REGIME`. Then provide 12 seconds of silence and confirm the HUD reaches `phase=ended`. This smoke test validates the environment and artistic tuning; deterministic completion remains based on automated tests.
