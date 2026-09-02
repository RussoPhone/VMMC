"""Persistent, probabilistic musical presences derived from contextual signatures."""

from dataclasses import dataclass
from enum import Enum
import math
from statistics import fmean

from memory.musical_memory import SoundSignature


class PresenceStage(Enum):
    SEED = "seed"
    EPHEMERAL = "ephemeral"
    CONFIRMED = "confirmed"
    DORMANT = "dormant"


@dataclass(frozen=True)
class PresenceEvidence:
    identifier: int
    signature: SoundSignature
    stage: PresenceStage
    visibility: float
    prominence: float
    recurrences: int
    age: float
    last_seen: float
    active: bool = True


@dataclass
class _TrackedPresence:
    identifier: int
    signature: SoundSignature
    stage: PresenceStage
    born_at: float
    last_seen: float
    visibility: float
    prominence: float
    recurrences: int = 0
    absent_since: float | None = None
    visibility_updated_at: float = 0.0


class PresenceTracker:
    def __init__(
        self,
        match_distance: float = 0.16,
        return_gap_seconds: float = 0.65,
        exceptional_prominence: float = 0.82,
    ):
        self.match_distance = match_distance
        self.return_gap_seconds = return_gap_seconds
        self.exceptional_prominence = exceptional_prominence
        self._cycle_index = None
        self._next_identifier = 1
        self._presences = []

    def update(self, context, timestamp=None) -> tuple[PresenceEvidence, ...]:
        timestamp = float(context.timestamp if timestamp is None else timestamp)
        if self._cycle_index != context.cycle_index:
            self._cycle_index = context.cycle_index
            self._presences.clear()

        phase = getattr(getattr(context, "cycle_phase", None), "value", "listening")
        musically_active = phase == "listening" and getattr(context, "energy", 1.0) > .01
        match = self._nearest(context.signature) if musically_active else None
        if match is None and musically_active:
            stage = (
                PresenceStage.EPHEMERAL
                if context.prominence >= self.exceptional_prominence
                else PresenceStage.SEED
            )
            match = _TrackedPresence(
                self._next_identifier,
                context.signature,
                stage,
                timestamp,
                timestamp,
                0.72 if stage is PresenceStage.EPHEMERAL else 0.18,
                context.prominence,
                visibility_updated_at=timestamp,
            )
            self._next_identifier += 1
            self._presences.append(match)
        elif match is not None:
            gap = timestamp - match.last_seen
            if gap >= self.return_gap_seconds:
                match.recurrences += 1
                match.stage = PresenceStage.CONFIRMED
            match.signature = self._blend(match.signature, context.signature, 0.18)
            match.last_seen = timestamp
            match.absent_since = None
            match.prominence += (context.prominence - match.prominence) * 0.25
            target = 0.9 if match.stage is PresenceStage.CONFIRMED else 0.35
            match.visibility += (target - match.visibility) * 0.3
            match.visibility_updated_at = timestamp

        for presence in self._presences:
            if presence is match:
                continue
            if presence.absent_since is None:
                presence.absent_since = timestamp
            absence = timestamp - presence.absent_since
            elapsed = max(0.0, timestamp - presence.visibility_updated_at)
            presence.visibility *= math.exp(-1.5 * elapsed)
            presence.visibility_updated_at = timestamp
            if absence > 1.5 and presence.stage is PresenceStage.CONFIRMED:
                presence.stage = PresenceStage.DORMANT

        self._presences = [
            presence
            for presence in self._presences
            if presence.stage in (PresenceStage.CONFIRMED, PresenceStage.DORMANT)
            or presence.absent_since is None
            or timestamp - presence.absent_since <= 5.0
        ]

        return tuple(
            self._snapshot(item, timestamp)
            for item in self._presences
            if item.visibility > 0.01
        )

    def _nearest(self, signature):
        candidates = [
            (self._distance(item.signature, signature), item)
            for item in self._presences
        ]
        if not candidates:
            return None
        distance, presence = min(candidates, key=lambda pair: pair[0])
        return presence if distance <= self.match_distance else None

    @staticmethod
    def _distance(left, right):
        return math.sqrt(
            fmean(
                (a - b) ** 2
                for a, b in zip(vars(left).values(), vars(right).values())
            )
        )

    @staticmethod
    def _blend(left, right, rate):
        return SoundSignature(
            *(a + (b - a) * rate for a, b in zip(vars(left).values(), vars(right).values()))
        )

    @staticmethod
    def _snapshot(item, timestamp):
        return PresenceEvidence(
            item.identifier,
            item.signature,
            item.stage,
            max(0.0, min(1.0, item.visibility)),
            max(0.0, min(1.0, item.prominence)),
            item.recurrences,
            timestamp - item.born_at,
            item.last_seen,
            item.absent_since is None,
        )
