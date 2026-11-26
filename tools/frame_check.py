#!/usr/bin/env python3
"""A frame decoder written from spec/04-algorithms/02-frame.md (hard
decisions, Viterbi with start and end state 0), run on
conformance/frame/decode.json: every case must give its octets.

    python3 tools/frame_check.py
"""
import json
from pathlib import Path

import numpy as np

SEED = Path(__file__).resolve().parent.parent
PHY = json.loads((SEED / "spec/03-domain/physical.json").read_text())


def gray_encode(k):
    return k ^ (k >> 1)


def deinterleave(bits, columns, shift):
    rows = 40
    table = [[0] * columns for _ in range(rows)]
    r = c = 0
    for b in bits:
        table[r][c] = b
        r += 1
        if r == rows:
            r = 0
            c += 1
        c -= shift
        if c < 0:
            c += columns
    out = []
    r = c = 0
    for _ in range(len(bits)):
        out.append(table[r][c])
        r = (r + 9) % rows
        if r == 0:
            c += 1
    return out


def parity(x):
    return bin(x).count("1") & 1


OUTS = [(parity(((s << 1) | b) & 0x7F & 0x6D), parity(((s << 1) | b) & 0x7F & 0x4F)) for s in range(64) for b in (0, 1)]


def viterbi(soft):
    """soft: values 0..1 per coded bit (1 = surely 1). Returns decoded bits."""
    n = len(soft) // 2
    inf = 1e18
    metric = np.full(64, inf)
    metric[0] = 0.0
    back = np.zeros((n, 64), dtype=np.int16)
    for i in range(n):
        a, b = soft[2 * i], soft[2 * i + 1]
        new = np.full(64, inf)
        for s in range(64):
            if metric[s] >= inf:
                continue
            for x in (0, 1):
                o0, o1 = OUTS[s * 2 + x]
                cost = metric[s] + abs(o0 - a) + abs(o1 - b)
                ns = ((s << 1) | x) & 0x3F
                if cost < new[ns]:
                    new[ns] = cost
                    back[i, ns] = s * 2 + x
        metric = new
    s = 0                                   # end state 0
    bits = [0] * n
    for i in range(n - 1, -1, -1):
        prev = back[i, s]
        bits[i] = prev & 1
        s = prev >> 1
    return bits


def decode(m1, symbols):
    p = PHY["modes"][m1]
    bps = p["bits_per_symbol"]
    m = 1 << bps
    scr = PHY["scrambler"]
    soft = []
    for i, k in enumerate(symbols):
        if scr[i % 120] == "1":
            k = (k + m // 2) % m
        g = gray_encode(k)
        soft += [(g >> (bps - 1 - j)) & 1 for j in range(bps)]
    coded = deinterleave(soft, p["interleaver_columns"], p["interleaver_column_shift"])
    if p["repetition"] == 2:
        coded = [(coded[2 * i] + coded[2 * i + 1]) / 2 for i in range(len(coded) // 2)]
    bits = viterbi(coded)
    octets = bytearray((len(bits) + 7) // 8)
    for i, b in enumerate(bits):
        octets[i // 8] |= b << (i % 8)
    return octets.hex()


def main():
    suite = json.loads((SEED / "conformance/frame/decode.json").read_text())
    bad = 0
    for c in suite["cases"]:
        got = decode(c["input"]["m1"], c["input"]["symbols"])
        ok = got == c["expected"]["octets"]
        bad += not ok
        print("ok  " if ok else "FAIL", c["id"])
    raise SystemExit(bad)


if __name__ == "__main__":
    main()
