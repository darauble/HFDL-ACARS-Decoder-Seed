# AGENTS.md: how to build from this seed

You are an AI coding agent. This directory is a **seed**: a specification and a conformance suite for an HFDL (ARINC 635) decoder with full ACARS decoding. Build the software from it, in the language and form the person chooses, and prove it correct against the vectors and scenarios here. It has the form of the DSC seed (`../DSC-Decoder-Seed/AGENTS.md`); where this file says "as DSC", follow that file's text.

## 1 Read

Read everything before you plan, in this order: `README.md`; `spec/README.md`; `spec/01-requirements.md`; `spec/02-architecture.md`; `spec/03-domain/` (`README.md` first, then the physical layer, the PDU layers, ground stations, ACARS, applications, and the data files); `spec/04-algorithms/`; `spec/05-data/`; `spec/06-behaviour.md` (and the DSC seed's, which it extends); `spec/07-ui/` with the mockups; `conformance/README.md`, `conformance/scenarios.md`; `conformance/FINDINGS.md`, whose decisions are part of the specification. Do not read the suites case by case yet; the runner will.

If the interview says the build is **hosted** in an existing program, read that program's documentation and architecture too, before the plan.

## 2 Interview

Ask the questions of `interview.yaml`, as DSC: in order, a few at a time, with their `why` and default; check the constraints; write `answers.yaml`.

## 3 Plan

Write `PLAN.md`, as DSC (scope, components with interfaces and libraries, test seams, test framework, risks, milestones), with at least these risks checked early:

- the DSP speed (`DEC-10`): a 500 kS/s band with 15 channels on the target hardware;
- the ASN.1 PER decoder for CPDLC (generated from `spec/03-domain/cpdlc-fans1a.asn1`, or by hand): prove it on `parse/apps.json`'s CPDLC cases in a spike;
- raw deflate (MIAM, OHMA): the language's library;
- the SDR backend (`CH-01`), if `live` is built.

Show the plan and wait for agreement. Then decide details yourself, and ask only about findings and changes of scope.

## 4 Build

**Test-first, always (`NFR-07`)**, exactly as DSC §4: red, green, refactor; the vectors are the tests, turned on a few at a time; your own tests first for what no vector covers; commits pairing tests and code, naming the test and how it failed.

### M0: The conformance runner

As DSC M0: copy `conformance/` unchanged (the WAV files included), write the runner, check the manifest's counts, build the comparison test-first. The comparison rules here add **trees** (rule 2: expected keys present and equal, extra keys ignored, non-normative keys skipped) and **frames** (rule 5: required frames found, optional allowed). Write the mapping from your model to the reference's JSON names (F-H19) as a small, tested layer of the runner, not of the product.

### M1: Domain and frame decoder

Load `physical.json`, `ground-stations.csv`, `cpdlc-elements.csv`, `cpdlc-types.csv` from the files (or generate code from them by a kept script; never retype). Build the scrambler, the PSK mapping, the deinterleaver, the Viterbi decoder. **Closes:** `frame-decode`.

### M2: PDU parser

The FCS, SPDU, MPDU, LPDU, HFNPDU, the system table, the AC ID table (`03-parser.md`). Turn on `parse-sequence` and expect its ACARS and application keys to fail until M3; count the others. **Closes:** the PDU-level keys of `parse-sequence`.

### M3: ACARS and applications

The ACARS block and reassembly, ARINC 622, ADS-C, CPDLC, MIAM (with file reassembly), media advisory, OHMA. **Closes:** `parse-acars`, `parse-apps`, `parse-sequence`.

### M4: Classification and presentation

Class, severity, keywords; the alert decision; search terms and matching; the filters; the aircraft view. **Closes:** `parse-classify`, `alerts`, `search-terms`, `search`, `aircraft`.

### M5: Time, storage, geography, settings

**Closes:** `file-name-time`, `file-center`, `iso8601`, `day-file`, `ndjson-write`, `ndjson-read`, `distance`, `parse-location`, `config-merge`.

### M6: Receiver and recordings

Follow `spec/04-algorithms/01-receiver.md`; its method is informative, its output normative. Get `iq/synthetic.json` passing first (clean signals: a failure is a logic error), then `iq/real.json` (required frames). Report the optional frames found (sensitivity). Measure `DEC-10` now. **Closes:** `iq-decode`.

### M7: Session, optional groups, front end

The session, store, reference data and settings with their state machines (`spec/06-behaviour.md`) and threading rules; the core scenarios (`SC-DEC-09`, `SC-DEC-11`, `SC-PAR-04`, `SC-PAR-07`, `SC-STO-*`, `SC-VIEW-*`, `SC-ALR-05`, `SC-CFG-04`, `SC-NFR-03`, `SC-AC-04`); each chosen group with its scenarios (`live`: `SC-CH-*`; `enrich`: `SC-ENR-03`; `lookup`: `SC-LKP-*`); then the front end by `spec/07-ui/`, using the presentation helpers.

### M8: Hardening

`SC-NFR-02` (fuzzing every reader and the parser); the concurrency scenarios under a race detector if the language has one; CI on each chosen platform; a live run on real HFDL if `live` is built.

## 5 Rules

As DSC §5: the vectors are frozen; doubts become findings (`FINDINGS.md`, `B-01`, …, with the affected test kept failing); scope as the requirements say; requirement levels; names are free; test-first; traceability.

**Clean room.** Build only from this seed and public documentation of your language, libraries and platforms (and of ASN.1 PER, ITU-T X.691). Do **not** read the source of dumphfdl, libacars, or any other HFDL or ACARS decoder, and do not look for one. The reference build in `tools/reference/` exists to make the vectors; do not use it as a design source.

## 6 Traceability and done

As DSC §6: `TRACEABILITY.md` with one row per requirement (ID, level, group, built?, verified by, status). Done when every normative vector of the built groups passes, every scenario of the built groups passes, every MUST of the built groups is met, every SHOULD is met or explained, and the packaging chosen in the interview works from a clean checkout.
