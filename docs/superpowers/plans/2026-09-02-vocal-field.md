# Behavioral VocalField Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-geometric vocal influence that continuously changes existing organisms, plus overlap prevention that fades through fusion and assimilation.

**Architecture:** A stateful `VocalFieldController` converts the existing vocal context into five smoothed public channels. `EcosystemController` assigns continuous influence weights, applies behavioral movement and collision response, and exposes immutable per-organism effects and aggregate metrics; `EcosystemGeometryBuilder` combines those transient effects with each persistent genome.

**Tech Stack:** Python 3.14, standard-library dataclasses/math/unittest, existing NumPy/Pygame runtime.

**Spec:** `docs/superpowers/specs/2026-09-02-vocal-field-design.md`

## Global Constraints

- Voice creates no organism, body, particle, center, or dedicated geometry.
- All field channels and effects stay normalized and decay continuously.
- `radius` is behavioral reach, not a rendered physical radius.
- Vocal effects never mutate `VisualGenome`.
- Collision is deterministic, soft, bounded per frame, and fades continuously through fusion and assimilation.
- `main.py` coordinates public interfaces and does not access private component state.
- Every elapsed audio frame continues through all interpretive layers in order.

---

### Task 1: Smoothed VocalField

**Files:**
- Create: `expression/vocal_field.py`
- Create: `tests/test_vocal_field.py`

**Interfaces:**
- Consumes: `VocalFieldController.update(context, dt: float) -> VocalField` where context provides the existing public vocal, signature, regime, stability, tension, and prominence values.
- Produces: immutable `VocalField(intensity, radius, roughness, continuity, pressure)` with values in `[0, 1]`; `VocalField.silent()`.

- [ ] **Step 1: Write failing derivation and decay tests**

```python
import unittest
from types import SimpleNamespace

from expression.vocal_field import VocalFieldController


def context(activity, presence, *, noise=.1, attack=.1, continuity=.8,
            stability=.8, tension=.1, prominence=.3, building=.0, climax=.0):
    return SimpleNamespace(
        vocal_activity=activity,
        vocal_presence=presence,
        signature=SimpleNamespace(noisiness=noise, attack=attack),
        signature_continuity=continuity,
        stability=stability,
        tension=tension,
        prominence=prominence,
        regimes=SimpleNamespace(building=building, climax=climax),
    )


class VocalFieldTests(unittest.TestCase):
    def test_soft_continuous_voice_builds_reach_and_continuity_without_pressure(self):
        controller = VocalFieldController()
        field = None
        for _ in range(20):
            field = controller.update(context(.35, .9), .1)
        self.assertGreater(field.radius, field.intensity)
        self.assertGreater(field.continuity, field.pressure)
        self.assertLess(field.roughness, .25)

    def test_rough_intense_voice_builds_pressure_and_roughness(self):
        controller = VocalFieldController()
        field = None
        for _ in range(20):
            field = controller.update(
                context(.95, .95, noise=.9, attack=.8, tension=.85,
                        prominence=.9, building=.7, climax=.8), .1)
        self.assertGreater(field.pressure, .6)
        self.assertGreater(field.roughness, .5)

    def test_absent_voice_decays_every_channel_without_abrupt_reset(self):
        controller = VocalFieldController()
        for _ in range(20):
            active = controller.update(context(.9, .9, noise=.7, tension=.8), .1)
        first_quiet = controller.update(context(0, 0, continuity=0, stability=0), .1)
        self.assertGreater(first_quiet.intensity, 0)
        self.assertLess(first_quiet.intensity, active.intensity)
        quiet = first_quiet
        for _ in range(180):
            quiet = controller.update(context(0, 0, continuity=0, stability=0), .1)
        self.assertTrue(all(value < .02 for value in vars(quiet).values()))
```

- [ ] **Step 2: Run tests and verify the missing module is the only failure**

Run: `.venv/bin/python -m unittest tests.test_vocal_field -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'expression.vocal_field'`.

- [ ] **Step 3: Implement the minimal stateful controller**

