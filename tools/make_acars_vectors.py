#!/usr/bin/env python3
"""Builds conformance/parse/acars.json: sequences of ACARS blocks -> what
libacars (tools/reference/acars_seq.c, HFDL bearer) makes of each block,
including reassembly.

    python3 tools/make_acars_vectors.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE.parent
sys.path.insert(0, str(HERE))
import hfdl_apps as A  # noqa: E402
import hfdl_pdu as P   # noqa: E402


def blk(*a, **k):
    return P.acars(*a, **k)[1:]          # without SOH


def corrupt(b, i, x=0x01):
    b = bytearray(b)
    b[i] ^= x
    return bytes(b)


DOWN_A = dict(msg_num="D01A", flight="SU1003")


def seq_cases():
    c = []
    c.append(("single-h1-sublabel-mfi", "one downlink H1 block with sublabel CF and MFI 5Z: final, skipped",
              [(0, "d", blk("2", "RA73752", "H1", "6", "#CFB/5Z ENG 1 FIRE LOOP B FAULT", msg_num="D01A", flight="SU1003"))]))
    c.append(("uplink-general-response", "an uplink _d without text",
              [(0, "u", blk("2", "XA-ADC", "_\x7f", "N", ack=ord("8")))]))
    c.append(("downlink-without-text", "a downlink block without text: an error",
              [(0, "d", blk("2", "RA73752", "_\x7f", "3"))]))
    c.append(("bad-crc", "a downlink block with a bad CRC: parsed, CRC flagged",
              [(0, "d", corrupt(blk("2", "RA73752", "H1", "6", "TEXT", **DOWN_A), -3))]))
    c.append(("too-short", "12 octets: an error", [(0, "d", blk("2", "RA73752", "H1", "6")[:12])]))
    c.append(("no-del", "the last octet is not DEL: an error", [(0, "d", blk("2", "RA73752", "H1", "6", "TEXT", **DOWN_A)[:-1] + b"\x00")]))
    c.append(("nul-in-text", "a NUL in the text is shown as a dot",
              [(0, "d", blk("2", "RA73752", "H1", "6", "AB\x00CD", **DOWN_A))]))
    c.append(("ack-character", "technical acknowledgement ACK (0x06) shown as ^",
              [(0, "u", blk("2", "EI-FNH", "SQ", "A", "TEXT", ack=0x06))]))
    t1, t2, t3 = "FIRST BLOCK OF A LONG MESSAGE ", "SECOND BLOCK ", "LAST"
    c.append(("downlink-three-blocks", "downlink in three blocks A, B, C: in progress, in progress, complete with the joined text",
              [(0, "d", blk("2", "G-VZIG", "H1", "1", t1, msg_num="D02A", flight="VIR401", final=False)),
               (30, "d", blk("2", "G-VZIG", "H1", "2", t2, msg_num="D02B", flight="VIR401", final=False)),
               (60, "d", blk("2", "G-VZIG", "H1", "3", t3, msg_num="D02C", flight="VIR401"))]))
    c.append(("downlink-duplicate", "block B received twice: the second is a duplicate",
              [(0, "d", blk("2", "G-VZIG", "H1", "1", t1, msg_num="D03A", flight="VIR401", final=False)),
               (30, "d", blk("2", "G-VZIG", "H1", "2", t2, msg_num="D03B", flight="VIR401", final=False)),
               (40, "d", blk("2", "G-VZIG", "H1", "2", t2, msg_num="D03B", flight="VIR401", final=False)),
               (60, "d", blk("2", "G-VZIG", "H1", "3", t3, msg_num="D03C", flight="VIR401"))]))
    c.append(("downlink-gap", "blocks A then C: out of sequence, the joining is abandoned",
              [(0, "d", blk("2", "G-VZIG", "H1", "1", t1, msg_num="D04A", flight="VIR401", final=False)),
               (60, "d", blk("2", "G-VZIG", "H1", "3", t3, msg_num="D04C", flight="VIR401"))]))
    c.append(("downlink-first-lost", "only block B (final) arrives: out of sequence",
              [(0, "d", blk("2", "G-VZIG", "H1", "2", t3, msg_num="D05B", flight="VIR401"))]))
    c.append(("downlink-timeout", "block B 1300 s after A (downlink timeout 1260 s): starts anew, and is out of sequence",
              [(0, "d", blk("2", "G-VZIG", "H1", "1", t1, msg_num="D06A", flight="VIR401", final=False)),
               (1300, "d", blk("2", "G-VZIG", "H1", "2", t3, msg_num="D06B", flight="VIR401"))]))
    c.append(("downlink-just-in-time", "block B 1250 s after A: joined",
              [(0, "d", blk("2", "G-VZIG", "H1", "1", t1, msg_num="D07A", flight="VIR401", final=False)),
               (1250, "d", blk("2", "G-VZIG", "H1", "2", t3, msg_num="D07B", flight="VIR401"))]))
    c.append(("uplink-wrap", "uplink blocks V, W, A: the block ID wraps after W; complete",
              [(0, "u", blk("2", "A6-ARD", "C1", "V", "UPLINK PART ONE ", final=False)),
               (10, "u", blk("2", "A6-ARD", "C1", "W", "PART TWO ", final=False)),
               (20, "u", blk("2", "A6-ARD", "C1", "A", "PART THREE"))]))
    c.append(("uplink-timeout", "uplink block B 400 s after A (uplink timeout 370 s): starts anew, final: skipped",
              [(0, "u", blk("2", "A6-ARD", "C1", "A", "PART ONE ", final=False)),
               (400, "u", blk("2", "A6-ARD", "C1", "B", "PART TWO"))]))
    c.append(("interleaved-keys", "two downlink messages interleaved (different message numbers): both complete",
              [(0, "d", blk("2", "D-ABYT", "H1", "1", "ONE-A ", msg_num="D10A", flight="DLH400", final=False)),
               (5, "d", blk("2", "D-ABYT", "H1", "2", "TWO-A ", msg_num="D11A", flight="DLH400", final=False)),
               (10, "d", blk("2", "D-ABYT", "H1", "3", "ONE-B", msg_num="D10B", flight="DLH400")),
               (15, "d", blk("2", "D-ABYT", "H1", "4", "TWO-B", msg_num="D11B", flight="DLH400"))]))
    ads = A.arinc622("REKCAYA", "ADS", "A6-BNI", A.basic_report(7, 64.1, -21.9, 38000, 1800.0) + A.earth_ref(270, 480, 0))
    c.append(("joined-application", "an ADS-C message split over two H1 blocks: decoded once, on the completing block",
              [(0, "d", blk("2", "A6-BNI", "H1", "1", "#M1B" + ads[:30], msg_num="M01A", flight="UAE11", final=False)),
               (20, "d", blk("2", "A6-BNI", "H1", "2", ads[30:], msg_num="M01B", flight="UAE11"))]))
    c.append(("uplink-no-wrap-after-x", "uplink blocks W, X, A: X follows W, but A does not follow X (the wrap is after W): out of sequence",
              [(0, "u", blk("2", "A6-ARD", "C2", "W", "PART ONE ", final=False)),
               (10, "u", blk("2", "A6-ARD", "C2", "X", "PART TWO ", final=False)),
               (20, "u", blk("2", "A6-ARD", "C2", "A", "PART THREE"))]))
    return c


def main():
    src = (HERE / "reference/acars_seq.c").read_text()
    cases = seq_cases()
    script = "cat > /tmp/a.c <<'CEOF'\n" + src + "\nCEOF\ngcc -O2 -I/usr/local/include/libacars-2 -o /tmp/acars_seq /tmp/a.c -lacars-2 || exit 1\n"
    for i, (_, _, blocks) in enumerate(cases):
        lines = "\n".join(f"{t} {d} {b.hex()}" for t, d, b in blocks)
        script += f"printf '%s\\n' '{lines}' | /tmp/acars_seq; echo '<<END>>'\n"
    out = subprocess.run(["docker", "run", "--rm", "-i", "hfdl-ref", "bash"], input=script,
                         capture_output=True, text=True, check=True).stdout
    chunks = out.split("<<END>>\n")
    suite_cases = []
    for (cid, desc, blocks), chunk in zip(cases, chunks):
        res = [json.loads(l) for l in chunk.strip().splitlines()]
        assert len(res) == len(blocks), (cid, chunk)
        suite_cases.append({"id": cid, "source": "synthetic", "description": desc,
                            "input": {"blocks": [{"t": t, "direction": "uplink" if d == "u" else "downlink", "octets": b.hex()} for t, d, b in blocks]},
                            "expected": {"blocks": res}, "req": ["PAR-01", "PAR-04"]})
        print(cid, [r.get("acars", {}).get("reassembly") for r in res])
    suite = {"suite": "parse-acars", "normative": True,
             "description": "ACARS blocks (the octets after SOH, as in an enveloped-data HFNPDU) parsed in order with reassembly (spec/03-domain/acars.md), t in seconds -> each block's result, in libacars' JSON vocabulary (F-H19).",
             "compare": {"method": "every key of expected present with an equal value; keys not in expected ignored", "non_normative_keys": ["descr", "name", "msg_type"], "float_abs_tolerance": 1e-5},
             "cases": suite_cases}
    (SEED / "conformance/parse/acars.json").write_text(json.dumps(suite, indent=1) + "\n")


if __name__ == "__main__":
    main()
