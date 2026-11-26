# Scenarios

Behaviour that vectors cannot show: concurrency, files over time, sources, tables, lookups. Each has an ID (`SC-…`) and its requirements. The implementation writes each one as an automated test named after the ID. The DSC seed's scenarios with the same ID apply as they are, with "channel" read as "source" (marked *as DSC*).

## Test seams

The implementation provides:

- the message, config and data directories as parameters (temporary directories in tests);
- a clock and a time zone that tests set;
- frame injection: a way to hand the parser frames (channel, time, octets) without samples;
- message injection into the session, as if decoded;
- fake sources: an I/Q source fed from a WAV file in real time or faster, an audio source likewise, a device that is present or absent on demand;
- a lookup stub: an HTTP server, or a function in place of the HTTP client, answering per key with a JSON body, a status code or a network error, and counting requests.

## Decoding

- **SC-DEC-09** (`DEC-09`). Given `iq/20261125T095809_iq50k_8961000Hz.wav` decoded as one source with its five channels, and the same file decoded five times, each as a source with one channel. Then the required frames of each channel are found in both runs, with the same octets.
- **SC-DEC-11** (`DEC-11`). Given a source fed with 2^32 + 10 000 samples of silence followed by the frames of `iq/synthetic.json` case `synth-all-modes`. Then all eight frames are found, with times after 2^32 samples correct to 0.5 s.

## Parsing

- **SC-PAR-04** (`PAR-04`, F-H06). Given injected frames on 8942 kHz: at t = 0 a logon confirm assigning AC ID 46 to ICAO 151DAD; at t = 10 a downlink performance data from AC ID 46; at t = 20 the same on 8977 kHz; at t = 3700 the same on 8942 kHz. Then the message at 10 has ICAO 151DAD (from the table), the one at 20 none (another channel), the one at 3700 none (expired after 1 h without a new confirm). Given then a logoff request for 151DAD on 8942 and a downlink from AC ID 46: no ICAO.
- **SC-PAR-07** (`PAR-07`). Given a synthetic system table of version 53 (`tools/hfdl_pdu.py` can build one: two parts of a table with three stations, one new), injected as two HFNPDUs out of order. Then: after the first part, the table in use is still 52; after the second, it is 53, the new station appears without a name, the known ones keep their names, the table file is written; a restart loads 53. A table of version 51 arriving next changes nothing. A squitter saying version 54 gives one notice.

## Storage, viewing, alerts

- **SC-STO-03, SC-STO-07, SC-STO-08, SC-VIEW-02, SC-VIEW-10, SC-ALR-05, SC-CFG-04, SC-NFR-03** *as DSC*, with HFDL records.
- **SC-NFR-02** (`NFR-02`). Given random octets (10 000 frames of each mode's length), random ACARS texts for every label of `acars.md` §4, truncated and bit-flipped copies of every `parse-*` input, and random day-file lines. Then nothing crashes or hangs, and every result is either a message, an error message, or nothing.

## Sources (group `live`)

- **SC-CH-04, SC-CH-05** *as DSC*: staged sources start and stop together; staged live sources persist and are restored, absent devices INACTIVE.
- **SC-CH-06** *as DSC* (CH-08 there): while decoding, opening files and changing the message directory are refused.

## Aircraft

- **SC-AC-04** (`AC-04`). Given the watch list `["RA73824", "4CA2D8"]` and injected messages from RA73824 (ACARS) and from ICAO 4CA2D8 (logon request). Then both aircraft are marked watched in the aircraft view and their messages in the list, a watch alert is raised for each once in 30 minutes, and the list survives a restart.

## Enrichment and lookups (groups `enrich`, `lookup`)

- **SC-ENR-03** (`ENR-03`). Given an aircraft CSV in the OpenSky layout (extra columns, quoted fields, a row without `icao24`), an airlines file and an airports file. Then a message from ICAO 151DAD shows the file's registration, type and operator; a flight `AFL1563` shows the airline; the bad row is skipped; a missing file gives a notice, not a failure.
- **SC-LKP-02** (`LKP-02`). Given hexdb on and the stub. When ten downlink messages from the same ICAO arrive within a minute, then exactly one aircraft request is made; when a 404 comes back, no request is made for that key for 24 h; requests to the stub are never closer than 1 s.
- **SC-LKP-03, SC-LKP-04, SC-LKP-05** *as DSC* (off the decoding path, failure told once, pending records written on quit), with the stub answering hexdb's and adsbdb's formats (`04-support.md` §4.11).