```python
from dataclasses import dataclass


def _clamp(value):
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class VocalField:
    intensity: float = 0.0
    radius: float = 0.0
    roughness: float = 0.0
    continuity: float = 0.0
    pressure: float = 0.0

    @classmethod
    def silent(cls):
        return cls()


class VocalFieldController:
    def __init__(self):
        self._state = VocalField.silent()

    def update(self, context, dt):
        presence = _clamp(context.vocal_presence)
        activity = _clamp(context.vocal_activity)
        vocal_gate = _clamp(presence * .65 + activity * .35)
        targets = VocalField(
            intensity=_clamp(activity * .8 + presence * activity * .2),
            radius=_clamp(presence * .55 + activity * .25 + context.prominence * presence * .2),
            roughness=_clamp(vocal_gate * (context.signature.noisiness * .72 + context.signature.attack * .28)),
            continuity=_clamp(presence * (context.signature_continuity * .7 + context.stability * .3)),
            pressure=_clamp(activity * (context.tension * .55 + context.regimes.building * .2 + context.regimes.climax * .25)),
        )
        values = {}
        for name, target in vars(targets).items():
            current = getattr(self._state, name)
            rate = 5.0 if target > current else 1.15
            values[name] = current + (target - current) * min(1.0, max(0.0, dt) * rate)
        self._state = VocalField(**values)
        return self._state
```

- [ ] **Step 4: Run the focused tests**

Run: `.venv/bin/python -m unittest tests.test_vocal_field -v`

Expected: 3 tests PASS.

- [ ] **Step 5: Commit the field controller**

```bash
git add expression/vocal_field.py tests/test_vocal_field.py
git commit -m "feat: derive a continuous behavioral vocal field"
```

### Task 2: Per-organism effects and collision gradient

**Files:**
- Modify: `state/ecosystem.py`
- Modify: `tests/test_ecosystem.py`

**Interfaces:**
- Consumes: optional `vocal_field: VocalField = VocalField.silent()` in `EcosystemController.update`.
- Produces: `VocalEffect(influence, fluidity, tension, roughness)` on every `OrganismState`; `VocalEffectSummary(reached_count, mean_influence, max_influence, mean_fluidity, mean_tension, mean_roughness)` and `CollisionSummary(contact_count, max_repulsion)` on `EcosystemState`.

- [ ] **Step 1: Write failing reach, behavioral, and no-vocal-body tests**

Add tests using four existing `PresenceEvidence` values and explicit fields:

```python
from expression.vocal_field import VocalField

def test_vocal_reach_spreads_continuously_without_creating_a_body(self):
    presences = tuple(self._presence(index, index / 10) for index in range(1, 5))
    narrow = EcosystemController().update(
        presences, .1, vocal_field=VocalField(.8, .15, .2, .7, .3)
    )
    wide = EcosystemController().update(
        presences, .1, vocal_field=VocalField(.8, .95, .2, .7, .3)
    )
    self.assertEqual(len(wide.organisms), len(presences))
    self.assertGreater(wide.vocal_effect.reached_count, narrow.vocal_effect.reached_count)
    self.assertGreater(wide.vocal_effect.mean_influence, narrow.vocal_effect.mean_influence)

def test_continuous_voice_changes_motion_and_exposes_transient_effect(self):
    presence = self._presence(4, .7)
    plain = EcosystemController()
    voiced = EcosystemController()
    plain.update((presence,), .1)
    voiced.update((presence,), .1)
    plain_state = plain.update((presence,), .1)
    voiced_state = voiced.update(
        (presence,), .1, vocal_field=VocalField(.8, 1, .1, .9, .7)
    )
    self.assertGreater(voiced_state.organisms[0].vocal_effect.influence, .5)
    self.assertNotEqual(
        (voiced_state.organisms[0].velocity_x, voiced_state.organisms[0].velocity_y),
        (plain_state.organisms[0].velocity_x, plain_state.organisms[0].velocity_y),
    )
    self.assertEqual(voiced_state.organisms[0].genome, plain_state.organisms[0].genome)
```

- [ ] **Step 2: Write failing collision and assimilation-gradient tests**

Seed two controller bodies through ordinary presences, place their private physical
centres together only as deterministic test setup, and compare public snapshots:

