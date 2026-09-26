# Backtest pre-registration: seasonal suitability against ECDC West Nile virus first-case dates

Status: **pre-registered, no result computed.** Written on 2026-09-26 before any weather was fetched for the backtest and before the index was computed for any region in this list. The only data inspected were the five ECDC season files in `data/ecdc/`, and only to list which regions and seasons exist and their first-case dates. This file is committed to git before `analysis/backtest.py` is written or run, so the history shows the plan came first.

Rule: **no weight, threshold, window, region, season or date rule in this plan is changed after results are seen.** If anything is changed later, for any reason including a bug fix that alters numbers, the change is listed under "Deviations from the pre-registered plan" in `eval/reports/backtest.md`, with the reason and the result under both the original and the changed rule.

## 1. Question

Does the weather-only part of the AquaSentinel index (seasonal suitability) reach a fixed level before the first locally acquired human West Nile virus (WNV) case in regions where one was recorded, and does it also reach that level in the OAH research-city regions, where none was recorded?

This is a test of timing, not of prediction of case counts. A seasonal suitability signal describes whether the weather favours vectors and virus development; it says nothing about infection status of any place, bird or person.

## 2. Fixed inputs

The following files are fixed at these SHA-256 hashes. The backtest script prints the hashes it ran with, and any mismatch is a deviation.

| File | SHA-256 |
|------|---------|
| config/risk.yaml | 7258cf66619ccfd0122c5b23731fe0dade431c2c1069c36c02c7c418c8fa54b2 |
| api/risk/factors.py | 3fdc304d1a3b98f9b015bb97645cac2902fc932ce1ba47b0cc1d8367ad888681 |
| api/risk/index.py | e2f06cd0af3ebf94468c1fc29e5425b34690a46f4d3fb9f2576caeece3a7dfd4 |
| data/ecdc/wnv_2018.xlsx | 3e88053d21e8d6a2bf59b8c77a979a1282ca5b0a62724e6c9573dc141d65101c |
| data/ecdc/wnv_2019.xlsx | c14c59418ab12a6b5d12a77f01c5da8e749b9cc919fda2efc4b77ee72a964181 |
| data/ecdc/wnv_2020.xlsx | c86bf58f8c5f3408554a4f77be6030a874b39255f0c8a8bfb5cafb52a5b60808 |
| data/ecdc/wnv_2021.xlsx | ec67b3eb4353c944307b07b4be3b8a2f6f9dbcf62d91e3531aff18ed7d36228b |
| data/ecdc/wnv_2023.xlsx | 706b3d9a7f3735a0fdd2580b901423b95861d6f2d939638805857cb5f6e11ad6 |

The region list is fixed in `data/ecdc/backtest_regions.json` (committed with this plan).

## 3. The environment-only index

Seasonal suitability S, exactly as the production index computes it, with config/risk.yaml version 1.0 unchanged:

