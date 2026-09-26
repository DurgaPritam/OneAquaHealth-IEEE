"""Turn the SUSHI output of the OAH IG into a local FHIR package.

The OAH IG (https://github.com/hl7-eu/oah) has no published package: its CI
build on build.fhir.org returns 404 (see docs/OPEN_QUESTIONS.md, OQ-2). This
script copies the conformance resources that SUSHI generated from the pinned
commit (StructureDefinition, CodeSystem, ValueSet) into a package folder and,
optionally, into the local FHIR package cache (~/.fhir/packages) so that both
SUSHI (for our profiles that derive from OAH profiles) and the HL7 validator
can resolve ``hl7.eu.fhir.oah#0.1.0-ci-build`` without network access.

SUSHI emits differential-only StructureDefinitions, but SUSHI itself needs
snapshots to derive from them. fhir/scripts/setup_oah.sh therefore asks the HL7
validator to generate the snapshots and passes them back with --snapshots.

Usage: python fhir/scripts/build_oah_package.py <oah-ig-dir> <out-dir> [--snapshots DIR] [--install]
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PACKAGE_ID = "hl7.eu.fhir.oah"
CONFORMANCE = ("StructureDefinition", "CodeSystem", "ValueSet")


def read_config(oah_dir: Path) -> dict[str, str]:
    """Pick id, version, canonical and FHIR version out of sushi-config.yaml without a YAML parser."""
    wanted = {"id", "version", "canonical", "fhirVersion"}
    out: dict[str, str] = {}
    for line in (oah_dir / "sushi-config.yaml").read_text(encoding="utf-8").splitlines():
        if ":" not in line or line.startswith((" ", "\t", "#")):
            continue
        key, value = line.split(":", 1)
        if key in wanted and key not in out:
            out[key] = value.split("#", 1)[0].strip()
    return out


def build(oah_dir: Path, out_dir: Path) -> Path:
    cfg = read_config(oah_dir)
    if cfg.get("id") != PACKAGE_ID:
        raise SystemExit(f"unexpected package id {cfg.get('id')!r} in {oah_dir}")
    resources = oah_dir / "fsh-generated" / "resources"
    pkg = out_dir / "package"
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)
    files = []
    for f in sorted(resources.glob("*.json")):
        res = json.loads(f.read_text(encoding="utf-8"))
        if res.get("resourceType") in CONFORMANCE:
            shutil.copy(f, pkg / f.name)
            files.append({"filename": f.name, "resourceType": res["resourceType"], "id": res.get("id"),
                          "url": res.get("url"), "version": res.get("version"), "kind": res.get("kind"),
                          "type": res.get("type")})
    manifest = {
        "name": PACKAGE_ID,
        "version": cfg["version"],
        "canonical": cfg["canonical"],
        "url": cfg["canonical"],
        "type": "IG",
        "fhirVersions": [cfg["fhirVersion"]],
        "dependencies": {"hl7.fhir.r4.core": "4.0.1", "hl7.fhir.uv.xver-r5.r4": "0.1.0"},
        "description": "Local build of the OAH IG from source by AquaSentinel (not an official release).",
    }
    (pkg / "package.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (pkg / ".index.json").write_text(json.dumps({"index-version": 1, "files": files}, indent=2), encoding="utf-8")
    print(f"OAH package {PACKAGE_ID}#{cfg['version']}: {len(files)} conformance resources in {pkg}")
    return out_dir


def merge_snapshots(out_dir: Path, snap_dir: Path) -> int:
    """Replace each StructureDefinition in the package with its validator-generated snapshot version."""
    pkg = out_dir / "package"
    n = 0
    for f in sorted(pkg.glob("StructureDefinition-*.json")):
        snap = snap_dir / f"{f.name}.snapshot.json"
        if not snap.exists():
            raise SystemExit(f"missing snapshot for {f.name} in {snap_dir}")
        res = json.loads(snap.read_text(encoding="utf-8"))
        if not res.get("snapshot", {}).get("element"):
            raise SystemExit(f"snapshot for {f.name} is empty")
        f.write_text(json.dumps(res, indent=2), encoding="utf-8")
        n += 1
    print(f"merged {n} snapshots into {pkg}")
    return n


def install(out_dir: Path, version: str) -> Path:
    target = Path.home() / ".fhir" / "packages" / f"{PACKAGE_ID}#{version}"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(out_dir, target)
    print(f"installed into FHIR package cache: {target}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("oah_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--snapshots", type=Path, help="folder with <file>.snapshot.json from the validator")
    parser.add_argument("--no-build", action="store_true", help="reuse the package folder already in out_dir")
    parser.add_argument("--install", action="store_true", help="copy into ~/.fhir/packages")
    args = parser.parse_args()
    if not args.no_build:
        build(args.oah_dir, args.out_dir)
    if args.snapshots:
        merge_snapshots(args.out_dir, args.snapshots)
    if args.install:
        install(args.out_dir, read_config(args.oah_dir)["version"])


if __name__ == "__main__":
    main()
