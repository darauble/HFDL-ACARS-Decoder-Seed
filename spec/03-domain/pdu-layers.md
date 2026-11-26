# HFDL PDU layers

What a frame's octets mean, from the frame (MPDU or SPDU) down to the HFDL network layer (HFNPDU). ACARS, carried inside, is `acars.md`. **Normative**: every layout, check and rule here. Source: dumphfdl 1.7.0 (F-H01); the round trip of `tools/hfdl_pdu.py` through dumphfdl confirms the layouts it builds.

## 1 Conventions

- Octets are numbered from 0. Bits within an octet are numbered from 0 (least significant) to 7. `b[3] & 0x0F` means the low four bits of octet 3.
- Multi-octet numbers are **little-endian** (low octet first) unless a row says otherwise.
- A field the table does not name is not decoded (ARINC 635 fields that no known receiver uses: slot selection, N1/N2, acknowledgement codes, priorities). It is kept in the raw octets.
- **ABSENT** means the field was not received or not decodable. It is never 0 or an empty string in its place (`PAR-02`).

## 2 FCS (frame check sequence)

- Every MPDU header, every LPDU and every SPDU ends in a 2-octet FCS: CRC-16 with the reflected polynomial 0x1021 (0x8408), initial value 0xFFFF, final XOR 0xFFFF (the X.25 / HDLC CRC). It is sent **low octet first**.
- Check value: the FCS of the ASCII octets `123456789` is 0x906E.
- A PDU whose FCS fails is not parsed further. It is still a decoded frame: it is counted and may be kept with `fcs: false` (`spec/05-data/`).

## 3 Which PDU

The first octet's bit 0 says: 1 = MPDU (media access, carries LPDUs), 0 = SPDU (squitter, a ground station's broadcast).

## 4 SPDU: squitter

A ground station sends a squitter on each of its frequencies every 32 s, in slot 0. Exactly 66 octets: 64 octets of data and the FCS over them. Shorter: an error.

| Octets / bits | Field | Meaning |
|---|---|---|
| `b[0]` bit 1 | RLS | the reliable link service is in use |
| `b[0]` bits 2..3 | version | squitter version |
| `b[0]` bit 5 | ISO 8208 | supported |
| `b[0]` bits 6..7 | change note | 0 none, 1 channel down, 2 upcoming frequency change, 3 ground station down |
| `b[1]` bits 0..6 | GS ID | the sending ground station (`ground-stations.csv`) |
| `b[1]` bit 7 | UTC sync | the station's clock is synchronised to UTC |
| `b[2]`, `b[3]` bits 0..3 | frame index | 12 bits: the TDMA frame number |
| `b[3]` bits 4..7 | frame offset | |
| `b[52]` bits 0..3 | minimum priority | |
| `b[53]`, `b[54]` bits 0..3 | system table version | 12 bits |
| `b[54]` bits 4..7, `b[55]`, `b[56]` | frequencies in use (own) | 20-bit mask: bit i = the station's frequency i (`ground-stations.csv`) |
| `b[57]` bits 0..6 / bit 7 | 2nd GS ID / UTC sync | another station's status |
| `b[58]`, `b[59]`, `b[60]` bits 0..3 | 2nd frequencies in use | 20-bit mask |
| `b[60]` bits 4..7, `b[61]` bits 0..2 | 3rd GS ID | 7 bits: low four from `b[60]`, high three from `b[61]` |
| `b[61]` bit 3 | 3rd UTC sync | |
| `b[61]` bits 4..7, `b[62]`, `b[63]` | 3rd frequencies in use | 20-bit mask |
| `b[64]`, `b[65]` | FCS | over `b[0..63]` |

A 20-bit mask built from parts takes the parts in the order listed, lowest bits first: e.g. the own mask is `(b[54] >> 4) | (b[55] << 4) | (b[56] << 12)`.

## 5 MPDU

An MPDU carries one or more LPDUs, from one aircraft to a ground station (downlink) or from a ground station to one or more aircraft (uplink). `b[0]` bit 1 is the direction: 1 downlink, 0 uplink.

### 5.1 Downlink header

| Octets / bits | Field |
|---|---|
| `b[0]` bits 2..5 | LPDU count `n` (1..15) |
| `b[1]` bits 0..6 | destination GS ID |
| `b[2]` | source AC ID |
| `b[3..5]` | not decoded |
| `b[6 .. 6+n-1]` | one octet per LPDU: its length minus 1 |
| next 2 octets | FCS over `b[0 .. 6+n-1]` |

### 5.2 Uplink header

| Octets / bits | Field |
|---|---|
| `b[0]` bits 4..6 | aircraft count minus 1 (1..8 aircraft) |
| `b[1]` bits 0..6 | source GS ID |
| `b[1]` bit 7 | UTC sync |
| then, per aircraft | AC ID (1 octet); an octet whose bits 4..7 are its LPDU count `m`; `m` octets: each LPDU's length minus 1 |
| next 2 octets | FCS over the whole header |

