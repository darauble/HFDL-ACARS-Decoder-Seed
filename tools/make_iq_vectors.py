#!/usr/bin/env python3
"""Builds conformance/iq/: excerpts of real recordings and the reference frames
of each, from the reference decoder (tools/reference, image `hfdl-ref`).

    python3 tools/make_iq_vectors.py RECORDINGS_DIR

RECORDINGS_DIR holds the original recordings (not in the seed; their names are
in EXCERPTS). For each excerpt: cut it (tools/excerpt.py), decode it with the
reference, decode the same window of the whole recording too (cached), and
write the frames: `required` when both decodes found the frame with a
signal-to-noise ratio of at least MIN_SNR_DB, otherwise `optional` (F-H17).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE.parent
OUT = SEED / "conformance/iq"
MIN_SNR_DB = 8.0

# name, source, its center (Hz), its start (UTC epoch), t0, dur, new center (Hz), decimation, channels (kHz)
# or, for audio, the channel instead of the new center
REC89 = ("20261125-095421_baseband_8902500Hz-HFDL.wav", 8902500, 1795600461)
REC10 = ("20261125-095504_baseband_10058500Hz-HFDL.wav", 10058500, 1795600504)
EXCERPTS = [
    dict(name="20261125T095809_iq50k_8961000Hz.wav", rec=REC89, t0=228, dur=62, center=8961000, decim=5,
         channels=[8939, 8942, 8948, 8957, 8977], note="five channels; ADS-C (A6), ARINC 622 (AA), H1 warnings, media advisories"),
    dict(name="20261125T100503_iq12k5_8979000Hz.wav", rec=REC89, t0=642, dur=20, center=8979000, decim=20,
         channels=[8977], note="600 bit/s double slot: ACARS 27 position report"),
    dict(name="20261125T102321_iq12k5_8979000Hz.wav", rec=REC89, t0=1740, dur=150, center=8979000, decim=20,
         channels=[8977], note="1200 bit/s; MIAM (MA); a block being joined"),
    dict(name="20261125T101949_iq12k5_8944000Hz.wav", rec=REC89, t0=1528, dur=35, center=8944000, decim=20,
         channels=[8942], note="Shannon 8942 kHz, several strong frames"),
    dict(name="20261125T101102_iq12k5_10029000Hz.wav", rec=REC10, t0=958, dur=45, center=10029000, decim=20,
         channels=[10027], note="10 MHz band, Molokai"),
    dict(name="20261125T095809_usb12k5_8977kHz.wav", rec=REC89, t0=228, dur=62, audio_khz=8977, decim=20,
         channels=[8977], note="USB audio of 8977 kHz (the signal at 1440 Hz), from the first excerpt"),
]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def reference(wav_or_raw, rate, center_khz, channels, fmt="CS16", skip=44):
    """Frames found by the reference: [(freq_khz, t_s, raw_hex, snr_db)], t from the first sample."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(wav_or_raw)
        cmd = (f"tail -c +{skip + 1} '{src}' | docker run --rm -i -e HFDL_SAMPLE_CLOCK_BASE=0 -v {d}:/out hfdl-ref "
               f"dumphfdl --iq-file - --sample-format {fmt} --sample-rate {rate} --centerfreq {center_khz} "
               + " ".join(str(c) for c in channels) + " --output-mpdus --output decoded:json:file:path=/out/o.json")
        run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        frames = []
        for line in open(Path(d) / "o.json"):
            h = json.loads(line)["hfdl"]
            key = "mpdu" if "mpdu" in h else ("spdu" if "spdu" in h else None)
            if key is None or h[key].get("err"):
                continue
            t = h["t"]["sec"] + h["t"]["usec"] / 1e6
            frames.append((h["freq"] // 1000, t, h[key]["raw"], h["sig_level"] - h["noise_level"],
                           h["bit_rate"], h["slot"]))
        return frames


