# Data sources (verified 26 September 2026)

Every source below was fetched from this machine on 2026-09-26. Anything that could not be verified is in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

| # | Source | Exact URL | Format | Licence | Auth | Status |
|---|--------|-----------|--------|---------|------|--------|
| 1 | ENORA OAH research sites | https://api.enora-oah.eu/api/sites/all | JSON array | Not stated (see OQ-1) | None | Verified, HTTP 200 |
| 2 | OAH Field Sampling Protocols | https://doi.org/10.5281/zenodo.20344421 | PDF, 14 pages | CC-BY-4.0 | None | Verified |
| 3 | OAH FHIR IG (source) | https://github.com/hl7-eu/oah | FSH (SUSHI) | Not stated in repo (see OQ-3) | None | Verified, commit b907cf0 (2026-06-11) |
| 4 | OAH FHIR IG (CI build) | https://build.fhir.org/ig/hl7-eu/oah/ | HTML, package | n/a | None | Not reachable, HTTP 404 (see OQ-2) |
| 5 | Open-Meteo forecast | https://api.open-meteo.com/v1/forecast | JSON | CC-BY-4.0, attribution required | None | Verified |
| 6 | Open-Meteo historical archive | https://archive-api.open-meteo.com/v1/archive | JSON | CC-BY-4.0, attribution required | None | Verified |
| 7 | GBIF occurrence search | https://api.gbif.org/v1/occurrence/search | JSON | Per record (CC0, CC-BY, CC-BY-NC) | None for search | Verified |
| 8 | GBIF species match | https://api.gbif.org/v1/species/match | JSON | CC0 backbone | None | Verified |
| 9 | ECDC WNV seasonal data | https://www.ecdc.europa.eu/en/west-nile-fever/surveillance-and-disease-data/historical | XLSX per season | CC-BY-4.0 (ECDC IP notice) | None | Verified for 2018 to 2021 and 2023 |
| 10 | OAH Policy Brief | https://doi.org/10.5281/zenodo.21476580 | PDF, 9 languages | CC-BY-4.0 | None | Verified |
| 11 | OAH Catalogue of Measures (D2.4) | https://doi.org/10.5281/zenodo.20040211 | PDF, 148 pages | CC-BY-4.0 | None | Verified |
| 12 | Reisen et al. 2006, WNV temperature thresholds | https://pubmed.ncbi.nlm.nih.gov/16619616/ | Paper | Journal | None | Verified (abstract) |
| 13 | Shocket et al. 2020, thermal optimum of WNV transmission | https://elifesciences.org/articles/58511 | Paper | CC-BY-4.0 | None | Verified |
| 14 | OAH DipteraCAST description | https://www.oneaquahealth.eu/2026/07/31/oneaquahealth-dipteracast-using-artificial-intelligence-to-predict-disease-vectors-in-urban-freshwater-ecosystems/ | Web page | n/a | None | Verified |

## 1. ENORA research sites

- Stored as [data/sites.json](../data/sites.json) with `source`, `retrieved` and `"synthetic": false`.
- 106 sites: Toulouse 24, Ghent 22, Coimbra 20, Benevento 20, Oslo 20.
- Fields per site: `code`, `name`, `city {id, name, longitude, latitude}`, `latitude`, `longitude`, `altitude` (nullable), `polygon` (nullable GeoJSON FeatureCollection, present for some Oslo sites).
- The Policy Brief reports 100 sites; the API returns 106. We use the API as is and note the difference.

## 2. Field Sampling Protocols (Zenodo 20344421)

- Title: "OneAquaHealth Field Sampling Protocols for Urban Stream Ecosystems", Calapez, Bouchali, Norte, Serra, Ramos, Schmeller, Feio. Published 2026-05-22.
- This is the **research** protocol. Its Annex I Field Sampling Form is the only structured form in the record.
- [data/questions.json](../data/questions.json) takes every Annex I field a volunteer can answer by eye, field for field, with the protocol code (RU, RI, PO, NP, D; BE ... AR; EA, ST, GA, CC), and records the instrument fields that were excluded and why.
- Answer scales: A/P/E (absent, present, extensive at more than 33 %) and riparian cover classes 1 to 5 (0-20 % ... 81-100 %).
- Section 4.2 (Adult Diptera) uses BG-Pro CO2 traps; section 4.3 (Birds) uses mist nets or BirdNET/Merlin acoustic survey. Neither is suitable for volunteers as written, which is why AquaSentinel adds a larval dip and a predator sighting module (see OQ-4).

## 3. OAH FHIR IG

Full inventory in [docs/fhir/IG_INVENTORY.md](fhir/IG_INVENTORY.md). Canonical `http://hl7.eu/fhir/ig/oah`, FHIR 4.0.1, version `0.1.0-ci-build`, depends on `hl7.fhir.uv.xver-r5.r4#0.1.0`.

## 5 and 6. Open-Meteo

- Forecast: `https://api.open-meteo.com/v1/forecast?latitude=40.2&longitude=-8.43&daily=temperature_2m_mean,precipitation_sum&past_days=3&forecast_days=1`
- Archive: `https://archive-api.open-meteo.com/v1/archive?latitude=40.2&longitude=-8.43&start_date=2023-06-01&end_date=2023-06-03&daily=temperature_2m_mean,precipitation_sum`
- Both returned `daily.time`, `daily.temperature_2m_mean` (°C), `daily.precipitation_sum` (mm). No key. Free tier is for non-commercial use with attribution.

