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

## Running locally

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY and EXA_API_KEY at minimum

docker-compose up -d
docker-compose exec backend alembic upgrade head
docker-compose exec backend playwright install chromium --with-deps
```

Open `http://localhost:3000`. With `APP_ENV=development`, authentication is bypassed — no Clerk setup needed for local testing.

For a first test, create a project, select Annual Report Analysis, and type a company name like `Bank Central Asia`. The run takes 2–3 minutes depending on the PDF size.

## API keys required

- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `EXA_API_KEY` — from dashboard.exa.ai (free tier available)
- `VOYAGE_API_KEY` — optional, only needed if you enable vector search features

See `docs/env-setup.md` for full deployment instructions including Railway and Vercel.

## How the pipeline works

```
user submits company name
  → backend enqueues arq job
  → worker: search for PDF URL (Exa)
  → worker: fetch and parse PDF (Playwright + pdfplumber)
  → worker: extract metadata via Claude
  → worker: generate executive briefing via Claude
  → worker: validate citations
  → frontend receives progress updates via SSE
  → user downloads .pptx
```

The citation validator checks that claims containing numbers, percentages, or financial figures have a corresponding page reference. Runs where citation coverage falls below the threshold are flagged in the UI.

## Project structure

```
researchpilot/
├── .env.example
├── .env                          
├── .gitignore
├── docker-compose.yml
├── railway.toml
├── vercel.json
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial.py
│   └── app/
│       ├── main.py               ← FastAPI entry point
│       ├── config.py             ← semua env vars
│       ├── auth.py               ← Clerk JWT verification
│       ├── api/
│       │   ├── routes/
│       │   │   ├── projects.py
│       │   │   ├── research.py   ← trigger jobs + SSE stream
│       │   │   └── exports.py    ← download PPTX
│       │   └── schemas/
│       │       ├── project.py
│       │       └── research.py
│       ├── core/
│       │   ├── prompts/
│       │   │   └── annual_report.py   ← prompt templates
│       │   └── workflows/
│       │       ├── annual_report.py
│       │       ├── competitive_landscape.py
│       │       ├── precedent_search.py
│       │       └── industry_overview.py
│       ├── data/
│       │   ├── search.py              ← Exa web search
│       │   ├── scrapers/
│       │   │   └── annual_report.py   ← Playwright PDF fetch
│       │   └── parsers/
│       │       └── pdf.py             ← pdfplumber parser
│       ├── db/
│       │   ├── session.py
│       │   └── models.py              ← Project, ResearchRun, Company, Document
│       ├── exports/
│       │   └── pptx.py                ← PowerPoint generator
│       ├── jobs/
│       │   └── worker.py              ← arq background worker
│       └── llm/
│           ├── client.py              ← Anthropic SDK wrapper
│           └── validators.py          ← citation checker
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── middleware.ts              ← Clerk route protection
│       ├── app/
│       │   ├── globals.css
│       │   ├── layout.tsx
│       │   ├── page.tsx               ← landing page
│       │   ├── sign-in/
│       │   ├── sign-up/
│       │   └── dashboard/
│       │       ├── page.tsx           ← list projects
│       │       └── [projectId]/
│       │           ├── page.tsx       ← list runs + submit
│       │           └── run/[runId]/
│       │               └── page.tsx   ← live progress + briefing
│       ├── components/
│       │   ├── layout/
│       │   │   └── AppShell.tsx       ← sidebar + breadcrumb
│       │   ├── research/
│       │   │   ├── ProgressTimeline.tsx
│       │   │   └── BriefingRenderer.tsx
│       │   └── ui/
│       │       └── index.tsx          ← Button, Input, Card, Badge, dll
│       └── lib/
│           ├── api.ts                 ← semua API calls + SSE reader
│           └── utils.ts
│
├── infra/
│   ├── docker/
│   │   ├── postgres.Dockerfile
│   │   ├── init.sql
│   │   └── nginx.conf
│   └── scripts/
│       ├── seed_companies.py
│       └── reset_db.sh
│
└── docs/
    ├── env-setup.md
    └── adding-workflows.md
```

## Adding a workflow

Copy an existing workflow file from `backend/app/core/workflows/`, implement the `run(target, progress)` function, register it in `backend/app/jobs/worker.py`, and add it to the workflow map in `backend/app/api/routes/research.py`. Full instructions in `docs/adding-workflows.md`.

## Known limitations

Annual reports that are scanned images (non-text PDFs) will not parse correctly. Some Indonesian company IR pages require scraping logic adjustments due to non-standard layouts. Rate limiting is not implemented. Test coverage is minimal.

## License

MIT
