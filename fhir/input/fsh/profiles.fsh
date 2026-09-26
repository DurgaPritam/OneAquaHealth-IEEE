// ------------------------------------------------------------------ invariants

Invariant: as-observer-code
Description: "The observer identifier is a random pseudonymous code of the form OBS-XXXXXX."
Expression: "value.matches('^OBS-[A-Z0-9]{6}$')"
Severity: #error

Invariant: as-dead-bird-no-diagnosis
Description: "A dead bird report carries a note stating that no diagnosis is made."
Expression: "note.where(text.contains('No diagnosis')).exists()"
Severity: #error

Invariant: as-oah-code
Description: "The code carries an OAH TemporaryOahSystem indicator coding."
Expression: "coding.where(system = 'http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu').exists()"
Severity: #error

Invariant: as-unit-interval
Description: "Reliability and kappa-derived scores lie in [-1, 1] and reliability in [0, 1]."
Expression: "(extension('dawidSkene').value as decimal).empty() or ((extension('dawidSkene').value as decimal) >= 0 and (extension('dawidSkene').value as decimal) <= 1)"
Severity: #error

// ------------------------------------------------------------------ extension

Extension: ObserverReliability
Id: observer-reliability
Title: "Observer reliability"
Description: "Reliability of a pseudonymous observer at the time of export: the Dawid-Skene reliability estimated across the city's stream checks and the calibration tier and kappa from the practice round. It weights evidence; it is never a judgement of the person."
Context: Provenance.agent
* obeys as-unit-interval
* extension contains
    dawidSkene 0..1 and
    calibrationTier 1..1 and
    calibrationKappa 0..1 and
    method 0..1
* extension[dawidSkene] ^short = "Dawid-Skene reliability, 0 to 1 (absent if the observer has no stream-check answers in the window)"
* extension[dawidSkene].value[x] only decimal
* extension[calibrationTier] ^short = "Calibration tier: new, calibrated or trusted"
* extension[calibrationTier].value[x] only Coding
* extension[calibrationTier].valueCoding from AquaSentinelCalibrationTierVS (required)
* extension[calibrationKappa] ^short = "Overall Cohen kappa in the calibration round"
* extension[calibrationKappa].value[x] only decimal
* extension[method] ^short = "How the reliability was estimated"
* extension[method].value[x] only string

// ------------------------------------------------------------------ people and places

Profile: AquaSentinelObserver
Parent: Practitioner
Id: aquasentinel-observer
Title: "AquaSentinel pseudonymous observer"
Description: "A citizen volunteer known only by a random code. No name, contact details, address, photo, gender or birth date is ever recorded."
* identifier 1..1
* identifier obeys as-observer-code
* identifier.system 1..1
* identifier.system = "http://example.org/fhir/aquasentinel/sid/observer-code" (exactly)
* identifier.value 1..1
* identifier.assigner 0..0
* name 0..0
* telecom 0..0
* address 0..0
* gender 0..0
* birthDate 0..0
* photo 0..0
* qualification 0..0
* communication 0..0

Profile: AquaSentinelSite
Parent: LocationOah
Id: aquasentinel-site
Title: "AquaSentinel stream site"
Description: "A OneAquaHealth research site from the ENORA sites API, identified by its site code. Coordinates are rounded to about 100 m."
* identifier 1..1
* identifier.system 1..1
* identifier.system = "http://example.org/fhir/aquasentinel/sid/enora-site-code" (exactly)
* identifier.value 1..1
* position 1..1
* telecom 0..0

// ------------------------------------------------------------------ citizen findings

Profile: AquaSentinelCitizenFinding
Parent: Observation
Id: aquasentinel-citizen-finding
Title: "AquaSentinel citizen finding"
Description: "A citizen finding at a stream site. Findings start as preliminary; after citizen confirmation and reliability weighting a finding with an OAH indicator code is exported as final under AquaSentinelIndicatorFinding instead. When an AI suggested a label, the citizen's answer is the value and the AI suggestion, confidence and provider are components."
* status from AquaSentinelFindingStatusVS (required)
* code 1..1
* code.coding 1..*
* subject 1..1
* subject only Reference(AquaSentinelSite)
* effective[x] 1..1
* effective[x] only dateTime
* performer 1..1
* performer only Reference(AquaSentinelObserver)
* value[x] only CodeableConcept or Quantity
* interpretation 0..0
* specimen 0..0
* component.code.coding 1..*

Profile: AquaSentinelIndicatorFinding
Parent: ObservationIndicatorsOah
Id: aquasentinel-indicator-finding
Title: "AquaSentinel promoted OAH indicator finding"
Description: "A citizen finding promoted to final after citizen confirmation and reliability weighting, conforming to the OAH ObservationIndicatorsOah profile."
* code from AquaSentinelOahIndicatorVS (required)
* code obeys as-oah-code
* subject 1..1
* subject only Reference(AquaSentinelSite)
* effective[x] only dateTime
* performer 1..1
* performer only Reference(AquaSentinelObserver)
* interpretation 0..0