def pdu_octets(raw):
    """The PDU's own octets (the frame after it is padding, physical-layer.md §8)."""
    b = bytes.fromhex(raw)
    if b[0] & 1 == 0:
        return b[:66]
    if b[0] & 2:
        n = (b[0] >> 2) & 0xF
        hdr = 6 + n
        return b[: hdr + 2 + sum(b[6 + i] + 1 for i in range(n))]
    count = ((b[0] & 0x70) >> 4) + 1
    pos, lens = 2, []
    for _ in range(count):
        m = b[pos + 1] >> 4
        lens += [b[pos + 2 + i] + 1 for i in range(m)]
        pos += 2 + m
    return b[: pos + 2 + sum(lens)]


def main():
    recdir = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    cache = {}
    cases = []
    for ex in EXCERPTS:
        rec_name, rec_center, rec_start = ex["rec"]
        src = recdir / rec_name
        out = OUT / ex["name"]
        args = ["python3", str(HERE / "excerpt.py"), str(src), str(out), "--center-in", str(rec_center),
                "--t0", str(ex["t0"]), "--dur", str(ex["dur"]), "--decim", str(ex["decim"])]
        rate = 250000 // ex["decim"]
        if "audio_khz" in ex:
            args += ["--audio-khz", str(ex["audio_khz"])]
            # the reference decodes I/Q: give it the analytic signal of the audio, centred on 1440 Hz
            run(args)
            with tempfile.TemporaryDirectory() as d:
                raw = Path(d) / "a.cf32"
                run(["python3", "-c", f"""
import numpy as np, struct
d=open('{out}','rb').read(); x=np.frombuffer(d[44:],'<i2').astype(np.float64)/32768
X=np.fft.fft(x); n=len(x); h=np.zeros(n); h[0]=1; h[1:(n+1)//2]=2
if n%2==0: h[n//2]=1
a=np.fft.ifft(X*h).astype(np.complex64); iq=np.empty(2*n,np.float32); iq[0::2]=a.real; iq[1::2]=a.imag; iq.tofile('{raw}')"""])
                # the analytic audio has the assigned frequency at 0 Hz: tell the reference so
                ex_frames = reference(raw, rate, ex["audio_khz"], [ex["audio_khz"]], fmt="CF32", skip=0)
        else:
            args += ["--center-out", str(ex["center"])]
            run(args)
            ex_frames = reference(out, rate, ex["center"] / 1000, ex["channels"])
        key = rec_name
        if key not in cache:
            chans = sorted({c for e in EXCERPTS if e["rec"][0] == rec_name for c in e["channels"]})
            cache[key] = reference(src, 250000, rec_center / 1000, chans)
        full = [f for f in cache[key] if f[0] in ex["channels"] and ex["t0"] <= f[1] <= ex["t0"] + ex["dur"]]
        full_set = {(f[0], f[2]) for f in full}
        frames = []
        for f, t, raw, snr, br, slot in ex_frames:
            strong = (f, raw) in full_set and snr >= MIN_SNR_DB
            frames.append({"freq_khz": f, "t": round(t, 2), "bit_rate": br, "slot": slot,
                           "pdu": pdu_octets(raw).hex(), "required": strong, "snr_db": round(snr, 1)})
        frames.sort(key=lambda x: (x["t"], x["freq_khz"]))
        start = rec_start + ex["t0"]
        cases.append({
            "id": ex["name"].rsplit(".", 1)[0],
            "source": "real-recording",
            "description": ex["note"],
            "input": {"file": ex["name"], "kind": "audio" if "audio_khz" in ex else "iq",
                      "sample_rate": rate, "center_hz": ex.get("center"), "channel_khz": ex.get("audio_khz"),
                      "channels_khz": ex["channels"], "start_utc_epoch": start, "time_zone": "UTC"},
            "expected": {"frames": frames},
            "provenance": {"recording": rec_name, "t0_s": ex["t0"], "dur_s": ex["dur"], "decimation": ex["decim"]},
            "req": ["DEC-01", "DEC-04", "DEC-05", "DEC-06"] + (["DEC-03"] if "audio_khz" in ex else []),
        })
        print(ex["name"], len(frames), "frames,", sum(x["required"] for x in frames), "required")
    (OUT / "real.json").write_text(json.dumps({"cases": cases}, indent=1) + "\n")


if __name__ == "__main__":
    main()
