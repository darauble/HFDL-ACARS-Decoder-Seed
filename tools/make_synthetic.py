#!/usr/bin/env python3
"""Builds the synthetic vectors: conformance/frame/decode.json (data symbols ->
octets) and conformance/iq/synth-*.wav with conformance/iq/synthetic.json.

    python3 tools/make_synthetic.py

Everything is made by tools/hfdl_tx.py and tools/hfdl_pdu.py, from the seed's
text alone. The I/Q files are checked with the reference decoder when the
`hfdl-ref` image is present (it must find every frame).
"""
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = HERE.parent
sys.path.insert(0, str(HERE))
import hfdl_pdu as P  # noqa: E402
import hfdl_tx as T   # noqa: E402

EX = P.examples()


def data_indices(m1, pdu):
    """The frame's data symbols as received: phase indices k (symbol =
    exp(j 2 pi k / M)), scrambler applied, phase resolved."""
    syms = T.frame_symbols(m1, pdu, T.prekey_symbols())
    mode = T.PHY["modes"][m1]
    m = 1 << mode["bits_per_symbol"]
    pre = len(syms) - mode["data_segments"] * 45
    out = []
    for seg in range(mode["data_segments"]):
        for s in syms[pre + seg * 45: pre + seg * 45 + 30]:
            out.append(int(round(math.atan2(s.imag, s.real) / (2 * math.pi / m))) % m)
    return out


def frame_octets(m1, pdu):
    mode = T.PHY["modes"][m1]
    return (bytes(pdu) + bytes(mode["user_octets"] - len(pdu))).hex()


