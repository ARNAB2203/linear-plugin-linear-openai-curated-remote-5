# ClearBooks MVP

ClearBooks is an MSME financial-control and compliance dashboard. This MVP lets an owner see reconciliation health, review exceptions, track filings, and approve a return draft without replacing the business's CA or accounting software.

## Included scope

- Owner dashboard with data-health metrics and priority actions
- Reconciliation exception list with resolve/escalate actions
- Filing-control workflow with owner approval
- Document-vault placeholder and CA workspace
- FastAPI JSON API with seeded demonstration data

## Architecture

```text
React (Vite) → FastAPI → in-memory seeded repository
```

The MVP uses a local SQLite database. Replace it with PostgreSQL and encrypted object storage before production use.

## Run locally

### API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive API reference.

### Database

The API now persists records. By default it creates a local SQLite file at `backend/clearbooks.db`; no separate database installation or package download is needed for development. Set `DATABASE_PATH` before starting FastAPI if you want the SQLite file elsewhere.

The MVP is intentionally configured for SQLite. Add PostgreSQL only after the pilot: use a production persistence adapter, migrations, and a managed PostgreSQL service rather than changing this development database directly.

The current MVP creates tables automatically at startup and seeds sample data only when the database is empty. Use PostgreSQL plus proper migrations, backups, encrypted storage, and authentication before production.

### Web app

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite, normally `http://localhost:5173`.

Set `VITE_API_URL=http://localhost:8000` in `frontend/.env` only if the API runs somewhere else.

## Important product boundaries

- The system does not submit GST, income-tax, or MCA filings.
- A CA/CS remains responsible for professional advice and actual filing.
- Owner approval means approval of a visible draft and evidence checklist, not a tax opinion.
- Never store government-portal passwords. Use authorised APIs and explicit customer consent when integrations are added.

See [docs/mvp-spec.md](docs/mvp-spec.md) for requirements, data model, API contract, and production next steps.

