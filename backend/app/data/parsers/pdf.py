"""PDF parser with page-aware chunking for citation support."""
from dataclasses import dataclass
from io import BytesIO
import pdfplumber
import structlog

logger = structlog.get_logger()


@dataclass
class PageContent:
    page_number: int
    text: str


@dataclass
class ParsedPDF:
    pages: list[PageContent]
    total_pages: int

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"[p.{p.page_number}]\n{p.text}" for p in self.pages)


def parse_pdf(pdf_bytes: bytes) -> ParsedPDF:
    """Parse PDF while preserving page numbers for citation generation."""
    pages: list[PageContent] = []

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
                # Skip empty or near-empty pages (covers, blanks)
                if len(text.strip()) < 50:
                    continue
                pages.append(PageContent(page_number=i, text=text))
            except Exception as e:
                logger.warning("pdf_page_parse_error", page=i, error=str(e))

    logger.info("pdf_parsed", total_pages=total, content_pages=len(pages))
    return ParsedPDF(pages=pages, total_pages=total)


def chunk_by_section(parsed: ParsedPDF, chunk_size: int = 2500, overlap: int = 200) -> list[dict]:
    """
    Chunk text with page boundary preservation.
    Returns: [{"text": ..., "page_number": int, "chunk_index": int}]
    """
    chunks: list[dict] = []
    chunk_idx = 0

    for page in parsed.pages:
        text = page.text
        if len(text) <= chunk_size:
            chunks.append({
                "text": text,
                "page_number": page.page_number,
                "chunk_index": chunk_idx,
            })
            chunk_idx += 1
        else:
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunks.append({
                    "text": text[start:end],
                    "page_number": page.page_number,
                    "chunk_index": chunk_idx,
                })
                chunk_idx += 1
                start += chunk_size - overlap

    return chunks
