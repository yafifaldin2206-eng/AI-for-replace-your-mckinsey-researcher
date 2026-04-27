"""
Industry Overview workflow.

Produces a McKinsey-style industry primer: market sizing, structure,
value chain, dynamics, regulatory context, and outlook.

Best for: new sector entry, investor briefings, board presentations.

Usage:
    result = await run("Indonesian digital payments industry 2025")
    result = await run("Southeast Asia longevity biotech")
"""
import structlog
from typing import Callable, Optional, Awaitable

from app.data.search import search_company_context
from app.llm.client import complete
from app.llm.validators import validate_citations

logger = structlog.get_logger()

ProgressCallback = Callable[[str, int, Optional[dict]], Awaitable[None]]

INDUSTRY_SYSTEM = """You are a McKinsey senior partner writing an industry primer for a partner meeting.

Structure your output exactly as:

## Industry Definition & Scope
What is in and out of scope. Why the boundary matters.

## Market Sizing
- TAM, SAM, SOM with methodology note
- Growth rate (CAGR)
- Geographic breakdown if relevant

## Value Chain
Map the key stages from input to end customer. Who makes money at each stage? What are typical margins?

## Industry Structure
- Number and type of players (fragmented/concentrated)
- Key player categories with examples
- Barriers to entry
- Switching costs

## Key Dynamics
Top 3-5 forces shaping the industry right now — not generic Porter's Five Forces, but specific current dynamics.

## Regulatory Environment
- Key regulations and regulators
- Pending changes
- Licensing requirements

## Outlook (2-3 years)
- Bull case
- Base case
- Bear case
- Key uncertainties

## What Smart Operators Know (That Outsiders Miss)
2-3 non-obvious insights about how this industry actually works.

CITATION RULES: Every number and specific claim must have [Source: URL]. Use "not publicly available" if unknown. Never round numbers suspiciously."""

INDUSTRY_USER = """Industry to analyze: {target}

Research data:
---
{research_data}
---

Generate industry primer."""


async def _noop(step: str, pct: int, detail: Optional[dict] = None) -> None:
    pass


async def run(target: str, progress: ProgressCallback = _noop) -> dict:
    """
    Generate an industry overview primer.

    Args:
        target: Industry description, e.g., "Indonesian digital payments 2025"
    """
    await progress("scoping", 10, {"message": f"Researching industry: {target}..."})

    results_overview = await search_company_context(target, max_results=6)
    results_stats = await search_company_context(f"{target} market size statistics report", max_results=4)
    results_reg = await search_company_context(f"{target} regulation regulator license", max_results=3)

    all_results = {r["url"]: r for r in results_overview + results_stats + results_reg}.values()
    research_data = "\n\n---\n\n".join(
        f"Source: {r['url']}\nTitle: {r['title']}\n\n{r['text'][:2500]}"
        for r in list(all_results)[:12]
    )

    await progress("analyzing", 55, {"message": "Building industry primer..."})

    analysis = await complete(
        system=INDUSTRY_SYSTEM,
        user=INDUSTRY_USER.format(target=target, research_data=research_data),
        max_tokens=7000,
        temperature=0.3,
    )

    await progress("validating", 90, None)
    validation = validate_citations(analysis, min_citation_ratio=0.3)

    await progress("done", 100, {"valid": validation.is_valid})

    return {
        "analysis": analysis,
        "target": target,
        "validation": {
            "is_valid": validation.is_valid,
            "citation_count": validation.citation_count,
            "issues": validation.issues[:5],
        },
        "sources": [r["url"] for r in all_results],
    }
