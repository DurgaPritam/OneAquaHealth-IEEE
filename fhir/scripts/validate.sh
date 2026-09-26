#!/usr/bin/env bash
# npm run validate
#   1. prepare the HL7 validator and the locally built OAH IG package (fhir/scripts/setup_oah.sh)
#   2. build our profiles and examples with SUSHI
#   3. export a synthetic lifecycle with the Python exporter (fhir/scripts/generate_lifecycle.py)
#   4. validate every example, the generated bundles and the negative records in one validator run
#   5. write docs/evidence/validation-summary.md; exit 1 unless valid records have 0 errors
#      and every negative record fails as expected
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON=python3
OUT="fhir/output"
SUMMARY="docs/evidence/validation-summary.md"
OAH_PKG="hl7.eu.fhir.oah#0.1.0-ci-build"

bash fhir/scripts/setup_oah.sh

echo "[validate] SUSHI build of fhir/"
mkdir -p "$OUT"
npx --no-install sushi build fhir > "$OUT/sushi.log" 2>&1 || { cat "$OUT/sushi.log"; exit 1; }
grep -E "Errors|Warnings" "$OUT/sushi.log" | tail -1

echo "[validate] exporting a synthetic lifecycle"
"$PYTHON" fhir/scripts/generate_lifecycle.py --out "$OUT/generated"
mkdir -p docs/evidence/fhir
cp "$OUT"/generated/*.json docs/evidence/fhir/

RES="fhir/fsh-generated/resources"
FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <(ls "$RES"/*.json | grep -vE '/(StructureDefinition|ValueSet|CodeSystem)-')
FILES+=("$OUT"/generated/*.json)
FILES+=(fhir/negative/*.json)
VALIDATE=()
for f in "${FILES[@]}"; do [ "$(basename "$f")" = "manifest.json" ] || VALIDATE+=("$f"); done

echo "[validate] HL7 validator on ${#VALIDATE[@]} files"
# -tx n/a: no terminology server, so the run is reproducible offline (UCUM codes are reported as not checked).
# -allow-example-urls: our canonical and identifier systems sit on the reserved example.org domain (fhir/README.md).
java -jar tools/validator_cli.jar -version 4.0.1 -tx n/a -allow-example-urls true \
  -ig "$OAH_PKG" -ig "$RES" -output "$OUT/validation.json" "${VALIDATE[@]}" > "$OUT/validator.log" 2>&1 || true
[ -s "$OUT/validation.json" ] || { tail -40 "$OUT/validator.log"; echo "validator produced no output"; exit 1; }

SUSHI_VERSION="$(npx --no-install sushi --version 2>/dev/null | head -1)"
VALIDATOR_LINE="$(grep -m1 'FHIR Validation tool' "$OUT/validator.log" || echo "validator $(cat tools/validator_cli.version)")"
OAH_COMMIT="$(git -C fhir/.oah-ig rev-parse HEAD)"
"$PYTHON" fhir/scripts/summarise_validation.py "$OUT/validation.json" "$SUMMARY" \
  --meta "HL7 validator=$VALIDATOR_LINE" \
  --meta "SUSHI=$SUSHI_VERSION" \
  --meta "Java=$(java -version 2>&1 | head -1)" \
  --meta "FHIR version=4.0.1" \
  --meta "OAH IG=https://github.com/hl7-eu/oah at commit $OAH_COMMIT, built locally as $OAH_PKG (CI build not published, OQ-2)" \
  --meta "Our profiles=fhir/input/fsh (canonical http://example.org/fhir/aquasentinel)" \
  --meta "Validator options=-tx n/a -allow-example-urls true -ig $OAH_PKG -ig $RES" \
  --meta "Generated lifecycle=fhir/scripts/generate_lifecycle.py (synthetic Coimbra season from api.seed, weather off)" \
  > "$OUT/summary.txt" && status=0 || status=$?
cat "$OUT/summary.txt" | sed -n '/## Result/,/## Valid records/p'
echo "[validate] summary written to $SUMMARY"
exit $status
