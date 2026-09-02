# Vocal Waves Laboratory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `vmmc-vocal`, a conservative voice-only visualization laboratory.

**Architecture:** Reuse audio analysis and musical memory, then pass context through a hysteretic `VocalGate`. A dedicated renderer draws waveform, harmonics, vocal-band spectrum, histories, and parameters; no instrumental ecosystem components are instantiated.

**Tech Stack:** Python, NumPy, Pygame, unittest.

**Spec:** `docs/superpowers/specs/2026-09-02-vocal-waves-lab-design.md`

## Global Constraints

- No instrumental presence, morphology, ecosystem, or geometry pipeline.
- Rejected background produces diagnostics only.
- Gate opening is conservative and closing is smooth.
- File and `--system-audio` inputs remain supported.

### Task 1: Conservative vocal gate

**Files:** create `expression/vocal_gate.py`, `tests/test_vocal_gate.py`.

**Interface:** `VocalGate.update(features, context, dt) -> VocalGateState`, exposing `open_amount`, `confidence`, `confirmed`, and `rejected_background`.

- [ ] Write tests proving sustained strong voice opens only after confirmation, isolated harmonic/instrument-like evidence stays rejected, and absence decays rather than resets.
- [ ] Run `.venv/bin/python -m unittest tests.test_vocal_gate -v` and observe the missing-module failure.
- [ ] Implement bounded scores, hysteresis, confirmation time, and exponential-style smoothing.
- [ ] Run the focused tests and commit.

### Task 2: Exclusive vocal pipeline

**Files:** create `vocal_main.py`, modify `pyproject.toml`, create `tests/test_vocal_main.py`.

**Interfaces:** `drain_vocal_frames(audio, analyzer, memory, gate, previous_timestamp=None) -> VocalFrame`; console entry point `vmmc-vocal = "vocal_main:cli"`.

- [ ] Write tests proving every frame crosses audio → memory → gate in order, and no ecosystem/morphology object is part of `VocalFrame`.
- [ ] Run the focused tests and observe missing-interface failures.
- [ ] Implement the minimal coordinator using `AudioInput`/`SystemAudioInput`, `AudioAnalyzer`, and `MusicalMemory` only.
- [ ] Run the focused tests and commit.

### Task 3: Lines, waves, parameters, and graphs

**Files:** create `renderer/vocal_renderer.py`, `tests/test_vocal_renderer.py`; modify `vocal_main.py`.

**Interface:** `VocalRenderer.draw(frame)` keeps bounded histories and renders only when `open_amount > 0`, while always showing gate diagnostics when fonts work.

- [ ] Write headless tests proving rejected background adds no expressive waveform, accepted voice adds waveform/history samples, and histories remain bounded.
- [ ] Run the focused tests and observe missing-renderer failures.
- [ ] Implement Pygame drawing for main waveform, harmonic lines, vocal-band spectrum, five histories, and numeric gate/field values.
- [ ] Wire events, playback lifecycle, reset-on-file-change, and smooth visual decay.
- [ ] Run focused tests and commit.

### Task 4: Verification and smoke test

- [ ] Run `.venv/bin/python -m unittest discover -s tests -v`.
- [ ] Run `.venv/bin/python -m compileall -q audio expression memory renderer vocal_main.py`.
- [ ] Run `git diff --check`.
- [ ] Launch `vocal_main.py` with “A Cidade” and compare vocal versus instrumental passages.
