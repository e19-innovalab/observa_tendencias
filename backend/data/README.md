# Observa Tendencias: datos

- `raw/linkedin_jobs/`: Apify LinkedIn scrapes, one CSV per run (`jobs_ar_YYYY-MM-DD.csv`). Never overwrite; add a new file per scrape.
- `processed/`: cleaned or derived files.

Columns: province, scraped_at (UTC), id, title, companyName, location, postedAt, seniorityLevel, employmentType, industries, salary, applicantsCount, link, applyUrl, descriptionText.
- `scripts/`: scripts de análisis de datos que generan `processed/` a partir de `raw/` (ver `scripts/README.md`).
