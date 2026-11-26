#!/usr/bin/env python3
"""Cuts an excerpt from a long I/Q recording for the conformance suite.

    python3 tools/excerpt.py IN.wav OUT.wav --center-in 8902500 --t0 228 --dur 62 \
        --center-out 8961000 --decim 5 [--audio-khz 8977 --audio-rate 12500]

IN.wav: 16-bit stereo I/Q (ShellSDR / SDR++ baseband). The excerpt starts t0 s
into the file, is shifted to center-out, low-pass filtered (Kaiser-windowed
sinc, cut-off 0.45 of the new rate) and decimated by an integer factor. With
--audio-khz it is instead the audio an upper-sideband receiver tuned to that
frequency would give: real samples, the HFDL signal around 1440 Hz.
"""
import argparse
import struct
from pathlib import Path

import numpy as np


def read_iq(path, t0, dur):
    with open(path, "rb") as f:
        assert f.read(4) == b"RIFF"
        f.read(4)
        assert f.read(4) == b"WAVE"
        rate = None
        while True:
            hdr = f.read(8)
            cid, size = hdr[:4], struct.unpack("<I", hdr[4:])[0]
            if cid == b"fmt ":
                fmt = struct.unpack("<HHIIHH", f.read(16))
                f.read(size - 16)
                assert fmt[1] == 2 and fmt[5] == 16, fmt
                rate = fmt[2]
            elif cid == b"data":
                start = f.tell()
                break
            else:
                f.read(size + (size & 1))
    n0, n = int(t0 * rate), int(dur * rate)
    data = np.memmap(path, dtype="<i2", mode="r", offset=start + 4 * n0, shape=(2 * n,))
    x = data[0::2].astype(np.float64) + 1j * data[1::2].astype(np.float64)
    return x / 32768.0, rate


def lowpass(numtaps, cutoff):
    """cutoff as a fraction of the sample rate."""
    n = np.arange(numtaps) - (numtaps - 1) / 2
    h = 2 * cutoff * np.sinc(2 * cutoff * n) * np.kaiser(numtaps, 8.6)
    return h / h.sum()


def write_wav(path, samples, rate, channels):
    data = samples.astype("<i2").tobytes()
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
    hdr += struct.pack("<IHHIIHH", 16, 1, channels, rate, rate * 2 * channels, 2 * channels, 16)
    hdr += b"data" + struct.pack("<I", len(data))
    Path(path).write_bytes(hdr + data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--center-in", type=float, required=True)
    ap.add_argument("--t0", type=float, required=True)
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--center-out", type=float)
    ap.add_argument("--decim", type=int, required=True)
    ap.add_argument("--audio-khz", type=float)
    ap.add_argument("--gain", type=float, default=1.0, help="after normalising the 99.9th percentile to 0.3")
    a = ap.parse_args()
    x, rate = read_iq(a.inp, a.t0, a.dur)
    # for audio: put the assigned frequency at 0 Hz, keep the upper sideband
    shift_to = a.audio_khz * 1000 if a.audio_khz else a.center_out
    t = np.arange(len(x)) / rate
    x = x * np.exp(-2j * np.pi * (shift_to - a.center_in) * t)
    out_rate = rate // a.decim
    if a.audio_khz:
        # pass 0..3 kHz (the USB channel), as a complex band-pass around 1.5 kHz
        h = lowpass(8 * a.decim + 1, 1600.0 / rate) * np.exp(2j * np.pi * 1500.0 / rate * np.arange(8 * a.decim + 1))
        y = np.convolve(x, h, mode="same")[:: a.decim]
        audio = np.real(y)
        audio *= 0.3 / max(1e-9, np.percentile(np.abs(audio), 99.9))
        write_wav(a.out, np.clip(np.round(audio * 32767 * a.gain), -32768, 32767), out_rate, 1)
    else:
        h = lowpass(16 * a.decim + 1, 0.45 / a.decim)
        y = np.convolve(x, h, mode="same")[:: a.decim]
        y *= a.gain * 0.3 / max(1e-12, np.percentile(np.abs(y), 99.9))   # use the 16-bit range
        iq = np.empty(2 * len(y))
        iq[0::2], iq[1::2] = y.real, y.imag
        write_wav(a.out, np.clip(np.round(iq * 32767), -32768, 32767), out_rate, 2)


if __name__ == "__main__":
    main()