- Temperature factor (`api.risk.factors.temperature`): degree-days above 14.3 °C in the window, divided by 109 and clipped to [0, 1], reduced linearly to zero between a window mean of 26 °C and 34 °C (Reisen et al. 2006; Shocket et al. 2020).
- Dry-spell factor (`api.risk.factors.dry_spell`): consecutive days under 1.0 mm of rain up to the last day of the window, divided by 10 and clipped to [0, 1].
- S = weighted mean of the two factors with weights temperature 0.75 and dry spell 0.25, over the factors that have data (`api.risk.index.combine` called with the two weather factors only; the `season` value it returns is S). The backtest imports these functions; it does not reimplement them.
- Window: 14 days (`window_days` in config/risk.yaml), ending on and including the evaluation date.
- Weather: daily mean 2 m temperature and daily precipitation sum from the Open-Meteo historical archive (https://archive-api.open-meteo.com/v1/archive, no key, CC BY 4.0) via `api.risk.weather.daily`, which rounds the point to 0.1 degree and caches on disk. One request per region-season, covering 15 March to 30 November of the season, UTC days. Default Open-Meteo archive model (no model parameter is passed).
- Evaluation dates: every Sunday from the first Sunday on or after 1 April to the last Sunday on or before 30 November of the season. Each Sunday gives one weekly value of S, labelled by its ISO week.
- Missing weather: if a factor has no data in a window it is excluded by the production weighting, as in the live index. If both are missing, that week has no value, cannot count towards a crossing, and breaks a run of consecutive weeks. The number of such weeks is reported.

Citizen observation factors (habitat, larvae, predators, dead birds) are not used, because no historical citizen data exist for these regions and seasons. The backtest therefore tests only the weather gate of the index, not the full index.

## 4. Region set

### Rule for positives (fixed now)

A positive region-season is every row in a cached ECDC season file that (a) is in Portugal, France, Italy, Belgium or Norway (the countries of the five OAH research cities) and (b) has a date in the "First human case reported" column. Rows with only equine or bird outbreaks and no human case date are excluded from both the positive and the negative sets.

Result of applying the rule (from the files, before any weather):

- 57 positive regions, all in France (13 region-seasons) or Italy (127 region-seasons). Portugal, Belgium and Norway have no row with a human case date in any cached season.
- Primary analysis: 119 positive region-seasons (2018: 37, 2019: 17, 2021: 14, 2023: 51).
- 2020: 21 Italian region-seasons. **Every first-case date in the 2020 file (all 64, all countries) falls in 2021**, which cannot be correct for a file covering the 2020 season. These are excluded from the primary analysis. They are used only in one labelled sensitivity check (section 6.4) in which the year is set to 2020 and the month and day are kept. This is an assumption, not a verified correction, and is reported as such.
- Region names in 2018 to 2020 are matched to the 2021 and 2023 NUTS 3 codes by name (accents and apostrophes normalised). Four regions have no code in any cached file (Corse-du-Sud, Pyrénées-Orientales, Vaucluse, Macerata) and are kept with `nuts3: null`; we do not assign codes from memory.

### Negative controls (fixed now)

The five OAH research-city regions, in every cached season (2018, 2019, 2020, 2021, 2023), 25 region-seasons:

| NUTS 3 | Region | Representative point |
|--------|--------|----------------------|
| PT16E | Região de Coimbra | Coimbra |
| FRJ23 | Haute-Garonne | Toulouse |
| BE234 | Arr. Gent | Ghent |
| ITF32 | Benevento | Benevento |
| NO081 | Oslo | Oslo |

None has a row (human, equine or bird) in any cached file; this was checked by name and code. 2020 negative controls are in the primary analysis, since they do not depend on a case date.

Other seasons of positive regions without a recorded case are **not** used as additional negatives. That choice is fixed now to avoid choosing controls after seeing results.

### Location of each region (fixed now)

One representative point per region: its administrative seat (Italian provincial capital, French departmental prefecture, or the city itself for the OAH regions). Coordinates come from the Open-Meteo geocoding API (https://geocoding-api.open-meteo.com/v1/search, GeoNames data), queried on 2026-09-26 with the seat name, taking the first result in the region's country with GeoNames feature code PPLA, PPLA2 or PPLC (seat of an administrative division or capital), otherwise the first result in the country. English exonyms were needed for five seats because the Italian or Dutch name returned a different place first (Mantua, Milan, Padua, Venice, Ghent). Each region's GeoNames id, feature code and admin names are recorded in `coordinate_source` in `data/ecdc/backtest_regions.json`, so every point can be checked. The points are not moved after results are seen, even where a seat is on the coast.

## 5. Outcomes

Threshold crossing: for a region-season, the crossing week is the first evaluation Sunday W such that S(W) ≥ θ and S(W + 7 days) ≥ θ. The **signal date** is W + 7 days, the Sunday on which the second consecutive week is complete, because that is the earliest date the system could have raised the signal.

### Primary outcome

For each primary positive region-season: **lead time in weeks = (first human case date minus signal date) in days / 7**, to one decimal. Positive means the signal came before the case. If no crossing occurs between 1 April and 30 November, the region-season is a **miss** and has no lead time.

Summary: n, median, interquartile range, minimum and maximum of lead time over region-seasons with a crossing; plus counts of misses. Reported overall, by season and by country.

### Secondary outcomes

1. **Share of positive region-seasons with the signal strictly before the case date** (signal date < case date), out of all 119, with a Wilson 95% interval. Misses and signals on or after the case date count as failures.
2. **Specificity check on negative controls**: for each of the 25 negative region-seasons, whether S crosses θ (same two-week rule), the signal date and the number of weeks at or above θ. Reported as the share of negative region-seasons that crossed.
3. **Contrast**: number of weeks at or above θ between 1 April and 30 November, and the seasonal maximum of S, for positive (119) against negative (25) region-seasons, summarised by median and IQR, with one two-sided Mann-Whitney U test per measure (scipy.stats.mannwhitneyu, α = 0.05). This is descriptive: region-seasons are not independent and the positive set is dominated by northern Italy.

## 6. Threshold (fixed now)

**Primary θ = 0.50**, the lower edge of the "high" band in config/risk.yaml. It is chosen because it is an existing, documented boundary of the index, not a value fitted to these data. For S to reach 0.50 with no dry spell, the temperature factor must reach 0.667, which needs about 73 degree-days above 14.3 °C in 14 days (a window mean of about 19.5 °C).

**Secondary θ = 0.30 and θ = 0.70**, the lower edges of the "moderate" and "very high" bands, reported in full alongside the primary result regardless of how they turn out. No other thresholds are tried. The alert threshold of 0.55 in config/risk.yaml is not used, because it applies to the full index (seasonal suitability x site conditions), not to S alone.

### 6.4 Sensitivity check for 2020

Primary outcome and secondary outcome 1 are recomputed for the 21 Italian 2020 region-seasons with case dates set to year 2020 (month and day unchanged), at θ = 0.50 only, and reported in a separate table labelled "2020 dates assumed, not verified".

## 7. What we expect, stated before seeing results

- S is driven mainly by temperature, which rises with the season everywhere in southern Europe. We expect most positive region-seasons to cross θ = 0.50 weeks before the first case, **and** we expect the southern negative controls (Coimbra, Toulouse, Benevento) to cross too. If so, the correct reading is that S is a seasonal gate (necessary conditions), not a predictor of where transmission happens. That is how the index is designed: S multiplies site conditions from citizen evidence; it is never used alone to alert.
- We expect Oslo, and possibly Ghent, to cross less often or later.
- Pre-stated reading of failure: if the median lead time is zero or negative, or fewer than half of positive region-seasons have the signal before the case, we will report that the weather gate gives no useful lead time at this threshold. If negative controls cross as often as positives, we will report that S has no specificity for transmission, as expected.

## 8. Limitations known in advance

1. **First-case date only.** ECDC tables give one first human case date per region-season, not weekly incidence (OQ-6). We cannot test whether S tracks the size or shape of the season. The column is labelled "First human case reported"; the files do not say whether it is the onset, diagnosis or notification date, so lead time may be biased by an unknown reporting delay (probably making it look longer).
2. **One point per region.** A NUTS 3 region is represented by the weather at its seat, which may not be where infection occurred. Several seats are coastal (for example Nice, Marseille, Toulon, Bastia, Ajaccio, La Rochelle, Venice, Bari, Taranto, Trapani), where the reanalysis cell may be milder than inland areas. Open-Meteo archive data are reanalysis, not station observations.
3. **Weather only.** No historical citizen observations exist, so the backtest cannot test the site-conditions part of the index, which is the part meant to say *where* risk is.
4. **Thresholds from another species.** The 14.3 °C base and 109 degree-days come from *Culex tarsalis* in North America; European transmission is mainly by *Culex pipiens* (OQ-9).
5. **Missing seasons.** 2022, 2024 and 2025 are not available as files (OQ-5). 2020 case dates are inconsistent with the season and are excluded from the primary analysis.
6. **Unbalanced positives.** 127 of 140 positive region-seasons are Italian and most are in the Po valley; no positive exists in Portugal, Belgium or Norway, so the three OAH research cities in those countries have no in-country comparison.
7. **Negative controls are not proven negatives.** "No recorded case" can reflect under-ascertainment or low population, not absence of transmission. Five regions give only 25 region-seasons, so the specificity estimate is imprecise.
8. **Name matching for 2018 to 2020.** Regions are matched by name; four have no NUTS code in the cached files.
9. **Not a validation of disease prediction.** Nothing here estimates infection status of any place, bird or person.

## 9. How results are reported

`eval/reports/backtest.md`, in this order:

1. **Limits first**: the list in section 8, updated with anything found while running, before any number.
2. Link to this plan and the git commit that registered it; the input hashes the run used; **Deviations from the pre-registered plan** (or "None").
3. Data: counts of regions and region-seasons actually analysed, weeks with missing weather, attribution to ECDC and Open-Meteo.
4. Table 1, primary result at θ = 0.50: n, crossings, misses, median lead (IQR, min, max), share with signal before case (Wilson 95%); overall, by season, by country.
5. Table 2, negative controls at θ = 0.50: one row per region-season with crossed (yes/no), signal date, weeks at or above θ, seasonal maximum of S.
6. Table 3, contrast (secondary outcome 3) with medians, IQRs and Mann-Whitney p-values.
7. Table 4, secondary thresholds 0.30 and 0.70: the same summary as Table 1 plus the negative-control crossing share.
8. Table 5, 2020 sensitivity check, labelled "2020 dates assumed, not verified".
9. Appendix table: every positive region-season (region, NUTS 3, season, case date, signal date, lead weeks) so each number can be traced.
10. Figures:
    - `eval/reports/backtest_leadtime.png`: lead time in weeks at θ = 0.50 for each positive region-season, one dot each, grouped by season, with a zero line; misses shown in a separate labelled row.
    - `eval/reports/backtest_trajectories.png`: weekly S by season (one panel per season), median and IQR band of positive region-seasons, one line per negative control, a horizontal line at θ = 0.50 and tick marks for positive first-case dates.
11. The per-week values for every region-season are written to `eval/reports/backtest_weekly.csv` so the figures and tables can be checked.

The report states plainly what the backtest shows and what it does not, including any failure.