def frame_suite():
    order = ["spdu-shannon", "logon-request-freq-data", "logon-confirm", "performance-data",
             "acars-h1-downlink", "acars-uplink-ack", "performance-data", "acars-h1-downlink"]
    cases = []
    rng = random.Random(7)
    for m1 in range(8):
        name = order[m1]
        pdu = EX[name]
        idx = data_indices(m1, pdu)
        cases.append({"id": f"m{m1}-{name}", "source": "synthetic",
                      "description": f"mode {m1}: {name}, error-free",
                      "input": {"m1": m1, "symbols": idx},
                      "expected": {"octets": frame_octets(m1, pdu)}, "req": ["DEC-02"]})
    for m1 in (1, 3, 5):
        pdu = EX["acars-h1-downlink"]
        idx = data_indices(m1, pdu)
        m = 1 << T.PHY["modes"][m1]["bits_per_symbol"]
        bad = sorted(rng.sample(range(0, len(idx), 97), 6))
        for i in bad:
            idx[i] = (idx[i] + m // 2) % m
        cases.append({"id": f"m{m1}-six-symbol-errors", "source": "synthetic",
                      "description": f"mode {m1}: six data symbols turned by 180 degrees, far apart; any maximum-likelihood decoder corrects them",
                      "input": {"m1": m1, "symbols": idx},
                      "expected": {"octets": frame_octets(m1, pdu)}, "req": ["DEC-02"],
                      "note": "symbol positions " + ", ".join(map(str, bad))})
    return {"suite": "frame-decode", "normative": True,
            "description": "A frame's data symbols (phase indices as received: scrambled, phase resolved) and its M1 mode -> the frame's octets (spec/04-algorithms/02-frame.md). The octets after the PDU are zero here.",
            "compare": {"method": "octets exactly"}, "cases": cases}


SYNTH = [
    dict(id="synth-all-modes", rate=48000, center=8935000, noise=-50, frames=[
        (1.0, 8942, 0, "spdu-shannon"), (3.6, 8942, 1, "logon-request-freq-data"), (6.2, 8942, 2, "logon-confirm"),
        (8.8, 8942, 3, "performance-data"), (11.4, 8942, 4, "acars-h1-downlink"), (16.4, 8942, 5, "acars-uplink-ack"),
        (21.4, 8942, 6, "performance-data"), (26.4, 8942, 7, "acars-h1-downlink")], dur=32,
        note="one frame in each of the eight modes on 8942 kHz, strong"),
    dict(id="synth-two-channels", rate=48000, center=8935000, noise=-45, frames=[
        (1.0, 8927, 0, "spdu-shannon"), (1.3, 8942, 1, "logon-confirm"), (4.0, 8927, 1, "acars-uplink-ack"),
        (4.2, 8942, 0, "logon-request-freq-data")], dur=8,
        note="frames overlapping in time on 8927 and 8942 kHz"),
    dict(id="synth-offsets", rate=24000, center=8950000, noise=-40, frames=[
        (1.0, 8942, 1, "acars-h1-downlink", dict(freq_err_hz=15.0, phase_rad=1.0)),
        (4.0, 8942, 2, "performance-data", dict(freq_err_hz=-20.0, sample_slip_ppm=40.0)),
        (7.0, 8948, 0, "spdu-shannon", dict(level_dbfs=-30, phase_rad=2.5))], dur=10,
        note="carrier offsets of +15 and -20 Hz, a 40 ppm sample-rate error, an odd phase, a weaker frame"),
    dict(id="synth-noise-only", rate=24000, center=8950000, noise=-30, frames=[], dur=10,
        note="white noise, no HFDL: no frame"),
    dict(id="synth-silence", rate=24000, center=8950000, noise=None, frames=[], dur=5,
        note="digital silence: no frame"),
]


def synth_suite():
    out_dir = SEED / "conformance/iq"
    cases = []
    for s in SYNTH:
        frames = []
        for f in s["frames"]:
            t, khz, m1, name = f[:4]
            extra = f[4] if len(f) > 4 else {}
            frames.append(dict(t=t, freq_khz=khz, m1=m1, pdu=EX[name].hex(), level_dbfs=extra.get("level_dbfs", -20), **{k: v for k, v in extra.items() if k != "level_dbfs"}))
        cfg = {"sample_rate": s["rate"], "center_hz": s["center"], "duration_s": s["dur"],
               "noise_dbfs": s["noise"], "seed": 1, "frames": frames}
        name = f"20261125T120000_{s['id']}_{s['center']}Hz.wav"
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(cfg, tf)
        subprocess.run(["python3", str(HERE / "hfdl_tx.py"), tf.name, str(out_dir / name)], check=True)
        chans = sorted({f["freq_khz"] for f in frames}) or [8942]
        rates = {0: (300, "S"), 1: (600, "S"), 2: (1200, "S"), 3: (1800, "S"), 4: (300, "D"), 5: (600, "D"), 6: (1200, "D"), 7: (1800, "D")}
        cases.append({"id": s["id"], "source": "synthetic", "description": s["note"],
                      "input": {"file": name, "kind": "iq", "sample_rate": s["rate"], "center_hz": s["center"],
                                "channels_khz": chans, "start_utc_epoch": 1795608000, "time_zone": "UTC"},
                      "expected": {"frames": [{"freq_khz": f["freq_khz"], "t": f["t"], "bit_rate": rates[f["m1"]][0],
                                               "slot": rates[f["m1"]][1], "pdu": f["pdu"], "required": True} for f in frames]},
                      "req": ["DEC-01", "DEC-04", "DEC-05", "DEC-06"] + (["DEC-08"] if not frames else [])})
        if shutil.which("docker") and frames:
            check = subprocess.run(
                f"tail -c +45 '{out_dir / name}' | docker run --rm -i -e HFDL_SAMPLE_CLOCK_BASE=0 hfdl-ref dumphfdl --iq-file - "
                f"--sample-format CS16 --sample-rate {s['rate']} --centerfreq {s['center'] / 1000} {' '.join(map(str, chans))} "
                f"--output-mpdus --output decoded:json:file:path=/dev/stdout 2>/dev/null",
                shell=True, capture_output=True, text=True).stdout
            found = {json.loads(l)["hfdl"].get("mpdu", json.loads(l)["hfdl"].get("spdu", {})).get("raw", "")[:16]
                     for l in check.splitlines() if l.startswith("{")}
            missing = [f for f in frames if f["pdu"][:16] not in found]
            print(s["id"], len(frames), "frames, reference missed", len(missing))
    return {"suite": "iq-decode-synthetic", "cases": cases}


def main():
    (SEED / "conformance/frame").mkdir(parents=True, exist_ok=True)
    (SEED / "conformance/frame/decode.json").write_text(json.dumps(frame_suite()) + "\n")
    s = synth_suite()
    (SEED / "conformance/iq/synthetic.json").write_text(json.dumps(s, indent=1) + "\n")


if __name__ == "__main__":
    main()
