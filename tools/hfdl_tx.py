#!/usr/bin/env python3
"""A small HFDL transmitter for synthetic test vectors.

Written from spec/03-domain/physical-layer.md and physical.json, independent of
any receiver: it runs the receiver's chain backwards. A frame carries one PDU
(octets), is sent with one of the eight M1 modes, and is placed at a given
time in a complex baseband recording.

    python3 tools/hfdl_tx.py frames.json out.cf32
    python3 tools/hfdl_tx.py frames.json out.wav

frames.json:
{
  "sample_rate": 48000,          # output rate (Hz)
  "center_hz": 8902500,          # the recording's center (tuned) frequency
  "duration_s": 30,
  "noise_dbfs": -60,             # white noise level (per complex sample), or null
  "seed": 1,
  "frames": [
    {"t": 1.0, "freq_khz": 8942, "m1": 0, "pdu": "hex octets", "level_dbfs": -20,
     "freq_err_hz": 0.0, "phase_rad": 0.0, "sample_slip_ppm": 0.0}
  ]
}

`.cf32` is raw little-endian float32 I/Q pairs; `.wav` is 16-bit stereo
(I left, Q right) with the rate as the WAV sample rate.
"""

import json
import math
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PHY = json.loads((HERE.parent / "spec/03-domain/physical.json").read_text())

SPS = 3                     # samples per symbol before resampling
RATE = PHY["symbol_rate_bd"]
OFFSET = PHY["carrier_offset_hz"]

# The pulse shape (also the receiver's matched filter in the informative
# method of spec/04-algorithms/01-receiver.md), 3 samples per symbol.
PULSE = np.array([
    -0.0170974647427123, 0.01148231492068473, 0.03138375667422348, 0.009454398851680437,
    -0.04161644170893816, -0.06451564801420356, -0.005495792933327306, 0.1316404671361545,
    0.2759693160697777, 0.3375901874933208, 0.2759693160697777, 0.1316404671361545,
    -0.005495792933327306, -0.06451564801420356, -0.04161644170893816, 0.009454398851680437,
    0.03138375667422348, 0.01148231492068473, -0.0170974647427123])


def bits(s):
    return [int(c) for c in s]


def bpsk(bitlist):
    """Bit 0 is +1, bit 1 is -1."""
    return [1.0 if b == 0 else -1.0 for b in bitlist]


def parity(x):
    return bin(x).count("1") & 1


def conv_encode(info):
    """K=7, rate 1/2; register = (register << 1) | bit, outputs
    parity(register & 0x6D) then parity(register & 0x4F)."""
    reg = 0
    out = []
    for b in info:
        reg = ((reg << 1) | b) & 0x7F
        out.append(parity(reg & 0x6D))
        out.append(parity(reg & 0x4F))
    return out


def interleaver_maps(columns, shift):
    """The receiver's table positions: push order (received) and pop order
    (to the Viterbi decoder), physical-layer.md section 6."""
    rows = 40
    n = rows * columns
    push = []
    r = c = 0
    for _ in range(n):
        push.append((r, c))
        r += 1
        if r == rows:
            r = 0
            c += 1
        c -= shift
        if c < 0:
            c += columns
    pop = []
    r = c = 0
    for _ in range(n):
        pop.append((r, c))
        r = (r + 9) % rows
        if r == 0:
            c += 1
    return push, pop


def gray_decode(g):
    n = 0
    while g:
        n ^= g
        g >>= 1
    return n


