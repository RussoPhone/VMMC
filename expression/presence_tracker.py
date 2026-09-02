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

    def update(self, context) -> tuple[PresenceEvidence, ...]:
        timestamp = float(context.timestamp)
        if self._cycle_index != context.cycle_index:
            self._cycle_index = context.cycle_index
            self._presences.clear()

        match = self._nearest(context.signature)
        if match is None:
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
            )
            self._next_identifier += 1
            self._presences.append(match)
        else:
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

        for presence in self._presences:
            if presence is match:
                continue
            if presence.absent_since is None:
                presence.absent_since = timestamp
            absence = timestamp - presence.absent_since
            presence.visibility *= 0.985
            if absence > 1.5 and presence.stage is PresenceStage.CONFIRMED:
                presence.stage = PresenceStage.DORMANT

        return tuple(self._snapshot(item, timestamp) for item in self._presences)

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
        )
