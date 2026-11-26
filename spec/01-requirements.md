# Requirements

What the software must do. Each requirement has an **ID** (cited by the conformance vectors' `req` field), a **level** (MUST, SHOULD, MAY as in RFC 2119), a **group**, and how it is **verified**: `vector` (a suite in `conformance/`), `scenario` (a Given/When/Then in `conformance/scenarios.md`, written by the implementation as an automated test), `review` (reading the code or using the program).

## Feature groups

The interview decides which optional groups are built. A group that is built must meet all of its MUST requirements.

| Group | Contents | Optional? |
|---|---|---|
| `core` | Decode recordings (I/Q, and USB audio), parse, store day files, view and search messages, aircraft and ground stations, alerts on screen | no |
| `live` | Decode live input (an SDR's I/Q, or audio), several channels at once | yes |
| `enrich` | The user's location, distances; aircraft, airline and airport files | yes |
| `lookup` | Online aircraft and route lookups (needs `enrich`) | yes |
| `notify` | Desktop notifications and the alert sound | yes |
| `export` | Save a message as text, copy it to the clipboard | yes |

---

## DEC: decoding

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| DEC-01 | MUST | core | Decode HFDL frames (`spec/03-domain/physical-layer.md`) in all eight M1 modes from complex samples of a band, every channel in the band at once. | vectors `iq-decode`, `frame-decode` |
| DEC-02 | MUST | core | Produce, for each frame, exactly the octets of `spec/04-algorithms/02-frame.md`; clean symbols give exactly the octets sent. | vector `frame-decode` |
| DEC-03 | MUST | core | Decode one channel from the audio of an SSB receiver in USB tuned to the channel's assigned frequency (signal at 1440 Hz). | vector `iq-decode` (audio cases) |
| DEC-04 | MUST | core | Find in each test recording every required frame of the reference, with its channel and PDU octets (F-H17); extra frames are allowed (their FCS is good by definition). | vector `iq-decode` |
| DEC-05 | MUST | core | Time-stamp each frame with the instant it began: recording base time + sample position, within 0.5 s; never the computer clock for a recording. | vector `iq-decode` |
| DEC-06 | MUST | core | Read WAV files: 2-channel I/Q or 1-channel audio; PCM 8/16/24/32-bit, IEEE float 32/64-bit, plain or `WAVE_FORMAT_EXTENSIBLE`, unknown chunks skipped; also raw `.cf32` and `.cs16` I/Q with the rate given. | vector `iq-decode` |
| DEC-07 | MUST | core | Take an I/Q recording's center frequency from its metadata or file name (`04-support.md` §4.1); refuse to decode without one until the user gives it. | vector `file-name-time`; review |
| DEC-08 | MUST | core | Report no frame for silence, white noise, or a band without HFDL. | vector `iq-decode` |
| DEC-09 | MUST | core | Channels decode independently and share no state but the input samples; one parser serves them all (`03-parser.md` §3.1). | scenario `SC-DEC-09` |
| DEC-10 | SHOULD | core | Decode a 500 kS/s band with 15 channels at least 4 times faster than real time on a typical desktop CPU, and in real time on a Raspberry Pi 4. | review |
| DEC-11 | MUST | core | Decode without a time limit: weeks without a restart; sample numbers never wrap. | scenario `SC-DEC-11` |

## PAR: parsing and the message model

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| PAR-01 | MUST | core | Parse frame octets into message records by `spec/04-algorithms/03-parser.md` and `spec/03-domain/`: every field exactly; never fail. | vectors `parse-pdu`, `parse-acars`, `parse-apps` |
| PAR-02 | MUST | core | Distinguish ABSENT from any value: a field not received, not decodable or out of range is ABSENT, never 0 or empty. | vectors `parse-*` |
| PAR-03 | MUST | core | Keep each message's octets and stored context (`03-parser.md` §3.3); they are the lossless record. | vectors `parse-*`, `ndjson-read` |
| PAR-04 | MUST | core | Keep the AC ID table, the system table and the reassembly tables by their rules, with frame times (`03-parser.md` §3.1). | vectors `parse-sequence`; scenario `SC-PAR-04` |
| PAR-05 | MUST | core | Decode all ACARS applications of `applications.md`: ARINC 622 with ADS-C and FANS-1/A CPDLC (PER unaligned), MIAM (with file reassembly), media advisory, OHMA. | vector `parse-apps` |
| PAR-06 | MUST | core | Classify every message (class and severity) and find keywords (`03-parser.md` §3.4, §3.6). | vector `parse-classify` |
| PAR-07 | MUST | core | Update the ground-station table from complete system tables received on the air, and persist it (`ground-stations.md` §3). | scenario `SC-PAR-07` |

## TIM: time

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| TIM-01 | MUST | core | The UTC instant is the source of truth; the local time is UTC + the stored offset. | vectors `ndjson-*`, `iso8601` |
| TIM-02 | MUST | core | Take a recording's start time from its file name (DSC seed rules), else its modification time. | vector `file-name-time` |
| TIM-03 | MUST | core | A live frame's time is the computer clock when its first symbol arrived. | review |
| TIM-04 | MUST | core | Record the time's source: `filename`, `mtime` or `wallclock`. | vectors `ndjson-*` |
| TIM-05 | MUST | core | Format instants as ISO 8601 (`04-support.md` §4.2). | vector `iso8601` |

## STO: storage

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| STO-01 | MUST | core | Record every message, link traffic and joined blocks included. | review |
| STO-02 | MUST | core | Append each message as one line of `spec/05-data/record.schema.json` to the day file of its local date. | vectors `ndjson-write`, `day-file` |
| STO-03 | MUST | core | One append per line; two writers never interleave inside a line. | scenario `SC-STO-03` |
| STO-04 | MUST | core | Read a day file line by line; skip invalid lines. | vector `ndjson-read` |
| STO-05 | MUST | core | On reading, derive the message's fields from its octets and stored context; ignore stored derived fields and unknown keys. | vector `ndjson-read` |
| STO-06 | MUST | core | Store day files in a user-chosen directory, by default the per-user data directory + `/<project_name>/hfdl`. | review |
| STO-07 | SHOULD | core | Keep messages of different local dates in their own files even out of order. | scenario `SC-STO-07` |
| STO-08 | MUST | core | Write to the file that has the day file's name at write time; report failed writes and retry with the next record (DSC seed F-38). | scenario `SC-STO-08` |

## VIEW: messages

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| VIEW-01 | MUST | core | At start, show today's day file. | review |
| VIEW-02 | MUST | core | Open one or several day files, merged in time order. | scenario `SC-VIEW-02` |
| VIEW-03 | MUST | core | Show the message list with, per message: time, frequency, direction, ground station, aircraft (registration, flight or ICAO), class, subject, distance, severity (`spec/07-ui/README.md`). | review |
| VIEW-04 | MUST | core | Show severity without relying on colour alone. | review |
| VIEW-05 | MUST | core | Show a message's details: every decoded field of every layer, enrichment, reception, the raw octets. | review |
| VIEW-06 | MUST | core | Search by words over the search terms (`search-terms.md`). | vectors `search`, `search-terms` |
| VIEW-07 | MUST | core | Filters: hide link traffic (default on), alerts only, hide joined blocks (default on) (`04-support.md` §4.6). | vector `search` |
| VIEW-08 | MUST | core | New messages appear while decoding; follow and hold modes. | review |
| VIEW-09 | SHOULD | core | Show which day file(s) are in view and the selected message's. | review |
| VIEW-10 | MUST | core | Follow the day files in view while viewing, as the DSC seed's VIEW-10 and VIEW-11. | scenario `SC-VIEW-10` |

## AC: aircraft and ground stations

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| AC-01 | MUST | core | Show the aircraft heard in the messages in view (`04-support.md` §4.9): identity, flight, type and operator when known, last position with its age, distance, last heard, message count. | vector `aircraft`; review |
| AC-02 | MUST | core | From an aircraft, show its messages (a search for it). | review |
| AC-03 | MUST | core | Show the ground stations: ID, name, position, distance, frequencies, which were heard (squitters) and when, and the system table version. | review |
| AC-04 | MUST | core | A watch list of ICAO addresses, registrations and flights, persisted; watched aircraft stand out in every view. | scenario `SC-AC-04` |

## ALR: alerts

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| ALR-01 | MUST | core | Decide alerts by `04-support.md` §4.7: emergency always, caution if enabled (default on), watched aircraft if enabled (default on), once per message or aircraft in 30 minutes. | vector `alerts` |
| ALR-02 | MUST | core | Show an alert prominently until acknowledged; a newer one replaces it. | review |
| ALR-03 | SHOULD | notify | Sound an alert if enabled (default on). | review |
| ALR-04 | MAY | notify | Desktop notification, critical for emergency. | review |
| ALR-05 | MUST | core | Alerts only for newly decoded messages and followed lines, never for opened files. | scenarios `SC-ALR-05`, `SC-VIEW-10` |
| ALR-06 | MUST | core | The keyword lists are settings with the defaults of `03-parser.md` §3.6. | vector `parse-classify`; review |

## CH: channels and inputs

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| CH-01 | MUST | live | Decode live I/Q from an SDR (the platform's SDR library) and live audio from an input or monitor device. | review |
| CH-02 | MUST | live | A **source** is an I/Q device (with its center frequency and rate) or an audio device (with its channel). An I/Q source decodes the channels the user picks among those its band covers, all by default (`ground-stations.md` §2). | review |
| CH-03 | MUST | live | Sources are staged, then started and stopped together; staged live sources persist and are restored (as the DSC seed CH-04, CH-05). | scenarios `SC-CH-04`, `SC-CH-05` |
| CH-04 | MUST | live | Show each source and channel: state (inactive, idle, silent, activity, decoding), signal level, noise, and the counters of `03-parser.md` §3.5. | review |
| CH-05 | MUST | core | A recording is a source too (transient); its messages carry the file name and go to the day file of the recording's date. | vector `ndjson-write`; review |
| CH-06 | MUST | core | While decoding, opening other day files and changing the message directory are refused. | scenario `SC-CH-06` |
| CH-07 | SHOULD | live | Offer the HFDL bands and their centers (`ground-stations.md` §2) when staging an I/Q source. | review |

## ENR: enrichment

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| ENR-01 | MUST | enrich | The user may set their location (`04-support.md` §4.5), or none. | vector `parse-location` |
| ENR-02 | MUST | enrich | Show distances, km with NM in parentheses, to: the aircraft's reported position, the ground station, the route's airports. | vector `distance`; review |
| ENR-03 | MUST | enrich | Load the aircraft, airline and airport files (`spec/05-data/`) when the user names them. | vector `enrich` |
| ENR-04 | MUST | enrich | Store in each record what was known at reception (`04-support.md` §4.10); a later view shows that. | vectors `ndjson-*` |

## LKP: online lookups

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| LKP-01 | MUST | lookup | Off by default; hexdb and adsbdb are switched on separately; endpoints configurable (`04-support.md` §4.11). | review |
| LKP-02 | MUST | lookup | Look up only by its rules (keys, cache ages, 1 request per second per service, not-found cached). | scenario `SC-LKP-02` |
| LKP-03 | MUST | lookup | Off the decoding and UI paths; the message shows at once and is written after the lookup with its result. | scenario `SC-LKP-03` |
| LKP-04 | MUST | lookup | A failure is told once per message and never loses the record; quitting writes pending records without results. | scenarios `SC-LKP-04`, `SC-LKP-05` |
| LKP-05 | MUST | lookup | No export or bulk download of looked-up data (F-H15). | review |

## CFG, EXP, NFR

| ID | Level | Group | Requirement | Verified |
|---|---|---|---|---|
| CFG-01 | MUST | core | Persist settings (`config.schema.json`) in the per-user config directory. | review |
| CFG-02 | MUST | core | Save by the three-way merge (`04-support.md` §4.8). | vector `config-merge` |
| CFG-03 | MUST | core | Write the settings file atomically. | review |
| CFG-04 | MUST | core | A missing or unreadable settings file gives the defaults. | scenario `SC-CFG-04` |
| EXP-01 | MUST | export | Save the shown message's details as text (`<project_name>_<local time>_<aircraft>.txt`). | review |
| EXP-02 | SHOULD | export | Copy the details to the clipboard. | review |
| NFR-01 | MUST | core | Decoding, lookups and the UI never block each other. | review |
| NFR-02 | MUST | core | No crash and no hang on any input: any octets, any day-file line, any settings file, any recording. | vectors `parse-*`, `ndjson-read`, `iq-decode`; scenario `SC-NFR-02` |
| NFR-03 | MUST | core | Stopping or quitting loses no decoded message. | scenario `SC-NFR-03` |
| NFR-04 | MUST | core | No network access unless the `lookup` group is built and a service is on. | review |
| NFR-05 | SHOULD | core | The decoding and data logic is a library, separate from the front end. | review |
| NFR-06 | MUST | core | Pass every normative conformance vector. | vectors (all) |
| NFR-07 | MUST | core | Built test-first (TDD). | review: the commit history |
| NFR-08 | SHOULD | core | A program that implements this seed together with other decoder seeds (DSC, …) shares one front end, one settings file and one user location among them (`02-architecture.md` §5). | review |
