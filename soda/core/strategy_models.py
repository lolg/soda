"""Strategy models — types for decision graph, classification, and results.

Pure data: no LLM, no I/O beyond loading YAML.
The graph walker lives in strategy.py. Classification logic lives in classify.py.
"""

from __future__ import annotations

import enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────


class Classification(str, enum.Enum):
    MIXED = "MIXED"
    UNDER_ONLY = "UNDER_ONLY"
    OVER_ONLY = "OVER_ONLY"
    WELL_SERVED = "WELL_SERVED"


class Answer(str, enum.Enum):
    YES = "yes"
    NO = "no"
    UNCERTAIN = "uncertain"

    @classmethod
    def from_input(cls, raw: str) -> Answer:
        """Parse CLI input to Answer."""
        raw = raw.strip().lower()
        if raw in ("y", "yes"):
            return cls.YES
        elif raw in ("n", "no"):
            return cls.NO
        return cls.UNCERTAIN


# ─────────────────────────────────────────────
# Graph node models
# ─────────────────────────────────────────────


class AllocationMap(BaseModel):
    """Per-zone investment recommendation from a strategy terminal."""
    underserved: str
    overserved: str
    table_stakes: str
    appropriate: str


class AskNode(BaseModel):
    """LLM formulates a contextual question, human answers via CLI."""
    type: Literal["ask"]
    gate_intent: str
    purpose: str
    context_from: list[str]
    on_yes: str
    on_no: str
    on_uncertain: str

    def follow(self, answer: Answer) -> str:
        """Return the next node ID for a given answer."""
        if answer == Answer.YES:
            return self.on_yes
        elif answer == Answer.NO:
            return self.on_no
        return self.on_uncertain


class StrategyNode(BaseModel):
    """Terminal — resolved strategy recommendation."""
    type: Literal["strategy"]
    label: str | None = None
    classification: str
    allocation: AllocationMap
    pricing_direction: str
    stop_doing: str | None = None
    note: str | None = None
    trajectory: str | None = None
    open_dependencies: list[str] | None = None


# Union for the walker to dispatch on
GraphNode = AskNode | StrategyNode


# ─────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────


class Thresholds(BaseModel):
    """Loaded from the thresholds section of the decision graph YAML."""
    meaningful_underserved_breadth: float = 15.0
    meaningful_underserved_intensity: float = 15.0
    meaningful_overserved_breadth: float = 20.0
    weight_dominance_ratio: float = 3.0
    high_opportunity: float = 15.0
    improvement_bar: float = 20.0


# ─────────────────────────────────────────────
# Decision graph container
# ─────────────────────────────────────────────


def _parse_node(node_id: str, data: dict[str, Any]) -> GraphNode:
    """Parse a YAML node dict into the appropriate typed model."""
    node_type = data.get("type")
    if node_type == "ask":
        return AskNode.model_validate(data)
    elif node_type == "strategy":
        return StrategyNode.model_validate(data)
    raise ValueError(f"Unknown node type '{node_type}' for node '{node_id}'")


class DecisionGraph(BaseModel):
    """The full parsed and validated decision graph."""
    thresholds: Thresholds
    entry_points: dict[str, str]  # Classification value → starting node ID
    nodes: dict[str, GraphNode]

    @classmethod
    def from_file(cls, path: str | Path) -> DecisionGraph:
        with open(path) as f:
            raw = yaml.safe_load(f)

        thresholds = Thresholds.model_validate(raw.get("thresholds", {}))
        entry_points = raw.get("entry_points", {})

        nodes: dict[str, GraphNode] = {}
        for node_id, node_data in raw.get("nodes", {}).items():
            nodes[node_id] = _parse_node(node_id, node_data)

        graph = cls(thresholds=thresholds, entry_points=entry_points, nodes=nodes)
        graph._validate()
        return graph

    def _validate(self) -> None:
        """Check referential integrity at load time."""
        all_ids = set(self.nodes.keys())

        # All ask node targets must exist
        for node_id, node in self.nodes.items():
            if isinstance(node, AskNode):
                for target in [node.on_yes, node.on_no, node.on_uncertain]:
                    if target not in all_ids:
                        raise ValueError(
                            f"Node '{node_id}' references '{target}' which does not exist"
                        )

        # All entry points must reference existing nodes
        for cls_value, entry_id in self.entry_points.items():
            if entry_id not in all_ids:
                raise ValueError(
                    f"Entry point '{cls_value}' references '{entry_id}' which does not exist"
                )

        # At least one strategy terminal must exist
        has_terminal = any(isinstance(n, StrategyNode) for n in self.nodes.values())
        if not has_terminal:
            raise ValueError("Graph must contain at least one strategy terminal")

        # All classification values must have entry points
        for cls in Classification:
            if cls.value not in self.entry_points:
                raise ValueError(
                    f"Missing entry point for classification '{cls.value}'"
                )

    def entry_node_id(self, classification: Classification) -> str:
        """Return the starting node ID for a classification."""
        return self.entry_points[classification.value]


# ─────────────────────────────────────────────
# Business context
# ─────────────────────────────────────────────


class BusinessContext(BaseModel):
    """Loaded from business-context.yaml. Project config, not pipeline logic."""
    entity_type: str
    core_jtbd: str
    market_size: int | float | None = None
    price_anchor: str | None = None
    constraints: str | None = None
    competitive_context: str | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> BusinessContext:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


# ─────────────────────────────────────────────
# Zone signals — deterministic classification
# ─────────────────────────────────────────────


class ZoneSignals(BaseModel):
    """Computed signals for a single zone."""
    breadth: float   # % of total outcomes in this zone
    intensity: float  # max opportunity score in zone
    weight: float     # sum of opportunity scores
    count: int        # number of outcomes


class SegmentSignals(BaseModel):
    """Computed signals for all zones, plus classification result."""
    underserved: ZoneSignals
    overserved: ZoneSignals
    table_stakes: ZoneSignals
    appropriate: ZoneSignals
    classification: Classification
    weight_override_applied: bool = False


# ─────────────────────────────────────────────
# Strategy result — per-segment output
# ─────────────────────────────────────────────


class StepRecord(BaseModel):
    """One step in the graph walk — for the reasoning trail."""
    node_id: str
    node_type: Literal["ask", "strategy"]
    gate_intent: str | None = None
    question: str | None = None       # contextualized question shown to user
    answer: Answer | None = None      # user's response
    next_node_id: str | None = None   # where the walk went next


class StrategyResult(BaseModel):
    """Complete strategy output for a single segment."""
    classification: Classification
    weight_override_applied: bool
    signals: SegmentSignals

    # From the strategy terminal
    strategy_label: str | None = None
    allocation: AllocationMap | None = None
    pricing_direction: str | None = None
    stop_doing: str | None = None
    note: str | None = None
    trajectory: str | None = None
    open_dependencies: list[str] | None = None

    # Addressable market (if market_size provided in business context)
    addressable_population: float | None = None
    addressable_value: str | None = None

    # Audit trail
    terminal_node_id: str | None = None
    steps: list[StepRecord] = []
