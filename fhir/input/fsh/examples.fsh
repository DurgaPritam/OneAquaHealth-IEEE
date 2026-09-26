// Examples. The site is a real ENORA site (C1, Coimbra); every observation, observer,
// action and message below is illustrative and tagged synthetic.

RuleSet: Synthetic
* meta.tag[+] = AquaSentinelCodes#synthetic "Synthetic record"

RuleSet: Narrative(text)
* text.status = #generated
* text.div = "<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>{text}</p></div>"

Instance: example-risk-engine
InstanceOf: Device
Title: "AquaSentinel risk index engine"
* insert Narrative(AquaSentinel risk index engine)
* deviceName.name = "AquaSentinel vector-habitat risk index"
* deviceName.type = #user-friendly-name
* version.value = "1.0"

Instance: example-site-c1
InstanceOf: AquaSentinelSite
Title: "Site C1 Exploratório (ENORA)"
Description: "Real OneAquaHealth research site from the ENORA sites API; coordinates rounded to about 100 m."
* insert Narrative(Site C1 Exploratório ENORA)
* identifier.system = $sid-site
* identifier.value = "C1"
* name = "Exploratório"
* status = #active
* mode = #instance
* position.latitude = 40.198
* position.longitude = -8.429

Instance: example-observer
InstanceOf: AquaSentinelObserver
Title: "Pseudonymous observer OBS-7F3K2Q"
* insert Narrative(Pseudonymous observer OBS-7F3K2Q)
* insert Synthetic
* identifier.system = $sid-observer
* identifier.value = "OBS-7F3K2Q"
* active = true

Instance: example-city-co
InstanceOf: Organization
Title: "Coimbra city dashboard"
* insert Narrative(Coimbra city dashboard)
* insert Synthetic
* identifier.system = $sid-city
* identifier.value = "CO"
* name = "AquaSentinel city dashboard, Coimbra"
* active = true

Instance: example-larval-dips-final
InstanceOf: AquaSentinelIndicatorFinding
Title: "Larval dips, promoted to final (OAH diptera)"
Description: "Five dips, 12 larvae in total. The AI saw larvae in the cup photo and the citizen confirmed."
* insert Narrative(Larval dips promoted to final OAH diptera)
* insert Synthetic
* identifier.system = $sid-finding
* identifier.value = "101"
* status = #final
* code.coding[0] = $oah#diptera "Diptera"
* code.coding[+] = AquaSentinelCodes#larval-dip-count
* subject = Reference(example-site-c1)
* effectiveDateTime = "2026-09-20T09:00:00Z"
* performer = Reference(example-observer)
* valueQuantity = 12 $ucum#1 "larvae"
* component[0].code = AquaSentinelCodes#dip-count
* component[=].valueQuantity = 4 $ucum#1 "larvae"
* component[+].code = AquaSentinelCodes#dip-count
* component[=].valueQuantity = 3 $ucum#1 "larvae"
* component[+].code = AquaSentinelCodes#dip-count
* component[=].valueQuantity = 2 $ucum#1 "larvae"
* component[+].code = AquaSentinelCodes#dip-count
* component[=].valueQuantity = 2 $ucum#1 "larvae"
* component[+].code = AquaSentinelCodes#dip-count
* component[=].valueQuantity = 1 $ucum#1 "larvae"
* component[+].code = AquaSentinelCodes#ai-suggestion
* component[=].valueCodeableConcept = AquaSentinelCodes#larvae_present
* component[+].code = AquaSentinelCodes#ai-confidence
* component[=].valueQuantity = 0.82 $ucum#1
* component[+].code = AquaSentinelCodes#ai-provider
* component[=].valueString = "mock"
* component[+].code = AquaSentinelCodes#citizen-decision
* component[=].valueCodeableConcept = AquaSentinelCodes#confirmed
* note.text = "AI suggestion (mock, confidence 0.82): larvae_present. Dark wriggling shapes near the surface of the cup. Citizen decision: confirmed."

