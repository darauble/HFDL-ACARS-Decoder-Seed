#!/usr/bin/env python3
"""Writes conformance/manifest.json: every suite file with its case count."""
import json
from pathlib import Path

C = Path(__file__).resolve().parent.parent / "conformance"


def main():
    real = json.loads((C / "iq/real.json").read_text())
    real.update({"suite": "iq-decode", "normative": True,
                 "description": "Excerpts of real recordings -> the frames found (README.md rule 5: required frames must be found).",
                 "compare": {"method": "README.md rule 5", "time_tolerance_s": 0.5}})
    real = {k: real[k] for k in ("suite", "normative", "description", "compare", "cases")}
    (C / "iq/real.json").write_text(json.dumps(real, indent=1) + "\n")
    syn = json.loads((C / "iq/synthetic.json").read_text())
    syn.update({"suite": "iq-decode", "normative": True,
                "description": "Synthetic recordings (tools/hfdl_tx.py) -> the frames sent; every frame required.",
                "compare": {"method": "README.md rule 5", "time_tolerance_s": 0.5}})
    syn = {k: syn[k] for k in ("suite", "normative", "description", "compare", "cases")}
    (C / "iq/synthetic.json").write_text(json.dumps(syn, indent=1) + "\n")
    suites = []
    for f in sorted(C.rglob("*.json")):
        if f.name == "manifest.json":
            continue
        d = json.loads(f.read_text())
        suites.append({"file": str(f.relative_to(C)), "suite": d.get("suite"), "normative": d.get("normative", True),
                       "cases": len(d["cases"])})
    (C / "manifest.json").write_text(json.dumps({"conformance_format": 1, "suites": suites}, indent=2) + "\n")
    for s in suites:
        print(f"{s['file']:34s} {s['suite']:16s} {s['cases']}")


if __name__ == "__main__":
    main()
