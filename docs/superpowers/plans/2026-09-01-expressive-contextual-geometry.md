# Expressive Contextual Geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a context-driven expressive and morphological layer so VMMC's geometry represents musical trajectory rather than direct feature mappings.

**Architecture:** Extend local DSP features, derive time-windowed musical context, interpret coupled gestures, and evolve a persistent morphology before generating render-ready geometry. Preserve the tested audio input and keep the renderer ignorant of musical concepts.

**Tech Stack:** Python 3.11+, NumPy, SoundFile, SoundDevice, Pygame, unittest

**Spec:** `docs/superpowers/specs/2026-09-01-expressive-contextual-geometry-design.md`

## Global Constraints

- No machine learning, emotional labels, or instrument recognition.
- Every continuous descriptor, context, gesture, and morphology value is finite and clamped to `0.0–1.0` unless explicitly an angle.
- No independent random values per frame.
- Renderer receives geometry and color only; it does not import audio, memory, or expression modules.
- Preserve sample-cursor audio playback and Linux behavior.
- Implement behavior changes test-first.

---

### Task 1: Acoustic Morphology Descriptors

**Files:**
- Modify: `audio/analyzer.py`
- Modify: `tests/test_contextual_pipeline.py`

**Interfaces:**
- Consumes: `AudioFrame(samples, timestamp, samplerate, frame_index)`
- Produces: `AudioFeatures` fields `spectral_centroid`, `zero_crossing_rate`, `spectral_density`, `spectral_stability`

- [ ] **Step 1: Add failing synthetic descriptor tests**

Use silence, a 100 Hz sine, a 4 kHz sine, and deterministic alternating-sign noise. Assert high sine centroid exceeds low sine centroid, noise ZCR exceeds sine ZCR, density is normalized, and identical consecutive spectra have stability above `0.95`.

- [ ] **Step 2: Verify the tests fail because fields are absent**

Run: `.venv/bin/python -m unittest tests.test_contextual_pipeline -v`
Expected: errors naming missing descriptor attributes.

- [ ] **Step 3: Implement normalized descriptors**

Extend `AudioFeatures` with four defaults of `0.0` for fixture compatibility. Compute centroid as the spectral weighted frequency divided by Nyquist, ZCR as sign transitions divided by sample transitions, density as bins above 10% of peak divided by bin count, and stability as `1 - normalized spectral distance` from the prior spectrum.

- [ ] **Step 4: Run contextual and audio tests**

Run: `.venv/bin/python -m unittest tests.test_contextual_pipeline tests.test_audio_input -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add audio/analyzer.py tests/test_contextual_pipeline.py
git commit -m "feat: extract morphology-oriented audio descriptors"
```

### Task 2: Time-Windowed Musical Context

**Files:**
- Modify: `memory/musical_memory.py`
- Create: `tests/test_musical_context.py`

**Interfaces:**
- Consumes: extended `AudioFeatures`
- Produces: `MusicalContext(energy, short_energy, medium_energy, energy_trend, activity, activity_trend, novelty, stability, tension, persistence, spectral_centroid, zero_crossing_rate, spectral_density, onset)`

- [ ] **Step 1: Write failing context sequence tests**

Create literal 30 FPS sequences for steady energy, rising energy, a novel onset, and post-intensity silence. Assert steady context has high stability/low novelty, rising context has positive trends/tension, the novel onset has higher novelty than repetition, and post-intensity context retains persistence.

- [ ] **Step 2: Verify failure against the five-field context**

Run: `.venv/bin/python -m unittest tests.test_musical_context -v`
Expected: missing `short_energy`, `medium_energy`, `novelty`, `stability`, or `persistence`.

- [ ] **Step 3: Implement two timestamp windows and residual state**

Store compact samples containing timestamp, energy, activity, centroid, ZCR, density, and local stability. Prune at 12 seconds; compute the short subset at 2 seconds. Accumulate tension under positive energy/activity trend and decay it slowly; update persistence with fast attack and slow release.

- [ ] **Step 4: Preserve compatibility aliases**

Expose `energy_average` as `short_energy` so existing debug/tests keep working during integration. Keep every context scalar normalized except signed trends, which are clamped to `-1.0–1.0`.

- [ ] **Step 5: Run memory and existing contextual tests**

