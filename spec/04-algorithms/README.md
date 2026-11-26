# Algorithms: from samples to messages

How the decoder turns samples into HFDL messages, as pseudocode with the reasons behind each step. The data it works on is `../03-domain/`; the results it must produce are fixed by `../../conformance/`.

## The pipeline

```
 samples ──► 1 RECEIVER ──► frame symbols ──► 2 FRAME DECODER ──► frame octets ──► 3 PARSER ──► message records
 (I/Q or     01-receiver.md  (per channel)     02-frame.md         (one per frame)    03-parser.md   (one per SPDU / LPDU)
  audio)                                                                                   │
                                     4 SUPPORT: time, distance, enrichment, search, ◄─────┘
                                     alerts, lookups, settings  (04-support.md)
```

| Stage | Input | Output | File |
|---|---|---|---|
| 1 Receiver | complex samples of a band, or the audio of one channel | per channel and frame: the M1 mode, the data symbols with their phase resolved, the frame time, signal level, noise and frequency error | `01-receiver.md` |
| 2 Frame decoder | a frame's data symbols and its mode | the frame's octets | `02-frame.md` |
| 3 Parser | a frame's octets, its channel and time, and the session's tables | message records | `03-parser.md` |
| 4 Support | message records, user input | times, distances, enrichment, search hits, alerts, merged settings | `04-support.md` |

## What is normative here

| Stage | What is required | How it is checked |
|---|---|---|
| 1 + 2 | For each test recording: every **required** frame, with its PDU octets exactly, its channel and its time within 0.5 s; no frame whose FCS fails (F-H17) | `iq/real.json`, `iq/synthetic.json` |
| 2 | The bit chain exactly (`physical-layer.md` §3 to §7): clean symbols give exactly the octets | `frame/decode.json` |
| 3 | The parser as written: every field, exact; the tables' rules | `parse/*.json` |
| 4 | The algorithms as written | `time/`, `geo/`, `ndjson/`, `presentation/`, `alerts/`, `config/` |

The receiver's method (`01-receiver.md`) is informative: it is the method of dumphfdl, which decodes real HF signals. A different method passes if it finds the required frames in the test recordings. Frames the reference found only weakly are `optional`: finding them is better, not required; how many it finds is reported as its sensitivity (informative).