## 7 and 8. GBIF

- `https://api.gbif.org/v1/occurrence/search?scientificName=Pelophylax%20perezi&decimalLatitude=40.1,40.3&decimalLongitude=-8.55,-8.3&limit=1` returned `count: 125`.
- `https://api.gbif.org/v1/species/match?name=Culex%20pipiens` returned `usageKey 1652991`, `matchType EXACT`.
- Used only to flag implausible bird or amphibian suggestions (zero occurrences within the radius), never to confirm a record.

## 9. ECDC West Nile virus seasonal data

Files cached in [data/ecdc/](../data/ecdc/):

| Season | URL | Columns | Region key |
|--------|-----|---------|-----------|
| 2018 | https://www.ecdc.europa.eu/sites/default/files/documents/End-of-the%20season%20update%202018_table.xlsx | Country, Region (NUTS 3 level), First human case reported, Number of human cases, ... | Region name |
| 2019 | https://www.ecdc.europa.eu/sites/default/files/documents/WNV-end-of-seaon-update.xlsx | as 2018 plus outbreaks among birds | Region name |
| 2020 | https://www.ecdc.europa.eu/sites/default/files/documents/west-nile-virus-july-to%20december-2020-transmission-season.xlsx | as 2019 | Region name |
| 2021 | https://www.ecdc.europa.eu/sites/default/files/documents/WNV_June_to_Nov_2021_0.xlsx | Place Of Infection (NUTS code), Location Name, First Human case reported, ..., Reporting Week | NUTS 3 code |
| 2023 | https://www.ecdc.europa.eu/sites/default/files/documents/transmission-WNV-2023-season.xlsx | Place Of Infection (NUTS code), Location Name, First Human case reported, human cases, equid and bird outbreaks | NUTS 3 code |

- Granularity: NUTS 3 (or GAUL 1 outside the EU), one row per region per season, with the **date of the first human case**, case counts and equine and bird outbreak counts. This is enough to test *timing* (did the environmental index rise before the first case), not weekly incidence.
- OAH research-city regions (Região de Coimbra PT16E, Haute-Garonne FRJ23, Arr. Gent BE234, Benevento ITF32, Oslo NO081): **no row in any cached season**. They are therefore negative controls in the backtest.
- Nearby regions with recorded transmission in 2023 include Gironde FRI12 (first case 2023-07-16, 26 cases), Charente-Maritime FRI32, Salerno ITF35 (2023-10-05) and Foggia ITF46, and animal outbreaks in Napoli ITF33, Avellino ITF34 and Gers FRJ24. These are the positive cases.
- Attribution required: "Dataset provided by ECDC based on data provided by public health authorities, scientific institutes or health care providers in the relevant reporting countries and/or by WHO." (https://www.ecdc.europa.eu/en/ecdc-intellectual-property-notices)

## 10. OAH Policy Brief (Zenodo 21476580)

Quotations we rely on (English section):

- p.2 "Urban streams host insect communities (Diptera) of public health importance, including mosquito species that are vectors of West Nile virus, dengue, and chikungunya, whose composition is shaped by climate and local habitat conditions."
- p.2 "Insectivorous birds, amphibians, and fish are natural control agents of insect disease vector populations. Poorer habitat conditions lead to the decline of these insect predators."
- p.2 "Incorporate Diptera monitoring from urban streams into national public health surveillance systems, using city-specific environmental baselines."
- p.2 "Degraded urban streams are associated with higher cause-specific mortality and reduced life expectancy."
- p.10 "Integrated data systems are essential to align ecological, environmental, and health information."
- p.8 to 9: the OAH Citizen Science App asks about flow types, colour, vegetation, channel characteristics and land use, plus well-being questions.

## 11. OAH Catalogue of Measures (Zenodo 20040211)

Used for [data/measures.json](../data/measures.json). Relevant statements (PDF page numbers):

- 4.3.1 Removing barriers (p.49): "during drought periods, low-head barriers may retain stagnant water, providing favourable conditions for mosquito breeding"; removal "reduces the availability of breeding sites for mosquitoes".
- 4.3.5 Constructed riffles: lists "Mosquito reduction" as a benefit.
- 4.6.1 Rain gardens, 4.6.6 Vegetated swales, 4.6.7 Retention ponds: warn that poorly drained or unmaintained designs "can create temporary stagnant water pockets that support mosquito larvae". AquaSentinel uses these as maladaptation warnings.

## 12 and 13. Temperature thresholds

- Reisen, Fang, Martinez (2006) J Med Entomol 43(2):309-317: extrinsic incubation of WNV in *Culex tarsalis* needs about 109 degree-days above a 14.3 °C zero-development point.
- Shocket et al. (2020) eLife 9:e58511: WNV transmission peaks between 23 and 26 °C; US human case incidence peaked at 24 °C mean summer temperature.
- Both are cited in [config/risk.yaml](../config/risk.yaml).

## 14. DipteraCAST

OAH's own AI tool (ENORA Innovation) predicts Diptera community composition from water quality, hydromorphology, land use and climate at 85 research sites, using Random Forest, Logistic Regression, SVM and XGBoost. It needs research-grade inputs. AquaSentinel is complementary: it collects frequent citizen observations between research campaigns and turns them into an auditable action loop.