Profile: AquaSentinelVegetationFinding
Parent: ObservationWithCompOah
Id: aquasentinel-vegetation-finding
Title: "AquaSentinel promoted vegetation finding"
Description: "A promoted macrophyte or riparian vegetation answer from the stream check (sections 4a and 4b), conforming to the OAH ObservationWithCompOah profile. One Observation per answer, because each OAH component slice allows one entry."
* subject 1..1
* subject only Reference(AquaSentinelSite)
* effective[x] only dateTime
* performer 1..1
* performer only Reference(AquaSentinelObserver)
* interpretation 0..0

Profile: AquaSentinelDeadBirdReport
Parent: Observation
Id: aquasentinel-dead-bird-report
Title: "AquaSentinel dead bird report"
Description: "Dead birds seen near a stream: count, place and time only. No identification, cause of death, interpretation or diagnosis is recorded. Routed to veterinary teams, never diagnosed."
* status from AquaSentinelFindingStatusVS (required)
* code = AquaSentinelCodes#dead-bird-report
* subject 1..1
* subject only Reference(AquaSentinelSite)
* effective[x] 1..1
* effective[x] only dateTime
* performer 1..1
* performer only Reference(AquaSentinelObserver)
* value[x] 1..1
* value[x] only Quantity
* valueQuantity.value 1..1
* interpretation 0..0
* dataAbsentReason 0..0
* bodySite 0..0
* method 0..0
* specimen 0..0
* device 0..0
* referenceRange 0..0
* hasMember 0..0
* derivedFrom 0..0
* component 0..0
* note 1..*
* obeys as-dead-bird-no-diagnosis

// ------------------------------------------------------------------ risk, reliability, action

Profile: AquaSentinelRiskIndex
Parent: Observation
Id: aquasentinel-vector-habitat-risk-index
Title: "AquaSentinel vector-habitat risk index"
Description: "Weekly index of conditions that favour mosquito vectors at a stream site, with every factor as a component. A screening estimate for officer review, so it is always preliminary. It describes habitat, never infection status."
* status = #preliminary
* code = AquaSentinelCodes#vector-habitat-risk-index
* subject 1..1
* subject only Reference(AquaSentinelSite)
* effective[x] 1..1
* effective[x] only Period
* value[x] 1..1
* value[x] only Quantity
* interpretation 0..0
* component 1..*
* component.code.coding 1..*
* note 1..*

Profile: AquaSentinelObserverProvenance
Parent: Provenance
Id: aquasentinel-observer-provenance
Title: "AquaSentinel observer provenance"
Description: "Who made the findings of one check-in and how reliable their reports were at export time."
* target 1..*
* target only Reference(Observation)
* location 1..1
* location only Reference(AquaSentinelSite)
* agent 1..1
* agent.who only Reference(AquaSentinelObserver)
* agent.extension contains ObserverReliability named reliability 1..1

Profile: AquaSentinelActionRequest
Parent: ServiceRequest
Id: aquasentinel-action-request
Title: "AquaSentinel approved action"
Description: "An action a city officer approved from a drafted alert. Never issued automatically. A veterinary notification routes a dead bird report; it is not a veterinary order and implies no diagnosis."
* status from AquaSentinelActionStatusVS (required)
* intent = #order
* category 1..1
* category from AquaSentinelActionCategoryVS (required)
* code 1..1
* subject 1..1
* subject only Reference(AquaSentinelSite)
* requester 1..1
* requester only Reference(Organization)
* authoredOn 1..1
* reasonReference only Reference(Observation)

Profile: AquaSentinelVolunteerMessage
Parent: Communication
Id: aquasentinel-volunteer-message
Title: "AquaSentinel volunteer feedback message"
Description: "Feedback to a pseudonymous volunteer whose report helped raise an alert or led to an action."
* status = #completed
* category 1..1
* category from AquaSentinelMessageKindVS (required)
* subject 0..0
* recipient 1..1
* recipient only Reference(AquaSentinelObserver)
* sent 1..1
* payload 1..1
* payload.content[x] only string

Profile: AquaSentinelCityWeekReport
Parent: MeasureReport
Id: aquasentinel-city-week-report
Title: "AquaSentinel weekly city summary"
Description: "Weekly summary of the vector-habitat risk index across a city's stream sites."
* status = #complete
* type = #summary
* measure = "http://example.org/fhir/aquasentinel/Measure/aquasentinel-vector-habitat-risk-week" (exactly)
* period.start 1..1
* period.end 1..1
* reporter 1..1
* reporter only Reference(Organization)
* group 1..*
* group.code 1..1
