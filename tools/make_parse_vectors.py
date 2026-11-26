#!/usr/bin/env python3
"""Builds conformance/parse/sequence.json from the reference decoder's JSON
output of whole recordings (tools/reference, run with --output-mpdus and
HFDL_SAMPLE_CLOCK_BASE=0; see conformance/README.md).

    python3 tools/make_parse_vectors.py NAME=PATH.json[@START_EPOCH] ...

Each recording becomes one case: the good frames in the order the reference
parsed them, and every message it produced (F-H19).
"""
import json
import sys
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent
RATES = {(300, "S"): 0, (600, "S"): 1, (1200, "S"): 2, (1800, "S"): 3,
         (300, "D"): 4, (600, "D"): 5, (1200, "D"): 6, (1800, "D"): 7}


def strip_raw(o):
    if isinstance(o, dict):
        return {k: strip_raw(v) for k, v in o.items() if k != "raw"}
    if isinstance(o, list):
        return [strip_raw(v) for v in o]
    return o


def case(name, path):
    path, _, base = path.partition("@")
    base = float(base or 0)
    frames, msgs = [], []
    for line in open(path):
        h = json.loads(line)["hfdl"]
        t = h["t"]["sec"] + h["t"]["usec"] / 1e6 - base
        if "mpdu" in h or "spdu" in h:
            key = "mpdu" if "mpdu" in h else "spdu"
            frames.append({"n": len(frames), "freq_khz": h["freq"] // 1000, "t": round(t, 3),
                           "m1": RATES[(h["bit_rate"], h["slot"])], "octets": h[key]["raw"]})
            if key == "spdu":
                msgs.append({"frame": len(frames) - 1, "spdu": strip_raw(h["spdu"])})
        elif "lpdu" in h:
            msgs.append({"frame": len(frames) - 1, "lpdu": strip_raw(h["lpdu"])})
    return {"id": name, "source": "real-recording",
            "description": f"every good frame of the recording {name}, in the order the reference parsed them, and the messages",
            "input": {"frames": frames},
            "expected": {"messages": msgs},
            "req": ["PAR-01", "PAR-02", "PAR-04", "PAR-05"]}


def main():
    cases = [case(*a.split("=", 1)) for a in sys.argv[1:]]
    suite = {
        "suite": "parse-sequence", "normative": True,
        "description": "Frames (octets as the frame decoder gives them, padding included) parsed in order by one parser (spec/04-algorithms/03-parser.md) -> the messages, as trees in the vocabulary of the reference's JSON output (F-H19).",
        "compare": {"method": "per message, every key of expected must be present with an equal value; keys not in expected are ignored; the keys in non_normative_keys (display wording) are not compared",
                    "non_normative_keys": ["name", "descr", "type.name"], "float_abs_tolerance": 1e-6,
                    "time": "t is seconds from the recording's first sample; reassembly and AC ID timeouts use it"},
        "cases": cases}
    out = SEED / "conformance/parse/sequence.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(suite, separators=(",", ":")) + "\n")
    for c in cases:
        print(c["id"], len(c["input"]["frames"]), "frames,", len(c["expected"]["messages"]), "messages")


if __name__ == "__main__":
    main()