Run: `.venv/bin/python -m unittest tests.test_musical_context tests.test_contextual_pipeline -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add memory/musical_memory.py tests/test_musical_context.py tests/test_contextual_pipeline.py
git commit -m "feat: derive multi-scale musical context"
```

### Task 3: Coupled Expressive Gestures

**Files:**
- Create: `expression/__init__.py`
- Create: `expression/gesture_engine.py`
- Create: `tests/test_gesture_engine.py`

**Interfaces:**
- Consumes: `MusicalContext`
- Produces: `GestureEngine.update(context: MusicalContext, dt: float) -> GestureState`
- Produces: `GestureState(pressure, release, impact, suspension, expansion, rupture)`

- [ ] **Step 1: Write failing gesture relationship tests**

Simulate stable-high energy, a rising 3-second crescendo, a drop after crescendo, the same drop without crescendo, silence after intensity, and repeated identical onsets. Assert crescendo pressure exceeds stable pressure; post-crescendo drop release/expansion exceeds isolated drop; post-intensity silence raises suspension; repeated impacts diminish.

- [ ] **Step 2: Verify imports fail**

Run: `.venv/bin/python -m unittest tests.test_gesture_engine -v`
Expected: `ModuleNotFoundError: expression`.

- [ ] **Step 3: Implement GestureState and coupled engine**

Use a private pressure reservoir. Growth and tension charge it; release consumes it. Compute impact from onset, novelty, reservoir, and inverse stability; rupture from impact, novelty, ZCR, and density; expansion from release and present energy; suspension from low energy and prior event residue. Smooth each gesture with separate attack/release rates and clamp `dt` to `0.0–0.1`.

- [ ] **Step 4: Run gesture tests**

Run: `.venv/bin/python -m unittest tests.test_gesture_engine -v`
Expected: all relationships pass without exact-value coupling.

- [ ] **Step 5: Commit**

```bash
git add expression tests/test_gesture_engine.py
git commit -m "feat: interpret coupled expressive gestures"
```

### Task 4: Persistent Coupled Morphology

**Files:**
- Create: `state/morphology.py`
- Create: `tests/test_morphology.py`
- Keep temporarily: `state/visual_state.py`

**Interfaces:**
- Consumes: `MorphologyController.update(context: MusicalContext, gestures: GestureState, dt: float) -> MorphologyState`
- Produces: `MorphologyState(wave, mass, shard, noise, roughness, elasticity, symmetry, density, fluidity, expansion, compression, rotation, brightness, saturation, hue, color_stability, fragmentation, residue)`

- [ ] **Step 1: Write failing neutral and coupling tests**

Assert the default state is neutral and normalized. Feed smooth low-ZCR stable context and assert wave/fluidity dominate shard; feed bright rough rupture and assert shard/roughness/fragmentation rise; feed pressure then release and assert compression precedes expansion; remove stimulus and assert residue decays rather than vanishes.

- [ ] **Step 2: Verify module import fails**

Run: `.venv/bin/python -m unittest tests.test_morphology -v`
Expected: missing `state.morphology`.

- [ ] **Step 3: Implement target coupling and asymmetric smoothing**

Derive mass from bass proxy (`1 - centroid`) plus density/persistence; wave/fluidity from spectral stability and low ZCR; shard/roughness from centroid, ZCR, novelty, and rupture; compression from pressure; expansion from release/expansion gesture. Couple symmetry inversely to rupture/noise, and residue to prior roughness/fragmentation with slow release.

- [ ] **Step 4: Implement persistent color**

Brightness follows smoothed energy, saturation follows tension/impact, hue drifts toward a centroid/activity-derived target on the shortest circular path, and color stability follows musical stability. Keep RGB conversion out of this module.

- [ ] **Step 5: Run morphology and gesture tests**

Run: `.venv/bin/python -m unittest tests.test_morphology tests.test_gesture_engine -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add state/morphology.py tests/test_morphology.py
git commit -m "feat: evolve persistent musical morphology"
```

### Task 5: Render-Ready Geometry and Temporary Fragments

**Files:**
- Modify: `geometry/deformation.py`
- Create: `geometry/snapshot.py`
- Modify: `renderer/renderer.py`
- Create: `tests/test_geometry_expression.py`
- Modify: `tests/test_renderer.py`

