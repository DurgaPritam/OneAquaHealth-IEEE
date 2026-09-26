# Risk model

AquaSentinel scores **conditions that favour mosquito vectors** at urban stream sites. It never states or implies the infection status of a site, bird or person.

- Code: [api/risk/](../api/risk/) (factors, combination, service), TypeScript port for the static demo in [web/src/lib/risk.ts](../web/src/lib/risk.ts)
- Parameters: [config/risk.yaml](../config/risk.yaml). Every stored score records the config fingerprint (`version+sha256[:8]`).
- Tests: [api/tests/test_risk.py](../api/tests/test_risk.py)
- Sensitivity: [eval/reports/sensitivity.md](../eval/reports/sensitivity.md)

## Formula

```
index = seasonal suitability x site conditions

seasonal suitability = (0.75 T + 0.25 D) / (sum of weights of the weather factors that have data)
site conditions      = sum_i w_i f_i / sum_i w_i  over site factors i that have data
```

Why a product rather than one weighted sum: weather is the same for every site in a city, so it can say *when* but not *where*. In an early version (a single weighted mean) the hot, dry weeks of September 2026 in Coimbra pushed 16 of 20 synthetic sites over the alert threshold on weather alone. As a multiplier, weather switches the index off in cold weeks, and citizen evidence decides which sites stand out (0 to 3 alerts a week in the same scenario).

## Factors

| Factor | Part | Weight | Value in [0, 1] | Inputs | Source |
|---|---|---|---|---|---|
| T Temperature suitability | season | 0.75 | degree-days above 14.3 °C over 14 days / 109, reduced linearly above a 26 °C mean to 0 at 34 °C | Open-Meteo daily mean temperature | Reisen et al. 2006 (14.3 °C, 109 DD, *Culex tarsalis*); Shocket et al. 2020 (optimum 23 to 26 °C) |
| D Dry spell and stagnation | season | 0.25 | consecutive days under 1 mm up to the last day / 10 | Open-Meteo daily precipitation | OAH Catalogue of Measures 4.3.1 (weirs hold stagnant water in drought) |
| Larval habitat | site | 0.30 | weighted mean of expected A/P/E scores (0, 0.5, 1): still water 0.35, sewage smell 0.2, organic matter 0.15, foam 0.1, unusual colour 0.1, free-floating plants 0.1 | stream-check answers, Dawid-Skene posterior across all sites of the city | OAH field protocol Annex I; Policy Brief p.7 |
| Mosquito larvae found | site | 0.35 | 1 - exp(-mean larvae per dip / 3), reliability weighted | larval dip counts | AquaSentinel module |
| Missing predators | site | 0.20 | 1 - weighted presence of frogs (none 0, heard 0.7, seen 1; weight 0.4), insect-eating birds (count / 5; 0.4), bats (0.2) | predator module | Policy Brief p.2 and p.7 |
| Dead bird reports | site | 0.15 | reports / 3 | dead bird module | routing signal only, never a diagnosis |

## Reliability weighting

- Stream-check answers: for each habitat question, [Dawid-Skene EM](../api/reliability/dawid_skene.py) runs over every (site, observer, answer) in the city and window. Each observer's calibration agreement seeds their confusion matrix (5 pseudo-observations). A site's answer is the posterior expected score, not a vote.
- Counts: each check-in is weighted by its observer's estimated reliability (the mean Dawid-Skene expected accuracy over habitat questions, 0.7 if unknown).
- Why priors: without them, Dawid-Skene lost to majority vote on panels of one to three observers in our simulation ([eval/reports/calibration.md](../eval/reports/calibration.md)).

## Missing data

- A factor without data has `value: null`. It is shown as "no data" and excluded from its part, never treated as zero.
- The score comes with a **range**: the index if every missing site factor were 0, and if every one were 1.
- If the site factors with data carry less than 60 % of the site weight, the site is flagged `needs_data` and **cannot alert**; it becomes a campaign target instead.
- No weather: seasonal suitability is taken as 1 (the upper bound) and the explanation says so.

## Alerts

`alert = index >= 0.55 and not needs_data`. An alert only drafts an action for an officer. Nothing is sent without approval.

## Tracing a score

Every `RiskScore` stores each factor's value, weight, contribution, data age and inputs. A real example from the synthetic Coimbra season (site C1, week 2026-W38, real weather):

```
Index 0.74 (very high) = seasonal suitability 1.00 x site conditions 0.74.
temperature      1.00  115 degree-days above 14.3 °C in 14 days; mean 22.5 °C      (Open-Meteo, 14 daily rows stored)
dry_spell        1.00  14 dry days in a row; 1 mm of rain in the window
vector_presence  0.99  2 larval dip sessions; reliability-weighted mean 13.1 per dip  (check-ins 114, 136)
predator_deficit 0.88  predator presence 0.12 from 2 observations
habitat          0.39  6 answers to 3 questions; posterior for still water:
                       absent 0.03, present 0.945, extensive 0.025
                       raw: check-in 114 OBS-SYN000 "present", check-in 136 OBS-SYN003 "present"
host_signal      0.67  2 dead birds reported; routed to the veterinary team, not a diagnosis
```

`GET /api/risk/latest?city_id=CO` and `GET /api/risk/history/{site_id}` return the full trace; the city dashboard shows the same fields.

## Limits

- Weights are expert judgement written down for transparency, not fitted. The backtest ([eval/reports/backtest.md](../eval/reports/backtest.md)) can only test the weather part, because no historical citizen data exists.
- The temperature thresholds come from *Culex tarsalis*; European transmission is mainly through *Culex pipiens* (OQ-9).
- Dry spell is a crude proxy for stagnation; it ignores rain-filled pools after storms.
- All citizen data in the demo is synthetic.