Instance: example-amphibian-preliminary
InstanceOf: AquaSentinelCitizenFinding
Title: "Amphibian candidate, preliminary"
Description: "The AI suggested a marsh frog; the citizen changed it to Perez's frog. Awaiting reliability weighting, so preliminary."
* insert Narrative(Amphibian candidate preliminary)
* insert Synthetic
* identifier.system = $sid-finding
* identifier.value = "102"
* status = #preliminary
* code.coding[0] = $oah#amphibians "Amphibians"
* code.coding[+] = AquaSentinelCodes#predator-photo
* subject = Reference(example-site-c1)
* effectiveDateTime = "2026-09-20T09:00:00Z"
* performer = Reference(example-observer)
* valueCodeableConcept.text = "Pelophylax perezi"
* component[0].code = AquaSentinelCodes#ai-suggestion
* component[=].valueCodeableConcept.text = "Pelophylax ridibundus"
* component[+].code = AquaSentinelCodes#ai-confidence
* component[=].valueQuantity = 0.55 $ucum#1
* component[+].code = AquaSentinelCodes#ai-provider
* component[=].valueString = "mock"
* component[+].code = AquaSentinelCodes#citizen-decision
* component[=].valueCodeableConcept = AquaSentinelCodes#corrected
* note.text = "AI suggestion (mock, confidence 0.55): Pelophylax ridibundus. Green frog on the bank. Citizen decision: corrected."

Instance: example-flow-final
InstanceOf: AquaSentinelIndicatorFinding
Title: "Stream check flow types, promoted to final (OAH hydrology)"
* insert Narrative(Stream check flow types promoted to final OAH hydrology)
* insert Synthetic
* status = #final
* code = $oah#hydrology "Hydrology of the stream"
* subject = Reference(example-site-c1)
* effectiveDateTime = "2026-09-20T09:00:00Z"
* performer = Reference(example-observer)
* component[0].code = AquaSentinelStreamCheckQuestions#flow_NP
* component[=].valueCodeableConcept = $oah#extensive "Extensive"
* component[+].code = AquaSentinelStreamCheckQuestions#flow_RU
* component[=].valueCodeableConcept = $oah#absent "Absent"
* component[+].code = AquaSentinelStreamCheckQuestions#barriers
* component[=].valueQuantity = 1 $ucum#1

Instance: example-macrophytes-final
InstanceOf: AquaSentinelVegetationFinding
Title: "Free-floating macrophytes, promoted to final (OAH macrophytes)"
* insert Narrative(Free-floating macrophytes promoted to final OAH macrophytes)
* insert Synthetic
* status = #final
* code = $oah#macrophytes "Macrophytes"
* subject = Reference(example-site-c1)
* effectiveDateTime = "2026-09-20T09:00:00Z"
* performer = Reference(example-observer)
* component[macrophytes].code = $oah#free-floating "Free-floating"
* component[macrophytes].valueCodeableConcept = $oah#present "Present"

Instance: example-riparian-final
InstanceOf: AquaSentinelVegetationFinding
Title: "Riparian trees cover, promoted to final (OAH riparianVegetation)"
* insert Narrative(Riparian trees cover promoted to final OAH riparianVegetation)
* insert Synthetic
* status = #final
* code = $oah#riparianVegetation "Riparian vegetation"
* subject = Reference(example-site-c1)
* effectiveDateTime = "2026-09-20T09:00:00Z"
* performer = Reference(example-observer)
* component[riparianVegetation].code = $oah#trees "Trees (height >3m)"
* component[riparianVegetation].valueCodeableConcept = $oah#21-40-percent "21-40%"

Instance: example-dead-bird
InstanceOf: AquaSentinelDeadBirdReport
Title: "Dead bird report"
Description: "Two dead birds seen near the stream. Count, place and time only."
* insert Narrative(Dead bird report)
* insert Synthetic
* status = #preliminary
* code = AquaSentinelCodes#dead-bird-report
* subject = Reference(example-site-c1)
* effectiveDateTime = "2026-09-20T09:00:00Z"
* performer = Reference(example-observer)
* valueQuantity = 2 $ucum#1 "birds"
* note.text = "Report only: count, place and time. No diagnosis or cause of death is made. The volunteer was told not to touch the birds."

Instance: example-risk-index
InstanceOf: AquaSentinelRiskIndex
Title: "Vector-habitat risk index, site C1, week 2026-W38"
* insert Narrative(Vector-habitat risk index site C1 week 2026-W38)
* insert Synthetic
* status = #preliminary
* code = AquaSentinelCodes#vector-habitat-risk-index
* subject = Reference(example-site-c1)
* effectivePeriod.start = "2026-09-07"
* effectivePeriod.end = "2026-09-20"
* performer = Reference(example-city-co)
* device = Reference(example-risk-engine)
* valueQuantity = 0.62 $ucum#1
* component[0].code = AquaSentinelCodes#risk-band
* component[=].valueCodeableConcept = AquaSentinelCodes#high
* component[+].code = AquaSentinelCodes#vector_presence
* component[=].valueQuantity = 0.8 $ucum#1
* component[+].code = AquaSentinelCodes#temperature
* component[=].dataAbsentReason = $data-absent-reason#not-asked
* component[+].code = AquaSentinelCodes#index-range-low
* component[=].valueQuantity = 0.5 $ucum#1
* component[+].code = AquaSentinelCodes#index-range-high
* component[=].valueQuantity = 0.7 $ucum#1
* note.text = "Index 0.62 (high). Describes conditions that favour mosquito vectors, never infection status."

