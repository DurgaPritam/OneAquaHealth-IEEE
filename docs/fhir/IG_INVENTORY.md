# OAH FHIR IG inventory

- Source: https://github.com/hl7-eu/oah (branch `master`, commit `b907cf0869b59d82d9138b3d147fca66f333d911`, 2026-06-11)
- Canonical: `http://hl7.eu/fhir/ig/oah`, package id `hl7.eu.fhir.oah`, version `0.1.0-ci-build`, FHIR 4.0.1
- Dependency: `hl7.fhir.uv.xver-r5.r4#0.1.0`
- CI build https://build.fhir.org/ig/hl7-eu/oah/ returned HTTP 404 on 2026-09-26, so we build the IG package locally with SUSHI from the source (see OQ-2).

## Profiles

| Profile | Id | Parent | Key constraints |
|---------|----|--------|-----------------|
| GroupOah | group-oah | Group | person cohort, `actual = false`, `member 0..0`, characteristic 1..* |
| LibraryOah | library-oah | Library | dataset description, `url`, `title`, `status`, `type`, `date` required |
| LocationOah | location-oah | Location | `identifier 1..`, `name 1..`, `mode = #instance`, `position` 0..1 with lat and long 1..1 |
| ObservationHealthMeasureOah | observation-health-measure-oah | Observation | `status = #final`, code from HealthIndicatorsOahVs, `subject only Reference(LocationOah)`, `focus only Reference(GroupOah)`, value CodeableConcept or Quantity |
| ObservationIndicatorsOah | observation-indicators-oah | Observation | `status = #final`, code from OahIndicatorsNoHealthOahVs (preferred), `subject only Reference(LocationOah)`, `effective[x] 1..`, **`performer 1..`**, value CodeableConcept or Quantity, components allowed |
| ObservationWithCompOah | observation-with-component-oah | ObservationIndicatorsOah | `value[x] 0..0`, `component 1..`, slices `macrophytes`, `nonNativeMacrophytes`, `riparianVegetation` with required value sets |
| SpecimenOah | specimen-oah | Specimen | `subject only Reference(LocationOah)`, `collection.collector only Reference(PractitionerRole)`, `collected[x] only dateTime` |

## Extensions

| Extension | Id | Context |
|-----------|----|---------|
| LibrarySize | library-size | Library, Quantity |
| LibraryNumberOfRecords | library-numberOfRecords | Library, integer |
| (external) artifact-relatedArtifact | used on LocationOah as `referenceForm` | Location |

## Code systems and value sets

| Artefact | Id | Notes |
|----------|----|-------|
| CodeSystem TemporaryOahSystem | temporarySystem-oah-eu | `http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu`, experimental, case sensitive; indicators, health codes, coded results |
| ValueSet OahIndicatorsVs | temporarySystem-oah-eu | all codes from TemporaryOahSystem (note: same id as the code system) |
| ValueSet OahIndicatorsNoHealthOahVs | oah-indicators-no-health-oah-vs | OahIndicatorsVs minus health codes |
| ValueSet HealthIndicatorsOahVs | (health-indicators-vs.fsh) | disease prevalence, mortality, hospitalisation codes |
| ValueSet ObservationTypeWithComponentOahVs | observation-type-with-component-oah-vs | macrophytes, riparianVegetation, nutrients |
| ValueSets for macrophytes and riparian vegetation | macrophytes-vs.fsh, riparianVegetation-vs.fsh | component code and value sets (absent/present/extensive, cover classes) |
| ValueSet SpecimenTypeOahVs | specimen-type-oah-vs | SNOMED 11713004 Water |
| ValueSet OahCohortCharacteristicCodeVs | cohort-characteristic-code-vs.fsh | cohort criteria |

## Coverage of the One Health chain

| Theme | IG code (TemporaryOahSystem) | Profile | AquaSentinel use |
|-------|------------------------------|---------|------------------|
| Diptera | `#diptera` "Diptera (specially Culicidae and Psycodidae)" | ObservationIndicatorsOah | larval dip counts, adult mosquito key result |
| Birds | `#birds` | ObservationIndicatorsOah | insectivorous bird sightings (predator module) |
| Amphibians | `#amphibians` | ObservationIndicatorsOah | amphibians heard or seen |
| Fish | `#fish`, `#fishes` | ObservationIndicatorsOah | not collected by volunteers |
| Habitat | `#hydrology`, `#morophology` (spelling as in IG), `#foam` "Foam/colour/smell" | ObservationIndicatorsOah | stream check flow, substrate, banks, sewage signs |
| Vegetation | `#macrophytes`, `#riparianVegetation` with components | ObservationWithCompOah | stream check sections 4a and 4b |
| Human health | `#disease-prevalence`, `#causes-of-death` and others | ObservationHealthMeasureOah on GroupOah | not produced: AquaSentinel never makes health claims about people |
| Dead birds | none | none | our own profile (report only, no diagnosis) |
| Vector-habitat risk index | none | none | our own Observation profile, preliminary status, then MeasureReport |
| Actions, messages, provenance | none | none | base FHIR R4 ServiceRequest, Communication, Provenance, profiled by us |

## Gaps we fill with our own profiles (fhir/)

1. No code for dead bird reports, larval counts per dip, or vector-habitat risk. We add a small AquaSentinel code system and keep OAH codes wherever one exists.
2. `ObservationIndicatorsOah` fixes `status = #final`. Citizen findings start as preliminary; our profile allows `preliminary`, and a finding is promoted to an `ObservationIndicatorsOah`-conformant record only after citizen confirmation and reliability weighting.
3. `performer 1..` is required. Our performer is a pseudonymous Practitioner with only an identifier (random code), no name or telecom.
4. Nothing in the IG covers observer reliability. We use Provenance with an extension carrying the Dawid-Skene reliability score.
