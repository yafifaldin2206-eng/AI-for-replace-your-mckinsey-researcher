# ResearchPilot

ResearchPilot is an open-source AI research tool that automates the kind of work a junior strategy consultant would do — finding annual reports, parsing them, and generating structured executive briefings. The output is a PowerPoint deck, not a chat response.

Instead of pasting a PDF into Claude, getting your token exploded, for only got "penjilat" answer, ResearchPilot builds a full pipeline around the LLM — automated data acquisition, multi-step prompt chains, citation validation, and formatted export. The result is more reliable and consistent than a single prompt, and requires no manual work from the user beyond typing a company name.

## What it does

Four research workflows are currently supported:

**Annual Report Analysis** — given a company name or PDF URL, the system finds and downloads the annual report, parses it page by page (preserving page numbers for citations), and produces an eight-section executive briefing: executive summary, financial performance, strategic priorities, competitive positioning, risk factors, forward outlook, and critical gaps. Every factual claim is required to have a page citation; claims without citations are flagged.

**Competitive Landscape** — given a market description, the system searches for competitor data and produces a structured map of players, their positioning, and white space no current player occupies well.

**Precedent Search** — given a scenario (fundraising stage, business model, geography), the system finds analogous deals or strategic moves and synthesizes the pattern across them, including cautionary cases.

**Industry Overview** — a sector primer covering market sizing, value chain, competitive structure, regulatory environment, and a bull/base/bear outlook.

All workflows run as background jobs. Progress streams to the frontend in real time via SSE. Results can be downloaded as a .pptx file.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.12 |
| Database | Postgres 16 with pgvector |
| Queue | Redis + arq |
| LLM | Claude via Anthropic SDK |
| Search | Exa |
| Scraping | Playwright |
| Frontend | Next.js 15, Tailwind CSS |
| Auth | Clerk |
| Export | python-pptx |

