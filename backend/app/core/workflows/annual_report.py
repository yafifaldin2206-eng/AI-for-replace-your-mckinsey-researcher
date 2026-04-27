"""
Annual Report Summarizer workflow.

Steps:
1. Find PDF URL via Exa search (if input is a company name)
2. Fetch PDF
3. Parse PDF page by page
4. Extract metadata (Step 1 prompt)
5. Identify sections (Step 2 prompt)
6. Core analysis with multi-section prompt (Step 3)
7. Validate citations
8. Return structured result
"""
import json
import re
from dataclasses import dataclass, asdict
from typing import Callable, Optional, Awaitable
import structlog

from app.data import search
from app.data.scrapers import annual_report as scraper
from app.data.parsers.pdf import parse_pdf, ParsedPDF
from app.llm import client as llm
from app.llm.validators import validate_citations
from app.core.prompts.annual_report import (
    SCOPING_SYSTEM,
    SCOPING_USER,
    CORE_ANALYSIS_SYSTEM,
    CORE_ANALYSIS_USER,
)

logger = structlog.get_logger()


@dataclass
class AnnualReportResult:
    company_metadata: dict
    executive_briefing: str
    validation: dict
    source_url: str
    page_count: int


ProgressCallback = Callable[[str, int, Optional[dict]], Awaitable[None]]


async def _noop_progress(step: str, pct: int, detail: Optional[dict] = None) -> None:
    pass


def _truncate_for_metadata(parsed: ParsedPDF, max_chars: int = 15000) -> str:
    """Take the first pages of the document to extract metadata."""
    pieces = []
    total = 0
    for page in parsed.pages[:20]:
        block = f"[p.{page.page_number}]\n{page.text}"
        if total + len(block) > max_chars:
            break
        pieces.append(block)
        total += len(block)
    return "\n\n".join(pieces)


def _smart_select_for_analysis(parsed: ParsedPDF, max_chars: int = 60000) -> str:
    """
    For short documents, send everything. For long documents, prioritize:
    - First 30 pages (letter to shareholders, overview, MD&A)
    - Sample from the middle (financial statement summaries)
    - Last 10 pages (outlook, governance)
    """
    full = parsed.full_text
    if len(full) <= max_chars:
        return full

    n = len(parsed.pages)
    selected_indices = set()

    selected_indices.update(range(min(30, n)))

    for i in range(30, n, 5):
        selected_indices.add(i)

    selected_indices.update(range(max(0, n - 10), n))

    pieces = []
    total = 0
    for i in sorted(selected_indices):
        page = parsed.pages[i]
        block = f"[p.{page.page_number}]\n{page.text}"
        if total + len(block) > max_chars:
            break
        pieces.append(block)
        total += len(block)

    return "\n\n".join(pieces)


def _extract_json(text: str) -> dict:
    """Robust JSON extraction from LLM output."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


async def run(
    target: str,
    progress: ProgressCallback = _noop_progress,
) -> AnnualReportResult:
    """
    Main entry point.
    target can be:
      - a company name (e.g., "Tokopedia")
      - a direct URL to an annual report PDF
      - a URL to an investor relations page
    """
    # Step 1: Resolve URL
    await progress("scoping", 5, {"message": f"Searching for annual report: {target}..."})

    if target.startswith("http"):
        url = target
    else:
        url = await search.find_annual_report(target)
        if not url:
            raise ValueError(f"No annual report found for: {target}")

    # Step 2: Fetch PDF
    await progress("fetching", 15, {"url": url})
    pdf_bytes = await scraper.get_annual_report_pdf(url)

    # Step 3: Parse
    await progress("parsing", 30, {"size_mb": round(len(pdf_bytes) / 1_000_000, 1)})
    parsed = parse_pdf(pdf_bytes)
    if not parsed.pages:
        raise ValueError("PDF parsing returned 0 content pages. The file may be a scanned image.")

    # Step 4: Metadata extraction
    await progress("metadata", 45, {"page_count": parsed.total_pages})
    metadata_text = await llm.complete(
        system=SCOPING_SYSTEM,
        user=SCOPING_USER.format(first_pages=_truncate_for_metadata(parsed)),
        max_tokens=1000,
        temperature=0.1,
    )
    try:
        metadata = _extract_json(metadata_text)
    except json.JSONDecodeError as e:
        logger.warning("metadata_json_parse_failed", error=str(e), raw=metadata_text[:500])
        metadata = {"raw": metadata_text, "parse_error": str(e)}

    # Step 5: Core analysis
    await progress("analyzing", 65, {"company": metadata.get("company_name")})
    content = _smart_select_for_analysis(parsed)
    briefing = await llm.complete(
        system=CORE_ANALYSIS_SYSTEM,
        user=CORE_ANALYSIS_USER.format(content=content),
        max_tokens=8000,
        temperature=0.3,
    )

    # Step 6: Validate citations
    await progress("validating", 90, None)
    validation = validate_citations(briefing, min_citation_ratio=0.4)

    await progress("done", 100, {
        "valid": validation.is_valid,
        "citations": validation.citation_count,
    })

    return AnnualReportResult(
        company_metadata=metadata,
        executive_briefing=briefing,
        validation={
            "is_valid": validation.is_valid,
            "citation_count": validation.citation_count,
            "claim_count": validation.claim_count,
            "issues": validation.issues[:10],
        },
        source_url=url,
        page_count=parsed.total_pages,
    )


def to_dict(result: AnnualReportResult) -> dict:
    return asdict(result)
