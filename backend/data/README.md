# Observa Tendencias: datos

- `raw/linkedin_jobs/`: Apify LinkedIn scrapes, one CSV per run (`jobs_ar_YYYY-MM-DD.csv`). Never overwrite; add a new file per scrape.
- `raw/datasets/`: official files downloaded by the backend (not in git; each one is recorded with its checksum).
- `processed/`: cleaned or derived files. `processed/data_analytics/matriz_habilidades_*.csv` are the team's files, read by `/analytics/habilidades`.

Columns: province, scraped_at (UTC), id, title, companyName, location, postedAt, seniorityLevel, employmentType, industries, salary, applicantsCount, link, applyUrl, descriptionText.
- `scripts/`: scripts de análisis de datos que generan `processed/` a partir de `raw/` (ver `scripts/README.md`).