```python
def test_unrelated_overlapping_forms_separate_softly(self):
    ecosystem = EcosystemController()
    presences = (self._presence(1, .1), self._presence(2, .9))
    ecosystem.update(presences, .1)
    ecosystem._bodies[1].x = ecosystem._bodies[2].x = .5
    ecosystem._bodies[1].y = ecosystem._bodies[2].y = 0
    state = ecosystem.update(presences, .1)
    self.assertGreater(self._distance(*state.organisms), 0)
    self.assertEqual(state.collisions.contact_count, 1)
    self.assertGreater(state.collisions.max_repulsion, 0)

def test_collision_repulsion_fades_through_assimilation(self):
    low = EcosystemController()
    high = EcosystemController()
    presences = (self._presence(1, .3), self._presence(2, .31))
    for controller in (low, high):
        controller.update(presences, .1)
        controller._bodies[1].x = controller._bodies[2].x = .5
        controller._bodies[1].y = controller._bodies[2].y = 0
    high._relations[(1, 2)] = _Relation(fusion=.9, assimilation=.85)
    low_state = low.update(presences, .1)
    high_state = high.update(presences, .1)
    self.assertLess(high_state.collisions.max_repulsion, low_state.collisions.max_repulsion)
```

- [ ] **Step 3: Run focused tests and verify missing interface failures**

Run: `.venv/bin/python -m unittest tests.test_ecosystem -v`

Expected: FAIL because `vocal_field`, effect summaries, and collision summaries do not exist.

- [ ] **Step 4: Implement immutable effect/summary state and continuous reach**

Add frozen dataclasses with zero defaults. Rank active bodies by
`(visibility * .55 + prominence * .45, -identifier)` descending. For rank position
`p = index / max(1, count - 1)`, calculate
`reach = clamp((field.radius - p + .35) / .35)` and
`influence = field.intensity * reach * body.visibility`. Smooth the stored body
effect toward targets, then use continuity to increase tangential cohesion and
pressure to add bounded outward/tangential impulse. Build aggregate metrics from
the public organism effects.

- [ ] **Step 5: Implement deterministic soft collisions after movement**

For every identifier-sorted body pair, find the public relation or a zero relation.
Use `collision_factor = (1 - assimilation) ** 2 * (1 - fusion * .45)` and
`minimum_distance = (left_radius + right_radius) * (.25 + .75 * collision_factor)`.
For penetration, derive a deterministic direction from identifiers when centres
coincide, move both bodies by at most `.04` per update, and add equal/opposite
velocity impulses. Accumulate `contact_count` and normalized `max_repulsion`.

- [ ] **Step 6: Run ecosystem tests**

Run: `.venv/bin/python -m unittest tests.test_ecosystem -v`

Expected: all ecosystem tests PASS, including existing fusion/divergence behavior.

- [ ] **Step 7: Commit physical behavior**

```bash
git add state/ecosystem.py tests/test_ecosystem.py
git commit -m "feat: let voice influence non-overlapping organisms"
```

### Task 3: Transient vocal morphology in ecosystem geometry

**Files:**
- Modify: `geometry/ecosystem_geometry.py`
- Modify: `tests/test_ecosystem_geometry.py`

**Interfaces:**
- Consumes: `OrganismState.vocal_effect`.
- Produces: vertices whose animation and surface combine genome identity with transient vocal fluidity, tension, and roughness.

- [ ] **Step 1: Write failing geometry-effect tests**

```python
from state.ecosystem import VocalEffect

def test_vocal_roughness_and_tension_deform_without_changing_genome(self):
    genome = VisualGenome(.4,.4,.1,.05,.5,.7,.5,.55,.5,.6)
    calm = EcosystemState((OrganismState(1,.4,0,1,.8,genome),), (), .5)
    vocal = EcosystemState((OrganismState(
        1,.4,0,1,.8,genome,vocal_effect=VocalEffect(1,.2,.9,.9)
    ),), (), .5)
    builder = EcosystemGeometryBuilder(vertex_count=48)
    calm_body = builder.build(calm, .7).organisms[0]
    vocal_body = builder.build(vocal, .7).organisms[0]
    calm_span = max(math.dist((.4, 0), point) for point in calm_body.vertices) - min(math.dist((.4, 0), point) for point in calm_body.vertices)
    vocal_span = max(math.dist((.4, 0), point) for point in vocal_body.vertices) - min(math.dist((.4, 0), point) for point in vocal_body.vertices)
    self.assertGreater(vocal_span, calm_span)
    self.assertEqual(vocal.organisms[0].genome, genome)
```

- [ ] **Step 2: Run focused tests and verify the effect is absent**

Run: `.venv/bin/python -m unittest tests.test_ecosystem_geometry -v`

Expected: FAIL because `VocalEffect`/`vocal_effect` are not yet consumed by geometry.

- [ ] **Step 3: Combine effects locally in `_organism`**

Keep genome values untouched. Calculate local effective channels:

