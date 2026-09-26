# Open questions

Anything we could not verify. Each entry has the URL we tried and what we did instead.

| # | Question | URL tried | Status | What we do meanwhile |
|---|----------|-----------|--------|----------------------|
| OQ-1 | Licence of the ENORA sites API is not stated. | https://api.enora-oah.eu/api/sites/all | Open | Use site codes, names and coordinates for the demo with attribution to ENORA and OneAquaHealth. Ask the organisers before any production reuse. |
| OQ-2 | The OAH IG CI build is not published. | https://build.fhir.org/ig/hl7-eu/oah/ (HTTP 404), .../package.tgz (404) | Open | Build the IG package locally from https://github.com/hl7-eu/oah at a pinned commit with SUSHI and validate against it. |
| OQ-3 | The OAH IG repository has no LICENSE file. | https://github.com/hl7-eu/oah | Open | We reference the IG by canonical URL and do not copy its files into our repo; the validator script clones it at run time. |
| OQ-4 | The Zenodo protocol is the research protocol, not a citizen protocol. The citizen app's exact questions are not published. | https://doi.org/10.5281/zenodo.20344421, https://www.oneaquahealth.eu/citizen-science-project/, https://app.enora-oah.eu/login | Open | questions.json uses the Annex I fields a volunteer can answer by eye. The larval dip, predator and dead bird modules are AquaSentinel additions and are labelled as such in the UI. |
| OQ-5 | ECDC WNV files for 2022, 2024 and 2025 were not found as XLSX. | https://www.ecdc.europa.eu/en/publications-data/west-nile-virus-infections-humans-2022-transmission-season (no file link), .../transmission-west-nile-virus-2024-season (404) | Open | Backtest uses 2018 to 2021 and 2023. 2018 to 2020 use region names, not NUTS codes, so they are matched by name. |
| OQ-6 | ECDC files give only the first human case date per region, not weekly incidence. | see SOURCES.md section 9 | Accepted limit | The backtest compares timing (lead time) only. |
| OQ-7 | Policy Brief says 100 sites; ENORA API returns 106. | https://api.enora-oah.eu/api/sites/all | Open | Use the API list; note the difference. |
| OQ-8 | Two Citizen Science App URLs are published: apps.oneaquahealth.eu (Policy Brief p.8) and app.enora-oah.eu (project website). | both | Open | We link to the project page, not the app. |
| OQ-9 | Reisen 2006 thresholds are for *Culex tarsalis* (North America). European vectors are mainly *Culex pipiens*. | https://pubmed.ncbi.nlm.nih.gov/16619616/ | Accepted limit | Threshold is configurable in config/risk.yaml; the 14.3 °C value is cited and its species is stated. |
