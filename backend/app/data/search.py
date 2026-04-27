"""Web search via Exa. Recency-biased and better suited for research than standard search."""
from typing import Optional
from exa_py import Exa
import structlog

from app.config import settings

logger = structlog.get_logger()
_client: Optional[Exa] = None


def get_client() -> Exa:
    global _client
    if _client is None:
        _client = Exa(api_key=settings.EXA_API_KEY)
    return _client


async def find_annual_report(company_name: str, year: Optional[int] = None) -> Optional[str]:
    """
    Search for the annual report PDF URL for a given company.
    Returns the best matching URL or None.
    """
    client = get_client()
    year_filter = f" {year}" if year else ""
    query = f"{company_name} annual report{year_filter} filetype:pdf"

    logger.info("searching_annual_report", company=company_name, year=year)
    result = client.search(
        query,
        type="neural",
        num_results=10,
    )

    candidates = []
    for r in result.results:
        url = r.url.lower()
        score = r.score or 0
        if ".pdf" in url:
            score += 0.3
        if any(kw in url for kw in ["investor", "ir.", "/ir/", "annualreport"]):
            score += 0.2
        if "wikipedia" in url or "linkedin" in url:
            score -= 0.5
        candidates.append((score, r.url))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    best_url = candidates[0][1]
    logger.info("annual_report_found", company=company_name, url=best_url)
    return best_url


async def search_company_context(company_name: str, max_results: int = 5) -> list[dict]:
    """
    Search for additional context: news, competitor mentions, industry data.
    Returns a list of {url, title, text}.
    """
    client = get_client()
    result = client.search_and_contents(
        f"{company_name} company overview business strategy",
        type="neural",
        num_results=max_results,
        text=True,
    )
    return [
        {"url": r.url, "title": r.title, "text": (r.text or "")[:5000]}
        for r in result.results
    ]
