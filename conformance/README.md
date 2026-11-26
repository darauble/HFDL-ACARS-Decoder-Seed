# Conformance suite

Language-neutral test vectors for the HFDL-ACARS decoder. An implementation conforms when it reproduces every **normative** expected result here. The vectors are JSON (plus WAV files), so a runner can be written in any language.

## Layout

| File | Suite | Normative | What it covers | Made by |
|---|---|---|---|---|
| `frame/decode.json` | frame-decode | yes | A frame's data symbols and mode → its octets, all eight modes, with symbol errors | `tools/make_synthetic.py`, checked by `tools/frame_check.py` |
| `iq/real.json` + `iq/2026*.wav` | iq-decode | yes (`required` frames) | Excerpts of real recordings (8.9 and 10 MHz, I/Q and USB audio) → frames | `tools/make_iq_vectors.py` + the reference |
| `iq/synthetic.json` + `iq/*synth*.wav` | iq-decode | yes | Synthetic frames: all modes, two channels, offsets, noise, silence | `tools/make_synthetic.py`, all found by the reference |
| `parse/sequence.json` | parse-sequence | yes | Every good frame of two 37-minute recordings, parsed in order → 1199 messages | `tools/make_parse_vectors.py` + the reference |
| `parse/acars.json` | parse-acars | yes | ACARS blocks: checks, fields, reassembly, timeouts | `tools/make_acars_vectors.py` + libacars |
| `parse/apps.json` | parse-apps | yes | ACARS application texts → ARINC 622, ADS-C, CPDLC, MIAM, media advisory, OHMA | `tools/make_apps_vectors.py` + libacars |
| `parse/classify.json` | parse-classify | yes | Messages → class, severity, keywords | `tools/make_support_vectors.py` (seed rules) |
| `alerts/alerts.json` | alerts | yes | Message sequences and settings → alert kinds | seed rules |
| `presentation/search_terms.json` | search-terms | yes (subset) | A message's search terms | seed rules |
| `presentation/search.json` | search | yes | Queries and filters → matching messages | seed rules |
| `aircraft/aircraft.json` | aircraft | yes | A recording's messages → the aircraft view | seed rules |
| `config/merge.json` | config-merge | yes | Three-way merge of HFDL settings | seed rules |
| `ndjson/write.json`, `ndjson/read.json` | ndjson-write, ndjson-read | yes | Day-file records written and read | seed rules |
| `time/center.json` | file-center | yes | A recording's center frequency (and metadata start) | seed rules |
| `time/file_name.json`, `time/iso8601.json`, `geo/*.json`, `ndjson/day_file.json` | as in the DSC seed | yes | Copied unchanged from the DSC seed (F-H14) | DSC seed |
| `scenarios.md` | – | yes | Given/When/Then scenarios for behaviour vectors cannot show | by hand |

`manifest.json` lists every suite with its case count. **The reference** is dumphfdl 1.7.0 with libacars 2.2.3 built by `tools/reference/` (with `reference.patch`: frame times from the sample count, the octets in its JSON). Suites marked "seed rules" were computed by a small Python rendering of the seed's rules; they check that an implementation reads the text the same way.

## File format

As the DSC seed: each suite file has `suite`, `description`, `normative`, `compare`, `cases`; each case `id`, `source` (`real-recording`, `synthetic`, `libacars-doc`), `description`, `input`, `expected`, `req`, optionally `note` and `non_normative_fields`. Some suites carry top-level data (`search.json`: `messages`).

## Comparison rules

1. **Absent is not a value.** A key absent from `expected` is not compared. Where `expected` has `null`, the implementation MUST give no value (or `decoded: null`: no application recognised the text).
2. **Trees** (`parse-*`): every key of `expected` must be present in the implementation's result, mapped to these names, with an equal value; keys the implementation has beyond them are ignored. Keys listed in the suite's `non_normative_keys` (display wording) are not compared. Lists compare element by element, in order.
3. **Floats** compare with the suite's `float_abs_tolerance`.
4. **Strings and integers** compare exactly.
5. **Frames (`iq-decode`):** for each case, every frame marked `required: true` MUST be found: same channel (`freq_khz`), the same PDU octets (`pdu`, the PDU's own octets, F-H16), and a time within **0.5 s** of `t` (seconds from the recording's first sample; the case's `start_utc_epoch` gives the absolute time). Frames with `required: false` MAY be found. Frames not listed MAY be found, if their FCS is good. A frame whose FCS fails is never a found frame. Report how many optional frames were found (informative: sensitivity).
6. **Recordings** are 16-bit WAV: I/Q as 2 channels (I left), or audio as 1 channel; their `input` gives the rate, the center (I/Q) or the channel (audio), and the channels to decode.
7. **Order:** `parse-sequence` and `parse-acars` cases must be run in the order given, with one parser state per case, the times given (`t`, seconds) as the frame times.
8. **Time zones:** cases with a `time_zone` run with that IANA zone as the local zone.

## Not covered by vectors

- Sensitivity beyond the required frames (informative, rule 5).
- The ground-station table updated from the air: no complete system table was received in the recordings; `scenarios.md` covers it with a synthetic table.
- Enrichment files and online lookups: `scenarios.md` with stubs.
- The user interface: reviewed against `spec/07-ui/`.
