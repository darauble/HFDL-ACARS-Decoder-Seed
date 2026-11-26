# Specification

What to build. It does not depend on any programming language. Read it in this order:

| Part | What it answers | Normative? |
|---|---|---|
| `01-requirements.md` | What the software must do: requirement IDs, feature groups, how each is verified | yes |
| `02-architecture.md` | Which parts there are, what each may do, threading rules | the boundaries and rules; names are free |
| `03-domain/` | HFDL on the air and in octets, ground stations, ACARS and its applications, as text and data | yes |
| `04-algorithms/` | Samples → frames → octets → messages, and the support algorithms | results yes; DSP method informative |
| `05-data/` | Every file format: day-file record, settings, aircraft and airport tables | yes |
| `06-behaviour.md` | State machines: session mode, channels, messages, alerts, lookups | yes |
| `07-ui/` | What every front end shows and offers; the search terms; mockups | the content and the search terms; layout free |

How it is checked:

- `../conformance/` holds the vectors. Each case cites the requirement IDs it proves.
- `../conformance/FINDINGS.md` records the questions that came up and what was decided. Its decisions are part of the specification. HFDL findings are numbered `F-H…`.

The words MUST, SHOULD and MAY are used as in RFC 2119.
