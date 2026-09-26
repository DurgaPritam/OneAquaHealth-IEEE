# AquaSentinel FHIR profiles

FHIR R4 (4.0.1) profiles, terminology and examples that carry the AquaSentinel loop (stream check, finding, observer reliability, risk index, approved action, volunteer feedback) to public health and veterinary teams. They build on the OneAquaHealth FHIR IG (OAH IG, https://github.com/hl7-eu/oah) and reuse its codes wherever one exists.

Nothing here records infection status, cause of death or a diagnosis. Observers are pseudonymous codes only.

## Run

```bash
npm install          # installs fsh-sushi (devDependency)
npm run validate     # = bash fhir/scripts/validate.sh
```

`npm run validate` does, in order:

1. `fhir/scripts/setup_oah.sh`: downloads the HL7 validator 6.10.4 into `tools/` (gitignored), clones the OAH IG at commit `b907cf0869b59d82d9138b3d147fca66f333d911` into `fhir/.oah-ig/` (gitignored), builds it with SUSHI, generates snapshots with the validator and installs the result as the local package `hl7.eu.fhir.oah#0.1.0-ci-build` in `~/.fhir/packages`. Each step is skipped when already done, so later runs work offline.
2. `npx sushi build fhir`: our profiles, code systems, value sets, the Measure and examples into `fhir/fsh-generated/resources/` (gitignored).
3. `fhir/scripts/generate_lifecycle.py`: builds an in-memory database from the labelled synthetic Coimbra season in `api/seed.py`, runs the risk index with weather switched off, approves one action per alert site (a stand-in for the Phase 7 officer workflow, labelled synthetic) and exports two transaction Bundles with the Python exporter. Copies go to `docs/evidence/fhir/`.
4. One validator run over every example, both generated Bundles and every record in `fhir/negative/`, against the OAH package and our profiles.
5. `fhir/scripts/summarise_validation.py` writes `docs/evidence/validation-summary.md` and exits non-zero unless valid records have 0 errors and every negative record fails with the expected error.

Other commands:

```bash
npx sushi build fhir                                   # profiles only (after setup_oah.sh has run once)
.venv/bin/python fhir/scripts/gen_question_codes.py     # regenerate the stream-check code system from data/questions.json
.venv/bin/python fhir/scripts/generate_lifecycle.py     # export the synthetic lifecycle only
.venv/bin/pytest api/tests/test_fhir.py                 # exporter tests
```

Requirements: Java 17 or later (tested with 25), Node and npm, the project venv. The first run needs network access for GitHub, packages.fhir.org (FHIR core and terminology packages) and npm.

## How the unpublished OAH IG is resolved

The OAH IG CI build on build.fhir.org returns HTTP 404 and there is no package on packages.fhir.org (OQ-2), and the repository has no licence file (OQ-3), so we never copy its files into this repository. Instead `setup_oah.sh`:

1. clones https://github.com/hl7-eu/oah at the pinned commit into the gitignored `fhir/.oah-ig/`;
2. runs SUSHI on it (0 errors, 0 warnings at that commit);
3. keeps only its StructureDefinitions, CodeSystems and ValueSets (`fhir/scripts/build_oah_package.py`);
4. asks the HL7 validator (`snapshot` command) to generate snapshots, because SUSHI outputs differentials only and SUSHI needs snapshots to derive our profiles from OAH profiles;
5. writes `package.json` and `.index.json` and installs the folder as `hl7.eu.fhir.oah#0.1.0-ci-build` in the local FHIR package cache.

Our `sushi-config.yaml` then declares `hl7.eu.fhir.oah: 0.1.0-ci-build` as an ordinary dependency, and the validator gets `-ig hl7.eu.fhir.oah#0.1.0-ci-build -ig fhir/fsh-generated/resources`. Set `FORCE_OAH=1` to rebuild the package.

## Mapping

| AquaSentinel record | FHIR resource | Profile | OAH reuse |
|---------------------|---------------|---------|-----------|
| Site (ENORA site code) | Location | `aquasentinel-site` | derives from `LocationOah` (identifier, name, mode instance, position); coordinates rounded to about 100 m |
| Observer (random `OBS-XXXXXX` code) | Practitioner | `aquasentinel-observer` | identifier only; `name`, `telecom`, `address`, `gender`, `birthDate`, `photo`, `qualification` are `0..0`; invariant `as-observer-code` enforces the code pattern |
| Larval dips (total and per dip) | Observation | promoted: `aquasentinel-indicator-finding`; else `aquasentinel-citizen-finding` | code `diptera` plus our `larval-dip-count`; each dip as a `dip-count` component |
| Larval posture and guided key | Observation | as above | `diptera` plus `larval-posture`; the citizen's posture is the value, the key result a component |
| Adult mosquito (key first) | Observation | as above | `diptera` plus `adult-mosquito-key`; type only, never species |
| Amphibians heard or seen | Observation | as above | `amphibians` |
| Insectivorous birds (count) | Observation | as above | `birds` |
| Bird or amphibian photo candidate | Observation | as above | `birds` or `amphibians` from the label group in `data/labels.json`, plus `predator-photo`; species as text |
| Bats | Observation | `aquasentinel-citizen-finding` only | no OAH code, so always our profile |
| Stream check: flow types, structures | Observation (one per section, one component per answer) | indicator or citizen finding | `hydrology`; A/P/E values use OAH `absent`, `present`, `extensive` |
| Stream check: channel substrate, banks | Observation | as above | `morophology` (spelling as in the OAH IG) |
| Stream check: water signs | Observation | as above | `foam` (Foam/colour/smell) |
| Stream check: macrophytes, riparian vegetation | Observation (one per answer) | promoted: `aquasentinel-vegetation-finding` (derives from `ObservationWithCompOah`); else citizen finding | `macrophytes` / `riparianVegetation` with the OAH component slices and value sets (A/P/E, cover classes) |
| Dead birds | Observation | `aquasentinel-dead-bird-report` | none in OAH; count (Quantity), place (subject) and time only; `interpretation`, `method`, `bodySite`, `specimen`, `component`, `hasMember`, `derivedFrom`, `dataAbsentReason` are `0..0`; value only Quantity; a note stating that no diagnosis is made is required (invariant `as-dead-bird-no-diagnosis`) |
| Observer reliability for a check-in | Provenance | `aquasentinel-observer-provenance` | agent carries extension `observer-reliability`: Dawid-Skene reliability, calibration tier, calibration kappa, method |
| Weekly risk score per site | Observation | `aquasentinel-vector-habitat-risk-index` | status always `preliminary` (a screening estimate for officer review); every factor a component; missing factors carry `dataAbsentReason`, never zero; performer the city dashboard Organization, device the index engine |
| Weekly city summary | MeasureReport | `aquasentinel-city-week-report` | against Measure `aquasentinel-vector-habitat-risk-week`: sites assessed, sites on alert, sites needing data, mean index with one stratum per site |
| Approved action | ServiceRequest | `aquasentinel-action-request` | only `approved` actions are exported; category `vector-control-visit`, `sewage-inspection`, `veterinary-notification` or `habitat-restoration`; `requester` (the city dashboard Organization) is required; reason is the risk Observation |
| Volunteer message | Communication | `aquasentinel-volunteer-message` | recipient is the pseudonymous Practitioner; `about` the ServiceRequest |

Codes AquaSentinel needs that OAH lacks are in the code system `aquasentinel` (`fhir/input/fsh/terminology.fsh`). Stream-check question codes are generated from `data/questions.json` into `aquasentinel-stream-check`.

### AI suggestion and citizen answer

The Observation value is always the citizen's own answer (count or coded answer). When an AI suggested a label, the Observation also carries components `ai-suggestion`, `ai-confidence`, `ai-provider` and `citizen-decision` (`confirmed`, `corrected`, `rejected`, `manual`, `expert_review`) and a note with the AI's one-line reason. A finding whose AI suggestion the citizen has not answered (`pending`), or a rejected suggestion with no citizen value in its place, is never exported. Dead birds are never sent to an AI.

### Preliminary to final promotion

Every citizen finding starts as `preliminary` under `aquasentinel-citizen-finding`, because the OAH indicator profile fixes `status = final`. The exporter (`api/fhir/export.py`) promotes a finding to `final` under `aquasentinel-indicator-finding` (or `aquasentinel-vegetation-finding`), which conform to the OAH profiles, only when all of these hold:

1. the citizen has answered it: status `confirmed`, `corrected`, `manual`, or `rejected` with a citizen value;
2. it is not flagged for expert review (for example implausible by GBIF);
3. it has an OAH indicator code (bats and dead birds have none, so they stay in our profiles);
4. the observer's Dawid-Skene reliability, estimated across the city's stream checks in the 14-day risk window with calibration priors (the same estimator as the risk index), is known and at least `PROMOTION_MIN_RELIABILITY = 0.6`.

Stream-check answers follow rule 4. Dead bird reports stay `preliminary`: they are routed, not confirmed. The Provenance of the check-in records the reliability used, so a receiver can see why a finding was or was not promoted.

### Synthetic records

Every resource built from a row with `synthetic = true` carries `meta.tag` `http://example.org/fhir/aquasentinel/CodeSystem/aquasentinel#synthetic`, and the Bundle carries it when any entry does. All FSH examples are tagged synthetic except the real ENORA site C1.

### Bundles

`lifecycle_bundle(session, checkin_id)` and `city_week_bundle(session, city_id, week)` in `api/fhir/` return FHIR R4 transaction Bundles: every entry has a `urn:uuid` fullUrl (deterministic uuid5, so re-exports match), `request.method = POST` and, for Location, Practitioner and Organization, `ifNoneExist` on the identifier so a server does not duplicate them. All references point at fullUrls inside the Bundle. HTTP routes are not wired here.

## Validation

`docs/evidence/validation-summary.md` has the counts per file and the result of every negative test. The negative records in `fhir/negative/` (listed with the expected error in `manifest.json`) cover a Practitioner with a name and e-mail, an e-mail used as observer code, an Observation without subject, a dead bird report with an interpretation and an infection result, a dead bird report without the no-diagnosis note, a ServiceRequest category outside the value set, a ServiceRequest without requester, a disallowed status (`amended`), a preliminary record claiming the OAH profile, a Provenance without the reliability extension, a citizen finding using an OAH human health code, and a transaction Bundle whose Practitioner entry has a name.

Warnings on valid records, and why they remain:

- `Unable to validate code '1' in system http://unitsofmeasure.org`: the validator runs with `-tx n/a` so it is reproducible offline; UCUM `1` (unity) is valid UCUM but is not checked without a terminology server.
- `Measure Groups should have at least one population`: the Measure describes a summary computed by `api/risk/`, not by CQL, so it has no population criteria.
- Information level: component codes from `aquasentinel-stream-check` are not in the OAH preferred value set `OahIndicatorsNoHealthOahVs`. The binding is `preferred`, so this is allowed; OAH has no per-question codes.

`-allow-example-urls true` is set because our canonical and identifier systems use the reserved `example.org` domain (see below).

## Known limits

- Canonical `http://example.org/fhir/aquasentinel` and the identifier systems under `.../sid/` are placeholders on a reserved domain, because the project has no registered domain and OAH publishes no identifier system for ENORA site codes (OQ-13).
- `ObservationWithCompOah` allows one `macrophytes` and one `riparianVegetation` component per Observation, so each vegetation answer is its own Observation (OQ-15).
- The generated lifecycle runs with weather off, so the seasonal factor is "no data" and indices are upper bounds, exactly as the live system reports when Open-Meteo is unreachable.
