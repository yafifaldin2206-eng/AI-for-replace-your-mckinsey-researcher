# ResearchPilot

**Replicate your McKinsey researcher.** AI-powered tool untuk meringkas annual report ratusan perusahaan dengan kualitas konsultan senior — bukan generic LLM output.

## MVP scope

Workflow utama: **Annual Report Summarizer**
- Input: nama perusahaan atau URL annual report
- Proses: scrape → parse PDF → chunk → analyze dengan Claude → validate citations
- Output: PowerPoint-ready deck dengan executive summary, financial highlights, strategic priorities, risk factors, dan competitive positioning

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + Python 3.12 |
| Database | Postgres 16 + pgvector |
| Cache/Queue | Redis + arq (async jobs) |
| LLM | Claude Opus 4.7 via Anthropic SDK |
| Search | Exa (recency-biased web search) |
| Scraping | Playwright (handles SPA & PDF) |
| Frontend | Next.js 15 (App Router) + Tailwind + shadcn/ui |
| Export | python-pptx |
| Deployment | docker-compose (local) → Railway + Vercel |

## Quick start

```bash
# 1. Copy env file dan isi API keys
cp .env.example .env

# 2. Run all services
docker-compose up -d

# 3. Run DB migration (first time only)
docker-compose exec backend alembic upgrade head

# 4. Open frontend
open http://localhost:3000
```

## API keys yang dibutuhkan

- `ANTHROPIC_API_KEY` — untuk Claude
- `EXA_API_KEY` — untuk web search (https://exa.ai)
- `VOYAGE_API_KEY` — untuk embeddings (https://voyageai.com)

## Arsitektur

Lihat [docs/architecture.md](docs/architecture.md) untuk diagram lengkap.

Singkatnya: user submit company name → backend trigger arq job → workflow chain (scope → fetch → parse → chunk → analyze → validate → export) → frontend stream progress via SSE → user download .pptx.

## Yang membuat ini berbeda dari "langsung ke LLM"

1. **Data acquisition otomatis** — user tidak upload PDF manual; sistem cari & download annual report
2. **Multi-step prompt chain** — bukan single prompt; ada scoping → extraction → synthesis → validation
3. **Citation validator** — setiap claim wajib ada page reference; output tanpa citation di-flag
4. **PowerPoint output** — langsung deck-ready, bukan markdown
5. **Caching cerdas** — annual report yang sama tidak di-fetch ulang; kompetitor lookup di-cache