def frame_symbols(m1, pdu, prekey):
    mode = PHY["modes"][m1]
    bps = mode["bits_per_symbol"]
    nbits = mode["user_bits"]
    # PDU octets -> bits, least significant bit of each octet first
    info = []
    for o in pdu:
        info.extend((o >> i) & 1 for i in range(8))
    if len(info) > nbits - 6:
        raise ValueError(f"PDU of {len(pdu)} octets too long for mode {m1}")
    info += [0] * (nbits - len(info))
    coded = conv_encode(info)
    if mode["repetition"] == 2:
        coded = [b for b in coded for _ in (0, 1)]
    columns, shift = mode["interleaver_columns"], mode["interleaver_column_shift"]
    push, pop = interleaver_maps(columns, shift)
    assert len(coded) == len(push)
    cell = {pos: coded[v] for v, pos in enumerate(pop)}
    sent = [cell[pos] for pos in push]
    # bits -> PSK symbols (Gray, most significant bit first), then scramble
    m = 1 << bps
    scr = bits(PHY["scrambler"])
    data = []
    for i in range(len(sent) // bps):
        v = 0
        for b in sent[i * bps:(i + 1) * bps]:
            v = (v << 1) | b
        k = gray_decode(v)
        s = complex(math.cos(2 * math.pi * k / m), math.sin(2 * math.pi * k / m))
        if scr[i % len(scr)]:
            s = -s
        data.append(s)
    t = bpsk(bits(PHY["T"]))
    sym = list(prekey)
    sym += bpsk(bits(PHY["A"])) * 2
    sym += bpsk(bits(mode["m1"]))
    sym += bpsk(bits(mode["m2"]))
    sym += t * PHY["T_count_preamble"]
    seg = PHY["data_segment_symbols"]
    for i in range(mode["data_segments"]):
        sym += data[i * seg:(i + 1) * seg]
        sym += t
    assert len(sym) == mode["symbols"], (len(sym), mode["symbols"])
    return np.array(sym, dtype=np.complex128)


def prekey_symbols():
    """The prekey's content is not used by a receiver (it is for the
    receiver's gain control); synthetic frames send BPSK of a 15-bit
    m-sequence (physical-layer.md section 2, F-H03)."""
    reg = 1
    out = []
    for _ in range(PHY["prekey_symbols"]):
        b = parity(reg & 0x4001)
        reg = ((reg << 1) | b) & 0x7FFF
        out.append(1.0 if b == 0 else -1.0)
    return out


def modulate(sym, fs, freq_hz, phase, slip_ppm):
    """Pulse-shape at 3 samples per symbol, then resample to fs (linear
    interpolation of a 3x-oversampled shaped signal is enough after an
    extra 8x upsampling) and shift to freq_hz."""
    up = np.zeros(len(sym) * SPS, dtype=np.complex128)
    up[::SPS] = sym
    x = np.convolve(up, PULSE * SPS)
    src_rate = RATE * SPS * (1.0 + slip_ppm * 1e-6)
    n_out = int(len(x) / src_rate * fs)
    t_src = np.arange(n_out) * src_rate / fs
    re = np.interp(t_src, np.arange(len(x)), x.real)
    im = np.interp(t_src, np.arange(len(x)), x.imag)
    y = re + 1j * im
    n = np.arange(n_out)
    return y * np.exp(1j * (2 * math.pi * freq_hz * n / fs + phase))


def main():
    cfg = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    fs = cfg["sample_rate"]
    total = int(cfg["duration_s"] * fs)
    sig = np.zeros(total, dtype=np.complex128)
    rng = np.random.default_rng(cfg.get("seed", 1))
    pre = prekey_symbols()
    for f in cfg["frames"]:
        sym = frame_symbols(f["m1"], bytes.fromhex(f["pdu"]), pre)
        # the HFDL signal is centred 1440 Hz above the assigned frequency
        off = f["freq_khz"] * 1000 + OFFSET - cfg["center_hz"] + f.get("freq_err_hz", 0.0)
        y = modulate(sym, fs, off, f.get("phase_rad", 0.0), f.get("sample_slip_ppm", 0.0))
        y *= 10 ** (f.get("level_dbfs", -20) / 20) / max(np.max(np.abs(y)), 1e-9)
        start = int(f["t"] * fs)
        end = min(total, start + len(y))
        sig[start:end] += y[:end - start]
    if cfg.get("noise_dbfs") is not None:
        a = 10 ** (cfg["noise_dbfs"] / 20) / math.sqrt(2)
        sig += a * (rng.standard_normal(total) + 1j * rng.standard_normal(total))
    if out.suffix == ".wav":
        iq = np.empty(2 * total, dtype=np.int16)
        iq[0::2] = np.clip(np.round(sig.real * 32767), -32768, 32767)
        iq[1::2] = np.clip(np.round(sig.imag * 32767), -32768, 32767)
        data = iq.tobytes()
        hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
        hdr += struct.pack("<IHHIIHH", 16, 1, 2, fs, fs * 4, 4, 16)
        hdr += b"data" + struct.pack("<I", len(data))
        out.write_bytes(hdr + data)
    else:
        iq = np.empty(2 * total, dtype=np.float32)
        iq[0::2] = sig.real
        iq[1::2] = sig.imag
        out.write_bytes(iq.tobytes())


if __name__ == "__main__":
    main()
