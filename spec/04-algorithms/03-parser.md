# 3 Parser

From a frame's octets to message records. **Normative**: every field, and the rules of the session's tables. The layouts are `03-domain/`; this file says how they are applied, what one message is, and what it carries.

## 3.1 One parser per session

- All channels' frames go through **one** parser, in a fixed order: by the frame's end time (the instant its last symbol was received), then by frequency, lowest first. The parser owns the session's state: the AC ID table (`pdu-layers.md` §8), the system table (`ground-stations.md` §3), and the reassembly tables of ACARS, MIAM files and OHMA (`acars.md` §3, `applications.md` §4, §6).
- Every time-dependent rule (reassembly timeouts, AC ID table expiry) uses the **frame time** (`physical-layer.md` §9), never the computer clock, so that a recording parses the same at any speed.
- The state is not persisted (F-H06). Opening a day file never touches it.

## 3.2 What one message is

| Frame | Messages |
|---|---|
| SPDU, FCS good | one message of kind `squitter` |
| MPDU, header FCS good | one message per LPDU in it (`pdu-layers.md` §5.3), kind `lpdu`; an LPDU with a bad FCS or too short is not a message (counted, §3.5) |
| anything else (bad FCS, too short, a truncated LPDU list) | no message; counted per channel as a frame with errors (§3.5) |

## 3.3 Parsing one LPDU

```
parse_lpdu(lpdu_octets, mpdu_context, frame):
    m = new message: kind lpdu, direction, gs_id, ac_id, freq, frame time and signal figures
    m.pdu = lpdu_octets                                   # lossless record, with its FCS
    m.lpdu_type = octet 0; parse the fixed body (pdu-layers.md §6)
    apply the AC ID table:
        logon confirm / resume confirm  → set (freq, assigned AC ID) = ICAO
        logoff request / logon denied   → remove the entry of that ICAO on freq
    m.icao = ICAO in the LPDU if it has one,
             else the AC ID table's entry for (freq, m.ac_id) if any        # downlink: source; uplink: destination
             else ABSENT;  m.icao_source = lpdu | table | ABSENT
    if octets remain: parse the HFNPDU (pdu-layers.md §7)
        system table part → store it; if it completes a table: m.systable = the complete table
                             (and update the table in use, ground-stations.md §3)
        enveloped data    → parse the ACARS block (acars.md), reassemble, decode the application
    m.position = reported position (pdu-layers.md §9), with its time and source
    classify(m)                                            # §3.4
    return m
```

**Stored context.** A message keeps, besides its octets, what the session's state contributed, so that reading it back needs no state (`STO-05`):

| Key | Content |
|---|---|
| `icao`, `icao_src` | the resolved ICAO address and where it came from |
| `reasm` | ACARS reassembly status: `skipped`, `in_progress`, `complete`, `duplicate`, `out_of_sequence`, or ABSENT (no ACARS) |
| `joined` | the joined ACARS text, only on the block that completed a message |
| `file` / `ohma` | the joined MIAM file or OHMA message text, only on the message that completed it |
| `systable` | the octets of a complete system table, only on the message that completed it |

Everything else of a message is derived from its octets and this context by the rules of `03-domain/`, the same way when decoding and when reading a day file.

## 3.4 Classification

Each message gets a **class** (what it is, for the list's type column and filters) and a **severity**.

**Class**, the first that applies:

| Class | When |
|---|---|
| `squitter` | kind squitter |
| `cpdlc`, `adsc`, `miam`, `media`, `ohma` | the ACARS text was decoded by that application |
| `acars` | an ACARS block (any other label or undecoded text) |
| `logon` (0x8F, 0xBF), `logon_resume` (0x4F), `logon_confirm` (0x9F, 0x5F), `logoff` (0x3F), `logon_denied` (0x2F) | by the LPDU type, whatever HFNPDU follows (a logon request with frequency data is `logon`; its position still counts) |
| `systable`, `perf`, `freq`, `echo`, `systable_req` | by the HFNPDU type (0xD0, 0xD1, 0xD5, 0xDE, 0xD2) in an unnumbered (acknowledged) data LPDU |
| `other` | anything else (an LPDU of unknown type, an HFNPDU of unknown type or protocol) |

**Severity:**

| Severity | When |
|---|---|
| `emergency` | a CPDLC downlink with dM55 or dM56 (`applications.md` §3.3) as its first or a further element; an ADS-C emergency basic report (tag 9) in a downlink; a text that matches an **emergency keyword** (§3.6) |
| `caution` | a text that matches a **caution keyword** (§3.6) |
| `link` | class `squitter`, `logon*`, `logoff`, `systable*`, `perf`, `freq`, `echo`; class `acars` with label `_d` or `Q0` and no text; class `media` |
| `routine` | everything else |

`link` is the "noise" the list hides by default (`VIEW-…`). Its messages are still stored and still update the aircraft and ground-station views.

## 3.5 Counters per channel

Per channel, since its start: frames found (A2), frames decoded (FCS good), frames with errors, LPDUs with errors, messages by class. They are shown in the channel view (`CH-06`) and are not stored in day files.

## 3.6 Keywords

The texts searched for keywords are: the ACARS text (the joined text when there is one), MIAM and OHMA text, and CPDLC free text (`FANSSupplementaryInformation` and other text values). Matching:

- case-insensitive (ASCII), on **whole words**: a keyword of several words matches the same words separated by any amount of white space; a word boundary is anything but a letter or a digit. `FIRE` matches `ENG 1 FIRE LOOP B FAULT`, not `FIREWALL`.
- The lists are settings, with these defaults:
  - emergency: `MAYDAY`, `PAN PAN`, `EMERGENCY`, `SQUAWK 7700`, `SQUAWK 7600`, `SQUAWK 7500`, `HIJACK`;
  - caution: `FIRE`, `SMOKE`, `ENG FAIL`, `ENGINE FAIL`, `ENG SHUTDOWN`, `ENGINE SHUTDOWN`, `DIVERT`, `DIVERSION`, `MEDICAL`, `BOMB`, `DEPRESSURIZATION`, `DECOMPRESSION`, `FUEL LEAK`, `LOW FUEL`.
- The matched keywords are part of the message (shown in the detail, searchable).

A block of a message being joined is matched on its own text, so a message whose later blocks are lost still alerts. The alert decision (`04-support.md` §4.7) prevents a second alert when the joined message completes.
