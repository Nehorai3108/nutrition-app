"""
FoodMatchResult model — result of food catalog matching.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .enums import ConfidenceLevel


@dataclass
class FoodMatch:
    query: str
    food_id: Optional[str] = None
    food_name: Optional[str] = None
    confidence_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    matched_by: str = ""  # "exact", "alias", "fuzzy", "custom"

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "food_id": self.food_id,
            "food_name": self.food_name,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "matched_by": self.matched_by,
        }


@dataclass
class FoodMatchResult:
    matches: List[FoodMatch] = field(default_factory=list)
    unmatched: List[str] = field(default_factory=list)
    low_confidence: List[FoodMatch] = field(default_factory=list)

    @property
    def all_high_confidence(self) -> bool:
        return len(self.unmatched) == 0 and len(self.low_confidence) == 0

    @property
    def requires_decision(self) -> bool:
        return len(self.unmatched) > 0 or len(self.low_confidence) > 0

    def to_dict(self) -> dict:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "unmatched": self.unmatched,
            "low_confidence": [m.to_dict() for m in self.low_confidence],
            "all_high_confidence": self.all_high_confidence,
            "requires_decision": self.requires_decision,
        }
