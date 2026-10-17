# AstraTrade — Market Intelligence Platform

A bilingual (English/Arabic) Django platform foundation for market research, manually reviewed trade ideas, transparent outcome logs, risk sizing, and membership requests.

## Current implementation
- Responsive landing page with Arabic/English toggle and RTL support.
- Django admin for trade ideas and membership/payment requests.
- Public signal list and outcome-derived metrics (only from records entered by administrators).
- Position sizing calculator (educational estimate, not instrument-specific broker sizing).
- `/health/` health endpoint.
- PostgreSQL via `DATABASE_URL`; SQLite fallback for local development.
- Railway-ready Docker deployment.

## Important integrations not yet active
Live market data, automated signal generation, Telegram delivery, verified USDT settlement, online payment gateway, member authentication/entitlements, and independent performance audit require configuration and testing. The website intentionally labels market charts as illustrative and does not fabricate quotes or performance.

## Deploy
Railway should build from `Dockerfile`. Configure `SECRET_KEY` with a strong random value, `DEBUG=False`, and `DATABASE_URL` from a Railway PostgreSQL service. The startup command runs migrations, collects static assets, then starts Gunicorn. Create the first admin account with a one-off Railway command: `python manage.py createsuperuser`.

## Local
`python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py runserver`

Paid trading research may be regulated. Obtain jurisdiction-specific legal advice before enabling checkout or distributing paid signals. No profit is guaranteed.
