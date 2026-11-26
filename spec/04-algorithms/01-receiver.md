# 1 Receiver

From samples to frames. **Informative method, normative output** (`README.md`). The method is dumphfdl 1.7.0's, which decodes real HF reception; its constants are given so an implementation can start from a working point.

## 1.1 Inputs

| Input | What it is | Channels |
|---|---|---|
| **I/Q band** | complex samples (a baseband recording, or an SDR) at rate `fs`, centred on `center_hz` | every HFDL channel whose signal (assigned + 0 to + 3 kHz) lies inside ±0.45 × `fs` of the center, or the channels the user lists |
| **Audio** | real samples of one channel from an SSB receiver in USB, tuned to the assigned frequency, at rate `fs` (e.g. 48 kHz) | exactly one: the label's frequency. The signal is at 1440 Hz audio |

- An I/Q recording names its center frequency in its file name (`…_8902500Hz…`, `…_8902.5kHz…`) or in its metadata (`04-support.md` §4.1); without one, the user gives it.
- An I/Q WAV is 2 channels, I then Q; formats as `DEC-07`.
- Audio is turned into complex baseband by taking the analytic signal (a Hilbert filter) and mixing by −1440 Hz; from there it is processed like one I/Q channel at 0 Hz.

## 1.2 Per channel: to symbols

Every channel is processed by its own instance; channels share nothing but the input samples (`DEC-09`).

1. **Channel filter and rate.** Shift the channel's signal center (assigned + 1440 Hz) to 0 Hz, low-pass (transition about 250 Hz; dumphfdl uses an FFT channelizer), resample to **5400 samples/s** (3 per symbol).
2. **Gain control.** An AGC on the complex samples (liquid `agc_crcf`, bandwidth 0.01). The signal level is the AGC's level estimate.
3. **Noise floor.** While no frame is being read, every 256 samples: `noise = 0.65 × noise + 0.35 × min(noise, level) + 1e-6`, starting from 1.0.
4. **Matched filter.** The 19-tap filter of `tools/hfdl_tx.py` (`PULSE`).
5. **Symbol timing.** A polyphase symbol synchroniser (liquid `symsync_crcf`, Kaiser, 3 samples per symbol, delay 3, β 0.9, 16 filters, loop bandwidth 0.001) giving 2 outputs per symbol; the second of each pair is the symbol.
6. **Carrier.** A Costas loop on each output: `out = in × e^(−jφ)`; per symbol `φ += dφ` (wrapped to ±π); after the decision, with the phase error `e` limited to ±1: `φ += 0.1 e`, `dφ += 0.00047 e`. While searching (A1), if `|dφ| > 0.25` the loop and the timing are reset. The frequency error shown is `dφ × 1800 / 2π` Hz at the second A.
7. **Equaliser.** An LMS equaliser of 15 taps on the 2-per-symbol stream (liquid `eqlms_cccf`, low-pass start 0.45, bandwidth 0.1), trained on the known `T` symbols, free-running on data.
8. **Decision** for the loop's phase error: BPSK in the preamble and training, the mode's PSK in data segments.

If 13 frames' worth of symbols pass without a frame, the loop and the timing are reset.

## 1.3 Finding a frame

States, with the constants that work:

| State | Wait for | Then |
|---|---|---|
| A1 search | every symbol: correlation `c = 2 × (matching bits of the last 127 BPSK bits with A) / 127 − 1` | if `|c| > 0.36`: the phase is inverted if `c < 0` (`physical-layer.md` §2); wait 127 symbols → A2 |
| A2 check | after 127 symbols, the same with the next 127 bits | if `|c| > 0.30`: frame found; its time is now − (448 + 254) symbols; → M1. Else retry up to 3 times (one symbol later each), then A1 search |
| M1 | after 127 more bits: correlate with the eight M1 sequences | the best, if `|c| > 0.30`: the mode; → skip M2 (15 symbols). Else A1 search |
| Training | 9 × T, equaliser trained | → data |
| Data | 30 data symbols, then 15 T (training again), N times | after the last T: the frame is complete (§1.4) |

Training bits are compared with `T` to count bit errors; the error rate is a quality figure (informative).

## 1.4 Output of a frame

- the channel (assigned frequency in kHz);
- the M1 mode (0..7);
- the frame time (`physical-layer.md` §9), from the sample position of the recording, or the computer clock live;
- the `N × 30` data symbols, as complex values with the phase resolved (inverted if the preamble said so);
- the signal level and noise floor in dBFS (20 log10 of the level averaged over the frame, and of the noise floor), the frequency error in Hz.

The frame decoder (`02-frame.md`) turns the symbols into octets. A frame whose octets fail every check (`03-parser.md`) still counts as a frame received with errors.

## 1.5 Timing (normative)

- The frame time is accurate to **0.5 s** against the reference (`iq/decode.json`); it is derived from the sample count, never from the computer clock, for a recording.
- Sample numbers never wrap (`DEC-11`).
