"""Citation validator. Guards against hallucination in research outputs."""
import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[str]
    citation_count: int
    claim_count: int


# Expected citation format: [p.45] or [Annual Report 2023, p.12]
CITATION_PATTERN = re.compile(r"\[([^\]]+(?:p\.|page)\s*\d+[^\]]*)\]", re.IGNORECASE)

# Heuristics to detect claims — sentences with numbers, percentages, or specific assertions
CLAIM_INDICATORS = [
    r"\d+\.?\d*\s*%",
    r"\$\s*\d+",
    r"Rp\s*\d+",
    r"\d+\s*(juta|miliar|triliun|million|billion)",
    r"increased|decreased|grew|declined|meningkat|menurun|tumbuh",
]
CLAIM_RE = re.compile("|".join(CLAIM_INDICATORS), re.IGNORECASE)


def validate_citations(text: str, min_citation_ratio: float = 0.5) -> ValidationResult:
    """
    Check whether the output has sufficient citations.

    Heuristic: count sentences containing numbers or claims, then check whether
    they have a citation in the same or adjacent sentence.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    issues: list[str] = []
    claim_count = 0
    cited_claim_count = 0

    for i, sentence in enumerate(sentences):
        if CLAIM_RE.search(sentence):
            claim_count += 1
            window = sentence + (sentences[i + 1] if i + 1 < len(sentences) else "")
            if CITATION_PATTERN.search(window):
                cited_claim_count += 1
            else:
                issues.append(f"Uncited claim: '{sentence[:80]}...'")

    citation_count = len(CITATION_PATTERN.findall(text))
    ratio = cited_claim_count / claim_count if claim_count > 0 else 1.0
    is_valid = ratio >= min_citation_ratio

    if not is_valid:
        issues.insert(
            0,
            f"Citation ratio {ratio:.0%} below threshold {min_citation_ratio:.0%}",
        )

    return ValidationResult(
        is_valid=is_valid,
        issues=issues,
        citation_count=citation_count,
        claim_count=claim_count,
    )