Instance: example-provenance
InstanceOf: AquaSentinelObserverProvenance
Title: "Provenance of a check-in with observer reliability"
* insert Narrative(Provenance of a check-in with observer reliability)
* insert Synthetic
* target[0] = Reference(example-larval-dips-final)
* target[+] = Reference(example-amphibian-preliminary)
* target[+] = Reference(example-dead-bird)
* recorded = "2026-09-20T09:05:00Z"
* location = Reference(example-site-c1)
* agent.type = $provenance-participant-type#author
* agent.who = Reference(example-observer)
* agent.extension[reliability].extension[dawidSkene].valueDecimal = 0.86
* agent.extension[reliability].extension[calibrationTier].valueCoding = AquaSentinelCodes#calibrated
* agent.extension[reliability].extension[calibrationKappa].valueDecimal = 0.71
* agent.extension[reliability].extension[method].valueString = "MAP Dawid-Skene over the city's stream checks in a 14-day window, seeded with calibration agreement"

Instance: example-action-vector-control
InstanceOf: AquaSentinelActionRequest
Title: "Approved verification visit"
* insert Narrative(Approved verification visit)
* insert Synthetic
* identifier.system = $sid-action
* identifier.value = "1"
* status = #active
* intent = #order
* category = AquaSentinelCodes#vector-control-visit
* code.text = "Verification visit: check standing water and larval habitat"
* subject = Reference(example-site-c1)
* requester = Reference(example-city-co)
* authoredOn = "2026-09-21T10:00:00Z"
* reasonReference = Reference(example-risk-index)
* note.text = "Drafted from the dominant driver vector_presence and approved by a city officer."

Instance: example-action-sewage
InstanceOf: AquaSentinelActionRequest
Title: "Approved sewage inspection"
* insert Narrative(Approved sewage inspection)
* insert Synthetic
* status = #active
* intent = #order
* category = AquaSentinelCodes#sewage-inspection
* code.text = "Inspect outflows for sewage"
* subject = Reference(example-site-c1)
* requester = Reference(example-city-co)
* authoredOn = "2026-09-21T10:00:00Z"

Instance: example-action-veterinary
InstanceOf: AquaSentinelActionRequest
Title: "Approved veterinary notification"
* insert Narrative(Approved veterinary notification)
* insert Synthetic
* status = #active
* intent = #order
* category = AquaSentinelCodes#veterinary-notification
* code.text = "Notify veterinary services of a dead bird report"
* subject = Reference(example-site-c1)
* requester = Reference(example-city-co)
* authoredOn = "2026-09-21T10:00:00Z"
* supportingInfo = Reference(example-dead-bird)
* note.text = "Routing only. No diagnosis is made or implied. Do not touch dead birds."

Instance: example-message
InstanceOf: AquaSentinelVolunteerMessage
Title: "Feedback to a volunteer"
* insert Narrative(Feedback to a volunteer)
* insert Synthetic
* status = #completed
* category = AquaSentinelCodes#action_taken
* recipient = Reference(example-observer)
* sent = "2026-09-21T10:01:00Z"
* about = Reference(example-action-vector-control)
* payload.contentString = "Your observation led to an action: Verification visit: check standing water and larval habitat."

Instance: example-city-week
InstanceOf: AquaSentinelCityWeekReport
Title: "Coimbra, week 2026-W38"
* insert Narrative(Coimbra week 2026-W38)
* insert Synthetic
* status = #complete
* type = #summary
* measure = "http://example.org/fhir/aquasentinel/Measure/aquasentinel-vector-habitat-risk-week"
* date = "2026-09-21T10:00:00Z"
* period.start = "2026-09-14"
* period.end = "2026-09-20"
* reporter = Reference(example-city-co)
* group[0].code = AquaSentinelCodes#sites-assessed
* group[=].measureScore = 1 $ucum#1
* group[+].code = AquaSentinelCodes#sites-alert
* group[=].measureScore = 1 $ucum#1
* group[+].code = AquaSentinelCodes#sites-needing-data
* group[=].measureScore = 0 $ucum#1
* group[+].code = AquaSentinelCodes#vector-habitat-risk-index
* group[=].measureScore = 0.62 $ucum#1
* group[=].stratifier[0].code = AquaSentinelCodes#site
* group[=].stratifier[0].stratum[0].value.text = "C1"
* group[=].stratifier[0].stratum[0].measureScore = 0.62 $ucum#1
* evaluatedResource = Reference(example-risk-index)
