"""AFCE-aligned span models for empathy opportunities, elicitations, responses, and SPIKES stages."""

from dataclasses import dataclass, asdict
from typing import Optional, Literal


# AFCE dimension types
DimensionType = Literal["Feeling", "Judgment", "Appreciation"]

# Explicit/implicit variants
ExplicitImplicit = Literal["explicit", "implicit"]

# Elicitation types
ElicitationType = Literal["direct", "indirect"]

# Response types (AFCE taxonomy)
ResponseType = Literal["understanding", "sharing", "acceptance"]

# Provenance types
ProvenanceType = Literal["rule", "ml", "llm"]

# SPIKES stage types
SPIKESStageType = Literal["setting", "perception", "invitation", "knowledge", "empathy", "summary"]

# Relation types
RelationType = Literal["elicits", "responds_to", "missed"]


@dataclass
class EmpathyOpportunitySpan:
    """Empathy opportunity span with AFCE dimension."""
    
    dimension: DimensionType
    explicit_or_implicit: ExplicitImplicit
    start_char: int
    end_char: int
    text: str
    confidence: float  # 0.0-1.0
    provenance: ProvenanceType = "rule"
    
    def to_dict(self) -> dict:
        """Convert span to dictionary."""
        return asdict(self)


@dataclass
class ElicitationSpan:
    """Elicitation span with AFCE dimension."""
    
    type: ElicitationType  # direct or indirect
    dimension: DimensionType
    start_char: int
    end_char: int
    text: str
    confidence: float  # 0.0-1.0
    provenance: ProvenanceType = "rule"
    
    def to_dict(self) -> dict:
        """Convert span to dictionary."""
        return asdict(self)


@dataclass
class ResponseSpan:
    """Empathic response span (AFCE taxonomy)."""
    
    type: ResponseType  # understanding, sharing, or acceptance
    start_char: int
    end_char: int
    text: str
    confidence: float  # 0.0-1.0
    provenance: ProvenanceType = "rule"
    
    def to_dict(self) -> dict:
        """Convert span to dictionary."""
        return asdict(self)


@dataclass
class SPIKESStageSpan:
    """SPIKES stage span (for future use)."""
    
    stage: SPIKESStageType
    start_char: int
    end_char: int
    text: str
    confidence: float  # 0.0-1.0
    provenance: ProvenanceType = "rule"
    
    def to_dict(self) -> dict:
        """Convert span to dictionary."""
        return asdict(self)


@dataclass
class Relation:
    """Span relation (for future use in Part 2)."""
    
    source_span_id: str  # ID referencing a span
    target_span_id: str  # ID referencing another span
    relation_type: RelationType  # elicits, responds_to, or missed
    confidence: float  # 0.0-1.0
    
    def to_dict(self) -> dict:
        """Convert relation to dictionary."""
        return asdict(self)

