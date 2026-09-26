# Status

| Phase | Area | State | Notes |
|-------|------|-------|-------|
| 0 | Source verification, scaffold | Built | docs/SOURCES.md, docs/fhir/IG_INVENTORY.md, docs/OPEN_QUESTIONS.md, data/sites.json, data/questions.json, data/ecdc/ |
| 1 | Data model and API | Built | SQLModel tables with synthetic flag, CRUD for all resources, idempotent check-in sync, EXIF-stripping photo upload, seed with 106 real sites and a labelled synthetic Coimbra season |
| 2 | Citizen PWA | Built | 6-step wizard (site map and list, OAH stream check from questions.json, larval dip with posture key, predators, dead birds with do-not-touch warning, review with consent); Dexie outbox with idempotent sync; client-side EXIF strip and 1600 px downscale; EN plus 5 machine-translated locales flagged in UI; axe 0 violations per screen in jsdom (colour contrast deferred to Playwright) |
| 3 | AI assist | Built | Provider layer (mock default, Anthropic claude-opus-5 via SDK structured output, Gemini needs GEMINI_MODEL), validation gate against data/labels.json with drops shown in UI, JSON guided keys (larvae posture, adult tiger mosquito), key vs vision disagreement, GBIF plausibility to expert review, dead birds never analysed, accept/change/reject chips (unanswered never sent), mock badge, vision eval script (mock report only; no licensed photo set yet) |
| 4 | Calibration and reliability | Built | 19-item reference set (illustrations generated from their answers; synthetic; pending team panel review), practice round with per-question Cohen kappa, rule-based bias feedback, tiers New/Calibrated/Trusted; MAP Dawid-Skene with calibration prior; simulation report shows plain ML Dawid-Skene loses to majority vote on small panels and how the priors fix it (tuned on a separate seed); TS scoring pinned to Python by golden fixtures |
| 5 | Risk index | Not started | |
| 6 | Backtest | Not started | |
| 7 | City dashboard and actions | Not started | |
| 8 | FHIR | Not started | |
| 9 | Engagement | Not started | |
| 10 | Hardening and deployment | Not started | |
| 11 | Submission package | Not started | |
