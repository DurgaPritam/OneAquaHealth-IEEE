# Status

| Phase | Area | State | Notes |
|-------|------|-------|-------|
| 0 | Source verification, scaffold | Built | docs/SOURCES.md, docs/fhir/IG_INVENTORY.md, docs/OPEN_QUESTIONS.md, data/sites.json, data/questions.json, data/ecdc/ |
| 1 | Data model and API | Built | SQLModel tables with synthetic flag, CRUD for all resources, idempotent check-in sync, EXIF-stripping photo upload, seed with 106 real sites and a labelled synthetic Coimbra season |
| 2 | Citizen PWA | Built | 6-step wizard (site map and list, OAH stream check from questions.json, larval dip with posture key, predators, dead birds with do-not-touch warning, review with consent); Dexie outbox with idempotent sync; client-side EXIF strip and 1600 px downscale; EN plus 5 machine-translated locales flagged in UI; axe 0 violations per screen in jsdom (colour contrast deferred to Playwright) |
| 3 | AI assist | Not started | |
| 4 | Calibration and reliability | Not started | |
| 5 | Risk index | Not started | |
| 6 | Backtest | Not started | |
| 7 | City dashboard and actions | Not started | |
| 8 | FHIR | Not started | |
| 9 | Engagement | Not started | |
| 10 | Hardening and deployment | Not started | |
| 11 | Submission package | Not started | |
