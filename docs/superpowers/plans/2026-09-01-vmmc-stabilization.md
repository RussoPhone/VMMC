# VMMC Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Leave VMMC flat, Linux-executable, observable, and demonstrably contextual with the smallest safe change set.

**Architecture:** Preserve the existing Audio → Memory → State → Geometry → Renderer boundaries. Add tests around the untested contextual core, change production code only where those tests expose a gap, and retain the existing audio backend.

**Tech Stack:** Python 3.11+, NumPy, SoundFile, SoundDevice, Pygame, unittest

**Spec:** `docs/superpowers/specs/2026-09-01-vmmc-contextual-recovery-design.md`

## Global Constraints

- Linux execution is required.
- Keep SoundFile/SoundDevice for audio and Pygame for display/events/drawing.
- Do not depend on `pygame.mixer` or require `pygame.font`.
- Keep one deformable shape and no new subsystems.
- Use tests before behavior changes.

---

### Task 1: Flatten the Canonical Repository

**Files:**
- Move: all tracked files and `.git/` from `vmmc/` to repository root
- Remove: outer empty `.git/`, `.venv/`, `env/`, `v/`, nested `.venv/`, nested `venv/`

**Interfaces:**
- Consumes: clean inner Git repository at commit containing this plan
- Produces: `/home/russophone/Ideias/VMMC` as the canonical Git root

- [ ] **Step 1: Record repository state**

Run: `git -C vmmc status --short && git -C vmmc log -1 --oneline`
Expected: clean status and the plan commit at HEAD.

- [ ] **Step 2: Promote the inner repository safely**

Move the empty outer `.git` to a temporary backup, move inner tracked/hidden content including `.git` to the root, and verify `git rev-parse --show-toplevel` returns `/home/russophone/Ideias/VMMC`.

- [ ] **Step 3: Remove only confirmed redundant environments**

Delete the explicitly approved `.venv`, `env`, `v`, and nested environment directories after resolving their exact paths. Recreate one root `.venv` with `python -m venv .venv` and install with `.venv/bin/pip install -e .`.

- [ ] **Step 4: Verify history and baseline**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: 20 baseline tests pass.

### Task 2: Prove the Contextual Core

**Files:**
- Create: `tests/test_contextual_pipeline.py`
- Modify only if a test requires it: `audio/analyzer.py`, `memory/musical_memory.py`, `state/visual_state.py`

**Interfaces:**
- Consumes: `AudioAnalyzer.analyze(AudioFrame) -> AudioFeatures`, `MusicalMemory.update(AudioFeatures) -> MusicalContext`, `VisualStateController.update(MusicalContext, float) -> VisualState`
- Produces: automated proof of normalized features, history-dependent context, and persistent visual response

- [ ] **Step 1: Write analyzer bounds test**

Create synthetic silence and 440 Hz `AudioFrame` values, analyze them, and assert every scalar feature is finite and in `[0.0, 1.0]`.

- [ ] **Step 2: Run the analyzer test**

Run: `.venv/bin/python -m unittest tests.test_contextual_pipeline.ContextualPipelineTests.test_analyzer_outputs_are_finite_and_normalized -v`
Expected: pass; if it fails, make the smallest normalization correction and rerun.

- [ ] **Step 3: Write the history contrast test**

Feed one `MusicalMemory` 90 calm frames and another 90 intense frames at 30 FPS, then feed both the same final `AudioFeatures(amplitude=0.8, spectral_flux=0.2, ...)`. Assert their `energy_average`, `energy_trend`, and `tension` differ.

- [ ] **Step 4: Run the history test and minimally correct memory if needed**

Run: `.venv/bin/python -m unittest tests.test_contextual_pipeline.ContextualPipelineTests.test_same_instant_has_different_context_after_different_histories -v`
Expected: pass with the current rolling-memory design or after a focused correction.

- [ ] **Step 5: Write visual persistence test**

Update two controllers for 30 steps of `1/30` second with the two contexts. Assert their scales/deformations differ and that one subsequent update changes values continuously rather than jumping directly to targets.

- [ ] **Step 6: Run the contextual test module**

Run: `.venv/bin/python -m unittest tests.test_contextual_pipeline -v`
Expected: all contextual tests pass.

- [ ] **Step 7: Commit contextual proof**

```bash
git add tests/test_contextual_pipeline.py audio/analyzer.py memory/musical_memory.py state/visual_state.py
git commit -m "test: prove contextual visual response"
```

### Task 3: Stabilize Renderer and Debug Output

**Files:**
- Modify: `renderer/renderer.py`
- Modify: `main.py`
- Modify: `tests/test_renderer.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: `Renderer.draw(vertices, debug_lines)`
- Produces: display initialization without mixer dependency and terminal debug fallback when font is unavailable

- [ ] **Step 1: Write renderer initialization test**

Patch `pygame.display.init`, `pygame.display.set_mode`, and unavailable font behavior. Assert construction does not call `pygame.init`, still creates the display, and enables terminal debug fallback.

- [ ] **Step 2: Run the renderer test to verify failure**

Run: `.venv/bin/python -m unittest tests.test_renderer -v`
Expected: fail because current code calls `pygame.init()` and suppresses terminal output when a display exists without a font.

- [ ] **Step 3: Implement selective initialization and fallback**

Use `pygame.display.init()` instead of `pygame.init()`. Attempt font initialization separately; when unavailable, render the shape normally and print throttled debug text to the terminal.

- [ ] **Step 4: Extend HUD assertions**

Assert `_build_debug_lines` contains instant energy, rolling average/trend/activity/tension, and visual state without accessing private backend fields.

- [ ] **Step 5: Run renderer and main tests**

Run: `.venv/bin/python -m unittest tests.test_renderer tests.test_main -v`
Expected: all pass.

- [ ] **Step 6: Commit renderer stability**

```bash
git add renderer/renderer.py main.py tests/test_renderer.py tests/test_main.py
git commit -m "fix: keep debug visible without pygame audio modules"
```

### Task 4: Remove Residue, Document, and Verify Linux

**Files:**
- Delete: `audio/timbre.py`
- Modify: `README.md`
- Modify: `.gitignore` only if flattened paths require it

**Interfaces:**
- Consumes: stable tested pipeline
- Produces: clean repository and reproducible Linux instructions

- [ ] **Step 1: Confirm dead code and remove it**

Run: `rg -n "TimbreProfile|audio\.timbre|from .*timbre" --glob '*.py'`
Expected: only `audio/timbre.py`; remove that tracked file.

- [ ] **Step 2: Update concise Linux instructions**

Document creation of one `.venv`, editable installation, exact-case paths, `.venv/bin/python main.py ~/Videos/Youtube/cidade.wav`, console debug fallback, and the existing `vmmc` entry point.

- [ ] **Step 3: Run full automated verification**

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q audio geometry memory renderer state main.py
.venv/bin/python -m pip check
git diff --check
```

Expected: all tests pass, compilation is silent, dependencies are consistent, and no whitespace errors exist.

- [ ] **Step 4: Run real-device smoke test**

Run: `timeout 12s .venv/bin/python main.py /home/russophone/Videos/Youtube/cidade.wav`
Expected: window opens, audio is audible, shape moves, and debug is visible in the HUD or terminal.

- [ ] **Step 5: Commit cleanup and documentation**

```bash
git add -A
git commit -m "chore: finish minimal VMMC stabilization"
```