```python
effect = body.vocal_effect
fluidity = clamp(genome.fluidity + effect.fluidity * .35)
roughness = clamp(genome.roughness + effect.roughness * .45)
tension = effect.tension
```

Use `fluidity` in temporal wave/lobe rates, `roughness` in the rough surface and
mutation terms, and a bounded tension harmonic in radius/stretch. Do not alter
color, lineage, organism count, or connection generation.

- [ ] **Step 4: Run focused geometry and ecosystem tests**

Run: `.venv/bin/python -m unittest tests.test_ecosystem_geometry tests.test_ecosystem -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit geometry expression**

```bash
git add geometry/ecosystem_geometry.py tests/test_ecosystem_geometry.py
git commit -m "feat: express vocal behavior through organism surfaces"
```

### Task 4: Pipeline coordination and causal debug

**Files:**
- Modify: `main.py`
- Modify: `tests/test_expressive_pipeline.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: optional `vocal_field_controller` in `drain_expressive_frames` and public field/effect/collision state.
- Produces: `ExpressiveFrame.vocal_field`; debug lines `VOCAL FEATURES`, `VOCAL FIELD`, `VOCAL EFFECT`, and `COLLISION`.

- [ ] **Step 1: Write failing pipeline-order test**

Extend `test_optional_ecology_receives_every_interpreted_frame` with a real recording
double whose `update(context, dt)` appends `("vocal_field", context.index)` and
returns `field-{index}`. Require the order per frame to be:

```python
audio -> memory -> gesture -> morphology -> vocal_field -> presence -> ecosystem
```

Require the ecosystem recording double to receive `vocal_field`, and assert
`result.vocal_field == "field-1"`.

- [ ] **Step 2: Write failing causal debug test**

Extend the debug fixture with instantaneous `features.vocal_evidence` and
`features.vocal_intensity`, a concrete `VocalField`, organism vocal effects,
`VocalEffectSummary`, and `CollisionSummary`. Assert the joined output includes:

```text
VOCAL FEATURES evidence=...
VOCAL FIELD intensity=... radius=... roughness=... continuity=... pressure=...
VOCAL EFFECT reached=... mean=... max=... fluidity=... tension=... roughness=...
COLLISION contacts=... repulsion=...
```

- [ ] **Step 3: Run focused tests and verify missing plumbing failures**

Run: `.venv/bin/python -m unittest tests.test_expressive_pipeline tests.test_main -v`

Expected: FAIL because `ExpressiveFrame` and the coordinator/debug interfaces lack the field.

- [ ] **Step 4: Wire the public field through `main.py`**

Import and instantiate `VocalFieldController`. After morphology and before presence
tracking, call `vocal_field_controller.update(context, dt)`, pass its result to
`ecosystem_controller.update(..., vocal_field=vocal_field)`, and store it on
`ExpressiveFrame`. Recreate the controller on file change. When no controller is
provided to compatibility helpers, use `VocalField.silent()` without changing the
existing five-stage call order.

- [ ] **Step 5: Build debug solely from public frame data**

Add `vocal_field=None` to `_build_debug_lines`; label raw feature values separately
from smoothed context and field values. Read effect/collision aggregates only from
`EcosystemState`, using zero-compatible `getattr` fallbacks for tests and startup.

- [ ] **Step 6: Run focused integration tests**

Run: `.venv/bin/python -m unittest tests.test_expressive_pipeline tests.test_main -v`

Expected: all tests PASS.

- [ ] **Step 7: Run full verification**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: all tests PASS with zero failures/errors.

Run: `.venv/bin/python -m compileall -q audio expression geometry memory renderer state main.py`

Expected: exit code 0 and no output.

Run: `git diff --check`

Expected: exit code 0 and no output.

- [ ] **Step 8: Commit pipeline and debug**

```bash
git add main.py tests/test_expressive_pipeline.py tests/test_main.py
git commit -m "feat: expose vocal field cause and effect"
```

- [ ] **Step 9: Perform the visual hypothesis check**

Run:

```bash
.venv/bin/python main.py "/home/russophone/Videos/Youtube/A Cidade [WVT1XskxUZk].mp3"
```

Observe vocal entrances, sustained passages, rough passages, and gaps. Confirm that
existing organisms change together with the three vocal debug stages, no dedicated
voice body appears, unrelated bodies avoid overlap, and merging bodies cross their
collision boundary gradually.

