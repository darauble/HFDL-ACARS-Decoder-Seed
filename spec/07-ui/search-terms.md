# Search terms

**Normative** (`VIEW-06`, test `presentation/search_terms.json`). The search (`04-support.md` §4.6) matches each word against these texts of a message, one text at a time. Absent values give no term. Texts are as listed; the matching lowercases both sides (ASCII).

| Term | Example |
|---|---|
| frequency, as `8942` | `8942` |
| direction: `uplink` or `downlink` | `downlink` |
| the class name (`03-parser.md` §3.4) | `acars`, `logon` |
| the severity: `emergency`, `caution` | `caution` |
| each matched keyword | `FIRE` |
| ground station ID, and its name | `7`, `Shannon, Ireland` |
| AC ID | `23` |
| ICAO address (6 hex digits, upper case) | `152060` |
| registration (dots trimmed) | `RA73824` |
| flight ID (spaces trimmed), from any layer | `U62905` |
| aircraft type code, type, operator, airline (enrichment) | `A320`, `Aeroflot` |
| ACARS label, and label/sublabel (`H1/CF`), MFI, message number | `H1`, `H1/CF`, `C00A` |
| the ACARS text (joined when complete), as one term | `MPF/DBN … FIRE LOOP B FAULT …` |
| the application's name: `ads-c`, `cpdlc`, `miam`, `media advisory`, `ohma` | `cpdlc` |
| each CPDLC element's text with values, and each text value | `CLIMB TO AND MAINTAIN FL350` |
| each ADS-C tag's name | `Emergency basic report` |
| MIAM and OHMA text | |
| route airports: ICAO and IATA codes, names | `UUEE`, `SVO` |
| the source label and file name | `20261125T190000_8902500Hz.wav` |

A word never spans two terms: `fire loop` as one search is two words, each matching somewhere. There is no term for link traffic: `link` would match every `uplink` and `downlink`; the "hide link traffic" filter does that job.