**Interfaces:**
- Consumes: `GeometryBuilder.build(shape, morphology, time_elapsed, dt) -> GeometrySnapshot`
- Produces: `GeometrySnapshot(body_vertices, fragments, fill_color, outline_color)`
- Produces: `Fragment(vertices, color)` for renderer; lifecycle remains inside geometry builder/state

- [ ] **Step 1: Write failing geometry snapshot tests**

Assert neutral morphology yields a near-circle, same inputs yield identical vertices/colors, small time increments move vertices only slightly, rupture can create at most six fragments, and subsequent calm frames reduce fragment count or displacement.

- [ ] **Step 2: Verify missing snapshot API**

Run: `.venv/bin/python -m unittest tests.test_geometry_expression -v`
Expected: missing `GeometrySnapshot` or `GeometryBuilder`.

- [ ] **Step 3: Implement body deformation and HSL color conversion**

Combine low harmonics for wave, angular harmonics for shard, deterministic irrational-frequency harmonics for roughness/noise, and asymmetry weighted by `1 - symmetry`. Apply compression anisotropically and expansion radially. Convert morphology hue/saturation/brightness into RGB tuples in geometry.

- [ ] **Step 4: Implement bounded deterministic fragment lifecycle**

Maintain at most six fragment records in a `GeometryBuilder`. Spawn from fixed contour sectors when fragmentation crosses successive levels; advance using morphology elasticity/expansion and age; dissolve/return under stability. Never call `random()`.

- [ ] **Step 5: Update renderer contract test-first**

Change renderer tests to pass a `GeometrySnapshot`; assert body and fragment polygons use snapshot colors. Then change `Renderer.draw(snapshot, debug_lines)` without importing upstream modules.

- [ ] **Step 6: Run geometry and renderer tests**

Run: `.venv/bin/python -m unittest tests.test_geometry_expression tests.test_renderer -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add geometry renderer/renderer.py tests/test_geometry_expression.py tests/test_renderer.py
git commit -m "feat: render expressive body and temporary fragments"
```

### Task 6: Pipeline Integration, Debug, and Linux Verification

**Files:**
- Modify: `main.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `tests/test_main.py`
- Create: `tests/test_expressive_pipeline.py`
- Remove after migration: `state/visual_state.py`

**Interfaces:**
- Consumes: analyzer, memory, `GestureEngine`, `MorphologyController`, `GeometryBuilder`, renderer
- Produces: full frame flow and grouped debug output

- [ ] **Step 1: Write failing full-pipeline ordering test**

Feed two queued frames through a helper that records calls. Assert each frame reaches analyzer → memory → gesture → morphology in order, rather than updating expression only once per render.

- [ ] **Step 2: Write failing grouped debug test**

Build complete dataclass fixtures and assert output contains `AUDIO`, `CONTEXT`, `GESTURES`, `MORPHOLOGY`, and `COLOR` groups with the selected values.

- [ ] **Step 3: Verify integration tests fail against the old pipeline**

Run: `.venv/bin/python -m unittest tests.test_expressive_pipeline tests.test_main -v`
Expected: missing gesture/morphology pipeline arguments and debug groups.

- [ ] **Step 4: Integrate every elapsed audio frame**

Replace `drain_audio_frames` with a helper that sends every frame through analyzer, memory, gesture, and morphology using timestamp deltas. `main()` retains the latest outputs, asks `GeometryBuilder` for a snapshot each render, and passes it to renderer.

- [ ] **Step 5: Replace legacy visual state and update packaging**

Remove `state/visual_state.py` and legacy imports after tests no longer use them. Add `expression` to setuptools package discovery. Update README/AGENTS pipeline descriptions and debug fields.

- [ ] **Step 6: Run the full automated suite**

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q audio expression geometry memory renderer state main.py
.venv/bin/python -m pip check
git diff --check
```

Expected: all tests pass, compileall is silent, dependencies are consistent, and Git diff has no whitespace errors.

- [ ] **Step 7: Run real Linux smoke test**

Run: `timeout 15s .venv/bin/python main.py /home/russophone/Videos/Youtube/cidade.wav`
Expected: audible playback, responsive expressive body, bounded fragments, and grouped debug output.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: integrate expressive contextual geometry"
```
