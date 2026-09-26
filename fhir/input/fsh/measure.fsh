Instance: aquasentinel-vector-habitat-risk-week
InstanceOf: Measure
Usage: #definition
Title: "AquaSentinel weekly vector-habitat risk summary"
Description: "Weekly count of a city's stream sites by vector-habitat risk index, with the index of each site as a stratum. Describes conditions that favour mosquito vectors, never infection."
* text.status = #generated
* text.div = "<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>AquaSentinel weekly vector-habitat risk summary.</p></div>"
* url = "http://example.org/fhir/aquasentinel/Measure/aquasentinel-vector-habitat-risk-week"
* version = "0.1.0"
* name = "AquaSentinelVectorHabitatRiskWeek"
* title = "AquaSentinel weekly vector-habitat risk summary"
* status = #draft
* experimental = true
* description = "Weekly count of a city's stream sites by vector-habitat risk index, with the index of each site as a stratum. The index is defined in docs/RISK_MODEL.md of the AquaSentinel repository."
* scoring = $measure-scoring#continuous-variable
* group[0].code = AquaSentinelCodes#sites-assessed
* group[0].description = "Number of sites with a risk score this week."
* group[1].code = AquaSentinelCodes#sites-alert
* group[1].description = "Number of sites at or above the alert threshold with enough site data."
* group[2].code = AquaSentinelCodes#sites-needing-data
* group[2].description = "Number of sites whose site data coverage is too low to raise an alert."
* group[3].code = AquaSentinelCodes#vector-habitat-risk-index
* group[3].description = "Vector-habitat risk index per site, one stratum per site."
* group[3].stratifier[0].code = AquaSentinelCodes#site
