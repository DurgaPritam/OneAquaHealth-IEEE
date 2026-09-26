# Demo video script (about 4 minutes)

Record the static demo (https://durgapritam.github.io/OneAquaHealth-IEEE/) or `npm run dev`. Use a phone-sized browser window for the citizen part and a desktop window for the city part. Press **Reset demo** in the purple banner before recording.

Say "synthetic" whenever synthetic data is on screen. The purple banner and badges show it too.

## 1. Problem (30 s)

Screen: home page on a phone.

> "The OneAquaHealth Policy Brief found that urban streams host mosquitoes able to carry West Nile virus, dengue and chikungunya, and that degraded streams lose the frogs, birds and fish that eat them. It asks cities to bring Diptera monitoring into public health surveillance. Research traps run a few nights a year. AquaSentinel turns citizen stream checks into an early-warning loop that a city can act on."

Point at the four promises: AI only suggests, an officer approves every action, no diagnosis, anonymous volunteers.

## 2. Citizen check-in with AI confirmation (60 s)

1. **Stream check** → choose **Estação Cbr-B (C2)** from the list (the map shows the same sites).
2. Stream step: "These are the OneAquaHealth field form questions, field for field." Set **Still water** to *Extensive* and **Sewage smell** to *Extensive*.
3. Larvae step: point at the dip illustration. Enter **60** for dip 1. Add the cup photo (`web/scripts/sample-cup.jpg`).
4. The **AI suggestion chip** appears with its confidence and one-line reason, plus the **Demo AI (mock)** badge. If an out-of-list label appears, it sits in a "removed" box: "that is the validation gate". Press **Change** and pick the right answer: "the AI suggested, I decided; both are stored".
5. Choose **Hanging at an angle**: the guided key says Culex-type or Aedes-type, "a type, never a species".
6. Predators: frogs **None**. Point at "all amphibians are protected".
7. Dead birds: show the red **Do not touch** box. Choose **Yes**.
8. Review, tick consent, **Send check-in**.

## 3. Calibration (30 s)

**Practice** → answer three or four drawings quickly, deliberately rating the mossy concrete bank (rs02) as natural → **See my results**.

> "Kappa per question, a tier, and plain-language feedback: 'you tend to rate banks as natural when hard revetment is visible'. The drawings are generated from their answers, so no AI labelled them. Tiers feed a Dawid-Skene model that weights each volunteer's answers."

Mention the simulation result: plain Dawid-Skene loses to majority vote on small panels; with calibration priors it wins by up to 10 points (simulated).

## 4. Risk explanation (30 s)

Desktop, **City view**, Coimbra.

> "Seasonal suitability from real Open-Meteo weather, times site conditions from volunteer evidence."

Point at C2: it now shows **Alert**. Click it: every factor with value, weight, share and a sentence, the Dawid-Skene posterior behind it, the check-in ids, the weekly trend and the config fingerprint. Point at a **Needs a stream check** site (C12): "too little data never alerts".

## 5. Officer approval and volunteer message (30 s)

1. **Check for new alerts** → drafts appear. Nothing has been sent.
2. On the C1 card press **Change measure** → *Retention ponds*: a **Mosquito warning from the Catalogue** appears. "The OAH Catalogue itself warns this can create larval habitat."
3. Enter `officer:CO-01`, approve the C2 action, and note "3 volunteer messages sent".
4. Phone, **My impact**: "Your observation at Estação Cbr-B led to an action". Show the campaign list and the team leaderboard: "points for quality, not volume".

## 6. FHIR validation (20 s)

Terminal or `docs/evidence/validation-summary.md`:

> "Every record maps to FHIR R4 on the OneAquaHealth implementation guide: Observations with OAH indicator codes, Location, a pseudonymous Practitioner, Provenance with reliability, ServiceRequest only after approval, Communication and MeasureReport. The HL7 validator gives zero errors on valid records, and every deliberately broken record fails."

## 7. Evidence and limits (20 s)

Show `eval/reports/backtest.md`.

> "We pre-registered a backtest against ECDC West Nile data. The weather part signalled before the first human case in 118 of 119 region-seasons, a median of 8 weeks ahead. It also fired in 24 of 25 control regions. So weather tells you when, not where. That is exactly why citizen site evidence matters. All volunteer data in this demo is synthetic; the claims and their limits are listed in docs/CLAIMS.md."