The header's length is known only after reading each aircraft's count. If the MPDU ends before the header and FCS are complete, it is an error (too short).

### 5.3 The LPDUs

After the header's FCS come the LPDUs, back to back, in header order (for an uplink: the first aircraft's LPDUs, then the next aircraft's). Each LPDU's length comes from its length octet (+1). An LPDU that would run past the end of the frame stops the parsing of that MPDU: the LPDUs before it are kept, it and those after it are dropped (F-H04).

Each LPDU inherits from its MPDU: the direction, the ground station (source of an uplink, destination of a downlink), the aircraft (source of a downlink; for an uplink, the aircraft whose list it is in), and the frequency.

## 6 LPDU

`b[0]` is the type. The last two octets are the LPDU's own FCS over all the octets before them. Shorter than 3 octets, or a bad FCS: an error LPDU (kept as such, not parsed).

| Type | Name | Body after the type octet |
|---|---|---|
| 0x0D | Unnumbered data | an HFNPDU |
| 0x1D | Unnumbered acknowledged data | an HFNPDU |
| 0x2F | Logon denied | ICAO (3), reason (1) |
| 0x3F | Logoff request | ICAO (3), reason (1) |
| 0x4F | Logon resume | ICAO (3), then optionally an HFNPDU |
| 0x5F | Logon resume confirm | ICAO (3), assigned AC ID (1), 3 more octets |
| 0x8F | Logon request (normal) | ICAO (3), then optionally an HFNPDU |
| 0x9F | Logon confirm | ICAO (3), assigned AC ID (1), 3 more octets |
| 0xBF | Logon request (DLS) | ICAO (3), then optionally an HFNPDU |
| other | unknown | kept raw |

- **ICAO address:** three octets, most significant first, and **each octet bit-reversed** (bit 7 ↔ bit 0). Shown as 6 upper-case hex digits, e.g. `151DAD`.
- A fixed body shorter than its table length makes the LPDU an error. Octets left after a fixed body are an HFNPDU (logon requests often carry frequency data).
- Logoff reasons: 1 not within slot boundaries, 2 downlink set in uplink slot, 3 RLS protocol error, 4 invalid aircraft ID, 5 the ground station does not support RLS, 6 other; other values: reserved.
- Logon denied reasons: 1 aircraft ID not available, 2 the ground station does not support RLS; other values: reserved.

## 7 HFNPDU (HF network layer)

`b[0]` must be 0xFF; otherwise the octets are an unknown protocol (kept raw). `b[1]` is the type.

| Type | Name | Layout (from `b[2]`) |
|---|---|---|
| 0xD0 | System table (partial) | §7.4 |
| 0xD1 | Performance data | §7.2, exactly 47 octets from `b[0]` |
| 0xD2 | System table request | `b[2..3]`: request data (16 bits); 4 octets |
| 0xD5 | Frequency data | §7.3, at least 15 octets |
| 0xDE | Delayed echo | no fields |
| 0xFF | Enveloped data | `b[2]` = 0x01 (SOH), then an ACARS block (`acars.md`). Anything else: unknown protocol |

Shorter than the layout needs: an error HFNPDU.

### 7.1 Common fields

- **Flight ID**: 6 ASCII characters, as sent (trailing spaces kept in the raw value, trimmed for display and search).
- **Position**: 5 octets, `p[0..4]`. Latitude = `p[0] | p[1] << 8 | (p[2] & 0x0F) << 16`, longitude = `(p[2] >> 4) | p[3] << 4 | p[4] << 12`. Each is a 20-bit two's complement number `v`, and the degrees are `v × 180 / 0x7FFFF` (resolution about 0.00034°, 38 m).
- A position is **valid** only if |lat| ≤ 90 and |lon| ≤ 180. Aircraft send 180.0 (0x7FFFF) for "unknown"; such a position is ABSENT, not shown on a map, and not used for distances (F-H05).
- **UTC time**: 2 octets, the seconds since midnight UTC divided by 2. Shown as `hh:mm:ss`.

### 7.2 Performance data (0xD1)

