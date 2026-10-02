"""EST-001 painting scope vocabulary, v1. Declarations only, not extracted takeoff facts.

No plan reading, quantity, production, pricing, or validation against real work occurs here.
Identifiers are stable within this version; change the version before changing their meaning.
"""

from dataclasses import dataclass

TAXONOMY_VERSION = "painting-takeoff/v1"
SCOPE_CATEGORIES = (
    "walls", "ceilings", "doors", "trim", "cabinets", "exterior",
)
FINISH_TYPES = ("paint", "stain", "clear_coat")
SHEENS = ("flat", "matte", "eggshell", "satin", "semi_gloss", "gloss")


def _require_identifier(value: str, allowed: tuple[str, ...], field: str) -> None:
    if type(value) is not str or value not in allowed:
        raise ValueError(f"unsupported {field}")


@dataclass(frozen=True)
class FinishRequirement:
    """Declared finish intent only; sheen=None means unspecified, not inferred."""

    finish_type: str
    sheen: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.finish_type, FINISH_TYPES, "finish type")
        if self.sheen is not None:
            _require_identifier(self.sheen, SHEENS, "sheen")


@dataclass(frozen=True)
class PaintingScope:
    """A category and optional declared finish; no area, count, cost or source claim."""

    category: str
    finish: FinishRequirement | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.category, SCOPE_CATEGORIES, "scope category")
        if self.finish is not None and type(self.finish) is not FinishRequirement:
            raise ValueError("finish must be a FinishRequirement or None")
