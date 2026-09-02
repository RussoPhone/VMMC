import unittest
from types import SimpleNamespace

from expression.presence_tracker import PresenceStage, PresenceTracker
from memory.musical_memory import SoundSignature
from memory.musical_memory import CyclePhase


class PresenceTrackerTests(unittest.TestCase):
    def test_brief_signature_becomes_confirmed_when_it_returns(self):
        tracker = PresenceTracker(return_gap_seconds=0.5)

        first = tracker.update(self._context(0.0, brightness=0.2, prominence=0.45))
        tracker.update(self._context(0.2, brightness=0.85, prominence=0.2))
        returned = tracker.update(
            self._context(0.8, brightness=0.21, prominence=0.5)
        )

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].stage, PresenceStage.SEED)
        original = next(item for item in returned if item.identifier == first[0].identifier)
        self.assertEqual(original.stage, PresenceStage.CONFIRMED)
        self.assertEqual(original.recurrences, 1)

    def test_exceptional_brief_event_can_appear_immediately(self):
        tracker = PresenceTracker(exceptional_prominence=0.8)

        presences = tracker.update(self._context(0.0, prominence=0.95))

        self.assertEqual(presences[0].stage, PresenceStage.EPHEMERAL)
        self.assertGreater(presences[0].visibility, 0.5)

    def test_uncertain_stream_does_not_create_a_presence_each_frame(self):
        tracker = PresenceTracker()
        for index in range(120):
            presences = tracker.update(
                self._context(index / 30.0, brightness=0.4 + index * 0.0001)
            )

        self.assertEqual(len(presences), 1)

    def test_absence_decay_depends_on_music_time_not_frame_count(self):
        slow = self._visibility_after_absence(10)
        fast = self._visibility_after_absence(100)

        self.assertAlmostEqual(slow, fast, places=2)

    def test_unconfirmed_seed_expires_after_prolonged_absence(self):
        tracker = PresenceTracker()
        seed = tracker.update(self._context(0.0, brightness=.1))[0]
        for index in range(1, 301):
            remaining = tracker.update(self._context(index/30, brightness=.9))

        self.assertNotIn(seed.identifier, {item.identifier for item in remaining})

    def test_contextual_silence_never_germinates_a_presence(self):
        tracker = PresenceTracker()
        context = self._context(0.0)
        context.energy = 0.0
        context.cycle_phase = CyclePhase.QUIETING

        self.assertEqual(tracker.update(context), ())

    def _visibility_after_absence(self, fps):
        tracker = PresenceTracker()
        original = tracker.update(self._context(0.0, brightness=.1))[0]
        result = ()
        for index in range(1, fps + 1):
            result = tracker.update(self._context(index/fps, brightness=.9))
        return next(item.visibility for item in result if item.identifier == original.identifier)

    @staticmethod
    def _context(timestamp, brightness=0.4, prominence=0.4):
        return SimpleNamespace(
            timestamp=timestamp,
            signature=SoundSignature(brightness, 0.2, 0.8, 0.3, 0.5),
            prominence=prominence,
            signature_continuity=0.7,
            cycle_index=0,
            energy=.4,
            cycle_phase=CyclePhase.LISTENING,
        )


if __name__ == "__main__":
    unittest.main()