| Octets | Field |
|---|---|
| 2..7 | flight ID |
| 8..12 | position |
| 13..14 | UTC time |
| 15 | version |
| 16 | flight leg |
| 17 bits 0..6 | GS ID (the station it is logged on to) |
| 18 | frequency index (of that station) |
| 19..20, 21..22 | frequency search count: previous leg, this leg |
| 23..24, 25..26 | HFDL disabled duration (s): previous leg, this leg |
| 27..30 | MPDUs received, per rate: 1800, 1200, 600, 300 bit/s (one octet each) |
| 31..34 | MPDUs received with errors, same order |
| 35..36 | SPDUs received |
| 37 | SPDUs missed |
| 38..41 | MPDUs transmitted, same order as 27..30 |
| 42..45 | MPDUs delivered, same order |
| 46 bits 0..3 | last frequency change cause: 0 first search in this flight leg, 1 too many NACKs, 2 SPDUs no longer received, 3 HFDL disabled, 4 GS frequency change, 5 GS or channel down, 6 poor uplink channel quality, 7 no change; others unknown |

### 7.3 Frequency data (0xD5)

| Octets | Field |
|---|---|
| 2..7 | flight ID |
| 8..12 | position |
| 13..14 | UTC time |
| 15 + 6i .. 20 + 6i | up to 6 entries, while 6 whole octets remain: `e[0]` bits 0..6 GS ID; propagating frequencies = `e[1] \| e[2] << 8 \| (e[3] & 0x0F) << 16`; tuned frequencies = `(e[3] >> 4) \| e[4] << 4 \| e[5] << 12` (20-bit masks of that station's frequencies) |

"Propagating" are the station's frequencies the aircraft hears; "tuned" (dumphfdl: "listening on") are those it is listening on.

### 7.4 System table (0xD0)

The system table lists every ground station with its position and frequencies. A ground station sends it in up to 16 parts.

| Octets | Field |
|---|---|
| 2 bits 4..7 | number of parts minus 1 |
| 2 bits 0..3 | this part's number (0-based) |
| 3 bits 4..7, 4 | system table version: `(b[3] >> 4) \| b[4] << 4` (12 bits) |
| 5 .. end | this part's data |

**Reassembly.** Parts are kept per version. When every part of one version has arrived, their data, concatenated in part order, is the table. A new version's part discards the parts of the older one. Each part is still shown by itself as "partial"; the complete table is shown once, with the message that completed it.

**The complete table** is a sequence of ground-station records, read while at least 7 octets remain:

| Octets | Field |
|---|---|
| 0 bits 0..6 / bit 7 | GS ID / UTC sync |
| 1..5 | position (as §7.1) |
| 6 bits 0..2 | squitter version |
| 6 bits 3..7 | frequency count `f` (at most 20; more is an error) |
| then `f` × 4 octets | per frequency: 3 octets of BCD digits, then 1 octet whose bits 0..3 are the master frame slot |

A frequency's 3 BCD octets, `d[0..2]`, are six decimal digits, least significant first: Hz = 100 × (d[0] & 0xF) + 1 000 × (d[0] >> 4) + 10 000 × (d[1] & 0xF) + 100 000 × (d[1] >> 4) + 1 000 000 × (d[2] & 0xF) + 10 000 000 × (d[2] >> 4).

A record that runs past the end makes the whole table an error. A complete, error-free table **newer** than the one in use replaces it (`ground-stations.md` §3), keeping the station names already known.

## 8 Identities

| Identity | Size | Scope | Shown as |
|---|---|---|---|
| GS ID | 7 bits | worldwide (`ground-stations.csv`) | `7` plus the name, e.g. `7 Shannon, Ireland` |
| AC ID | 8 bits | one channel: assigned by the ground station at logon, reused after logoff | `46`, plus the ICAO address when known: `46 (151DAD)` |
| ICAO address | 24 bits | worldwide, one per airframe | 6 hex digits |
| Registration | ACARS, up to 7 characters | worldwide | e.g. `RA73752`, dots trimmed |
| Flight ID | HFNPDU or ACARS, 6 characters | one flight | e.g. `SU1003` |

- **AC ID 255** in a logon request means "not logged on yet". It never names an aircraft.
- **The AC ID table** (per receiver): a logon confirm or logon resume confirm on frequency F maps (F, assigned AC ID) to its ICAO address. A logoff request or logon denied for an ICAO address on F removes its entry. Entries expire after 1 hour without being confirmed again. The table lets an LPDU that carries only an AC ID be shown, searched and positioned with its aircraft's ICAO address (F-H06).
- An aircraft is logged on to one channel at a time; the same AC ID on another frequency is another aircraft.

## 9 Positions in a message

A message's **reported position** is, in this order:

1. a valid position in performance data or frequency data (§7.2, §7.3), with that HFNPDU's UTC time;
2. a valid position in an ADS-C report inside the ACARS message (`applications.md`), with the report's time.

Downlinks only: an uplink's position fields, if any, are not the aircraft's. A position is credited to the message's aircraft: its ICAO address from the LPDU (logon requests), else from the AC ID table, else from an ADS-C airframe ID. A position whose aircraft has no ICAO address is still shown and used for distance, but not cached per aircraft (`spec/04-algorithms/06-support.md`).
