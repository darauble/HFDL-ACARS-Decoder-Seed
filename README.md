# HFDL-ACARS decoder: seed

A **seed** (blueprint) for building a decoder of aeronautical **HFDL** (High Frequency Data Link, ARINC 635) with full **ACARS** decoding (ARINC 618/620/622: ADS-C, FANS-1/A CPDLC, MIAM, media advisory, OHMA). It is not software. Give this directory to an AI coding agent, answer a few questions (language, UI, target platform, …), and the agent builds the software, proving correctness against the included conformance suite.

The program it describes shows what aircraft and ground stations send over HF: the message list and one message in full, the aircraft heard (registration, flight, type, airline, last position and its distance from you), and the ground stations. Messages with emergency content raise an alert.

It follows the form of the DSC decoder seed (`../DSC-Decoder-Seed`), so one program can implement both (`spec/02-architecture.md` §5).

> **Status:** complete draft, awaiting review (2026-11-25). Steps 1 to 5 are done; step 6 (a clean-room build by a fresh agent) is next.

**To use it:** give this directory to a coding agent and tell it to follow `AGENTS.md`; answer the questionnaire when the agent asks.

| Step | Part | Status |
|---|---|---|
| 1 | `spec/03-domain/`: the physical layer, the PDU layers, ground stations, ACARS and its applications, as text and data | done (draft): physical and PDU layers verified by a round trip through dumphfdl; ACARS and applications from libacars 2.2.3 |
| 2 | `spec/04-algorithms/`: receiver (informative method, normative output), frame decoding, parsing, reassembly, support algorithms | done (draft) |
| 3 | `spec/`: requirements, architecture, data schemas, state machines, UI behaviour and mockups | done (draft), awaiting review; mockups in `spec/07-ui/mockups/` |
| 4 | `conformance/`: vectors from real recordings (reference output from dumphfdl) and synthetic frames from `tools/` | done: 20 suites, 291 cases (`conformance/manifest.json`); two 37-minute recordings of 2026-11-25 (8.9 and 10 MHz, F-H18), six excerpts, 1199 parsed messages, 52 application texts, 19 ACARS sequences; synthetic frames in all modes |
| 5 | `interview.yaml` + `AGENTS.md`: the questions and the agent's procedure | done (draft): 14 questions, including hosting in a multi-decoder program; milestones M0 to M8 |
| 6 | Clean-room validation with a fresh agent | – |

This directory is complete on its own: nothing outside it is needed. `tools/` holds the scripts that made the synthetic vectors (Python 3 with NumPy); an implementation does not need them.

## Sources and credits

- **dumphfdl** by Tomasz Lemiech (GPL-3.0-or-later): the physical layer, the PDU layers and the ground-station table were taken from it and checked against it.
- **libacars** by Tomasz Lemiech (MIT): the ACARS layer and its applications, and the FANS-1/A CPDLC ASN.1 module.
- ARINC 635-4, 618, 620, 622 and RTCA DO-258A are the standards behind them; they are not public, and this seed does not quote them.
