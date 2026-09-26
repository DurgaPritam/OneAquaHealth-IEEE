# Devpost submission text (draft)

## Project name

AquaSentinel

## Tagline (under 200 characters)

Citizen stream checks become a human-approved early warning for mosquito habitat, with FHIR records for public health and veterinary teams.

## Track alignment statement

AquaSentinel's primary tracks are **AI-Supported Assessment** and **Data-to-Insight**. It also covers **Digital Health Standards**, **Citizen Science UX**, **Resilience Informatics** and **Community and Gamification**.

- The AI suggests with a confidence and a reason; the citizen decides.
- Answers are weighted by calibrated observer reliability.
- The evidence becomes a transparent, traceable risk index.
- A city officer approves every action.
- Records are exported as FHIR R4 on the OneAquaHealth implementation guide.

## Inspiration

The OneAquaHealth Policy Brief (2026) found that urban streams host mosquitoes able to carry West Nile virus, dengue and chikungunya. It also found that degraded streams lose the frogs, birds and fish that eat them. It asks cities to "incorporate Diptera monitoring from urban streams into national public health surveillance systems".

Research traps run a few nights a year. Volunteers visit streams every week, but their observations rarely reach anyone who can act. We wanted to close that loop without letting AI or automation make decisions that belong to people.

## What it does

1. **A volunteer does a 15-minute stream check** at one of the 106 OneAquaHealth research sites. It covers:
   - the OneAquaHealth field-form questions a person can answer by eye;
   - a five-cup larval dip with a resting-posture key;
   - predators (frogs, insect-eating birds, bats);
   - dead birds, with "do not touch" guidance.

   It works offline, photos lose their location data on the device, and volunteers are anonymous codes.
2. **AI suggests, the citizen decides.**
   - Each suggestion is a chip with a confidence and a one-line reason, which the volunteer must accept, change or reject.
   - Only labels from a fixed list survive, and anything else is shown as removed.
   - Mosquitoes are identified to type, never species. Dead birds never go to a model.
   - GBIF records flag unlikely species for expert review.
3. **Reliability.** A five-minute practice round measures each volunteer's agreement (Cohen's kappa) and explains their bias in plain words. A Dawid-Skene model then combines volunteers, seeded by that calibration.
4. **A transparent risk index.**
   - It multiplies seasonal suitability, from real weather and published West Nile virus thresholds, by site conditions from volunteer evidence.
   - Missing data widens a displayed range and can never trigger an alert.
   - Every number traces back to check-ins and daily weather.
5. **Human-approved action.**
   - Alerts draft actions mapped to sections of the OneAquaHealth Catalogue of Measures.
   - A named officer approves, edits or dismisses each draft.
   - If the officer picks a measure the Catalogue warns can create standing water, AquaSentinel shows that warning.
6. **FHIR records.**
   - Findings, sites, pseudonymous observers, reliability, approved actions, messages and weekly summaries export as FHIR R4 on the OneAquaHealth implementation guide.
   - The HL7 validator reports 0 errors, and all 12 deliberately broken records are rejected.
7. **Feedback.**
   - Volunteers are told when their observation led to an action.
   - Campaigns point them to sites with data gaps.
   - A team leaderboard rewards quality, never volume.

## How we built it

- **API:** Python 3.11 with FastAPI and SQLModel.
- **Web app:** a React, TypeScript and Tailwind PWA, with a Dexie offline queue, Leaflet maps and i18next in six languages.
- **FHIR:** profiles written in SUSHI and checked with the HL7 validator.
- **Analysis:** pandas, SciPy and matplotlib.
- **Browser demo:** the judges' link runs the whole backend in the browser. TypeScript ports of the risk engine, Dawid-Skene, calibration and action drafting are pinned to the Python results by golden-fixture tests.
- **Tests:** 142 pytest, 37 Vitest and 8 Playwright end-to-end tests (phone and desktop), including axe checks for colour contrast. All run in CI.

## Challenges we ran into

- **Dawid-Skene failed on realistic panels.** With the one to three volunteers per site and week that are realistic, plain Dawid-Skene did worse than majority vote in simulation, and its class prior could collapse onto one class. MAP priors, including one from calibration, fixed it. We tuned them on a separate seed and report both versions.
- **Our first index alerted on weather alone.** A single weighted sum put 16 of 20 sites on alert in a hot, dry September, because weather is the same for every site. We switched to multiplying seasonal suitability by site conditions.
- **The OneAquaHealth FHIR guide has no published package.** We build it from its pinned source, derive our profiles from it, and validate against it.
- **Pre-registration.** We committed the backtest plan before computing anything, and reported the one deviation.

## Accomplishments that we're proud of

- **A pre-registered backtest against real ECDC West Nile data.** The weather-only signal preceded the first human case in 118 of 119 region-seasons, a median of 8 weeks ahead. It also fired in 24 of 25 control regions. We report both: weather tells you *when*, not *where*, which is exactly why citizen evidence matters.
- **Traceability.** Every number in the city view can be traced to its inputs.
- **Principles tested in code.** No automatic actions, no diagnosis, no invented labels, and no reward for spam are all covered by tests, not just stated.

## What we learned

- Citizen data needs calibration before aggregation.
- Honest uncertainty (ranges, "needs data") is more useful to an officer than a single number.

## What's next for AquaSentinel

- Pilot with a OneAquaHealth city team.
- Replace the synthetic calibration drawings with expert-labelled photos.
- Run the vision evaluation on a licensed photo set.
- Get native-speaker review of the translations.
- Integrate with the OneAquaHealth Citizen Science App and the Decision Support System.

## Built with

python, fastapi, sqlmodel, pydantic, numpy, scipy, pandas, react, typescript, vite, tailwindcss, dexie, leaflet, i18next, fhir, sushi, hl7-validator, playwright, axe-core, open-meteo, gbif, ecdc, anthropic-claude (optional provider)

## Links

- Demo: https://durgapritam.github.io/OneAquaHealth-IEEE/
- Code: https://github.com/DurgaPritam/OneAquaHealth-IEEE
- Video: (add the link after recording; the script is in docs/DEMO_SCRIPT.md)
