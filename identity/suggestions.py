"""TIME-002: conservative, pure in-memory identity *suggestions*, never mappings.

Labels are evidence only. A caller must not treat any outcome as a confirmed
identity; this module does not mutate its inputs or store review decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

NAMESPACES = frozenset({"employee", "job"})
_LABEL = re.compile(r"[A-Za-z0-9]+(?:[ \t]+[A-Za-z0-9]+)*\Z")


def normalize(label: str) -> str:
    """Case/ASCII horizontal-spacing normalization; reject punctuation and Unicode lookalikes."""
    if type(label) is not str or not _LABEL.fullmatch(label.strip(" \t")):
        raise ValueError("label must contain ASCII words separated by spaces or tabs")
    return " ".join(label.lower().split())


@dataclass(frozen=True)
class IdentityLabel:
    namespace: str
    reference: str  # caller-owned source locator, not a resolved identity
    label: str

    def __post_init__(self) -> None:
        if type(self.namespace) is not str or self.namespace not in NAMESPACES:
            raise ValueError("unknown identity namespace")
        if type(self.reference) is not str or not self.reference.strip() or self.reference != self.reference.strip():
            raise ValueError("reference must be a nonempty trimmed string")
        normalize(self.label)


@dataclass(frozen=True)
class CandidateSuggestion:
    reference: str
    label: str
    normalized_label: str
    reason: str  # normalized_equal or single_typo; neither is confirmation


@dataclass(frozen=True)
class SuggestionResult:
    namespace: str
    source_reference: str
    normalized_source: str
    state: str  # needs_review or no_suggestion; never confirmed
    reason: str  # stable classification
    candidates: tuple[CandidateSuggestion, ...]


def _one_edit(a: str, b: str) -> bool:
    """Exactly one insertion/deletion/substitution or adjacent swap."""
    if a == b:
        return False
    if len(a) == len(b):
        differences = [i for i in range(len(a)) if a[i] != b[i]]
        return len(differences) == 1 or (
            len(differences) == 2 and differences[1] == differences[0] + 1
            and a[differences[0]] == b[differences[1]]
            and a[differences[1]] == b[differences[0]]
        )
    if abs(len(a) - len(b)) != 1:
        return False
    shorter, longer = sorted((a, b), key=len)
    for i in range(len(longer)):
        if longer[:i] + longer[i + 1:] == shorter:
            return True
    return False


def _likely_typo(source: str, target: str) -> bool:
    left, right = source.split(), target.split()
    if len(left) != len(right) or len(left) < 2:
        return False
    differences = [(a, b) for a, b in zip(left, right) if a != b]
    if len(differences) != 1:
        return False
    a, b = differences[0]
    # Require another whole matching word and a long alphabetic word with the
    # same first character. Never fuzzy-match job numbers or short names.
    return (a.isalpha() and b.isalpha() and min(len(a), len(b)) >= 5
            and a[0] == b[0] and _one_edit(a, b))


def suggest(source: IdentityLabel, candidates: tuple[IdentityLabel, ...]) -> SuggestionResult:
    """Return ranked review evidence; exact collisions and ties stay ambiguous.

    All inputs are checked before matching. Cross-namespace labels are ignored,
    even if their references and spellings coincide. Duplicate references or
    normalized labels within the requested namespace fail closed.
    """
    if type(source) is not IdentityLabel or type(candidates) is not tuple or any(
        type(candidate) is not IdentityLabel for candidate in candidates
    ):
        raise ValueError("source and tuple of candidates must be IdentityLabel values")
    normalized = normalize(source.label)
    relevant = [c for c in candidates if c.namespace == source.namespace]
    references = [c.reference for c in relevant]
    if len(references) != len(set(references)) or source.reference in references:
        raise ValueError("duplicate candidate reference or source included as candidate")
    result = lambda state, reason, matches=(): SuggestionResult(
        source.namespace, source.reference, normalized, state, reason, tuple(matches)
    )
    if len(normalized.split()) < 2:
        return result("no_suggestion", "insufficient_label")
    exact = [c for c in relevant if normalize(c.label) == normalized]
    if len(exact) > 1:
        # Even capitalization/spacing-only duplicates must not choose a winner.
        return result("needs_review", "normalized_collision", _matches(exact, "normalized_equal"))
    if exact:
        return result("needs_review", "normalized_equal", _matches(exact, "normalized_equal"))
    fuzzy = [c for c in relevant if _likely_typo(normalized, normalize(c.label))]
    if len(fuzzy) > 1:
        return result("needs_review", "ambiguous_typo", _matches(fuzzy, "single_typo"))
    if fuzzy:
        return result("needs_review", "single_typo", _matches(fuzzy, "single_typo"))
    return result("no_suggestion", "no_supported_match")


def _matches(candidates: list[IdentityLabel], reason: str) -> tuple[CandidateSuggestion, ...]:
    return tuple(CandidateSuggestion(c.reference, c.label, normalize(c.label), reason)
                 for c in sorted(candidates, key=lambda c: c.reference))
