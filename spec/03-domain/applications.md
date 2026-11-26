# ACARS applications

The protocols carried in ACARS text (`acars.md` §4 says which label tries which): ARINC 622 with ADS-C and FANS-1/A CPDLC, MIAM, media advisory and OHMA. **Normative**: detection, layouts, checks, scales, value tables and texts. Source: libacars 2.2.3 (MIT).

Bit fields marked **MSB-first** are read from a bit stream filled with the octets in order, each octet most significant bit first; an n-bit field takes the next n bits, the first of them most significant. Signed fields are two's complement of their width.

## 1 ARINC 622 (ATS applications over ACARS)

### 1.1 Detection

The text (after the sublabel and MFI) may start with `/`, which is skipped. Then the text must start with a **ground address** directly followed by an **IMI** (imbedded message identifier):

- The IMIs, searched in this order, the first one found anywhere in the text wins: `.AT1`, `.CR1`, `.CC1`, `.DR1`, `.ADS`, `.DIS`.
- The ground address is the text before the IMI's dot. It must be exactly 7 or exactly 4 characters, each an upper-case letter or a digit (`AKLCDYA`, `EDYY`).
- Anything else: not ARINC 622 (the next application is tried).

### 1.2 Layout

After the IMI's dot: the IMI (3 characters), the aircraft registration (7 characters, as in ACARS), then **hexadecimal digits** (upper or lower case), two per octet. Fewer than 3 + 7 + 4 characters there: not ARINC 622.

- Hex decoding: an odd last digit is ignored; decoding stops at the first character that is not a hex digit, keeping the octets before it.
- The last 2 octets are the **CRC**. The rest is the application's message.
- The CRC is good when CRC-16 (polynomial 0x1021, not reflected, initial 0xFFFF; for each octet `crc = (crc << 8) XOR table[(crc >> 8) XOR octet]`, 16 bits) over IMI + registration + all the octets **including** the CRC gives **0x1D0F**. A bad CRC is shown ("CRC error"); the message is decoded all the same.

| IMI | Message | Decoded as |
|---|---|---|
| `AT1` | FANS-1/A CPDLC message | CPDLC (§3) |
| `CR1` | FANS-1/A CPDLC connect request | CPDLC |
| `CC1` | FANS-1/A CPDLC connect confirm | CPDLC |
| `DR1` | FANS-1/A CPDLC disconnect request | CPDLC |
| `ADS` | ADS-C message | ADS-C (§2) |
| `DIS` | ADS-C disconnect request | ADS-C, one reason octet |

## 2 ADS-C (FANS-1/A, ARINC 745)

### 2.1 Structure

An `ADS` message is a sequence of **tags**: one octet tag number, then the tag's fields. The direction (downlink: aircraft to ground; uplink: ground to aircraft) chooses the table. Tags are read until the octets end. An unknown tag number, or a tag shorter than its layout, ends the parsing with an error ("unparseable tag n"); the tags before it are kept.

A `DIS` message has no tags: its one octet carries the disconnect reason in its **high four bits** (`octet >> 4`, as libacars reads it, F-H22): 0 reason not specified, 1 congestion, 2 application not available, 8 normal disconnect; others "unknown (n)". No octet: an error.

### 2.2 Downlink tags

| Tag | Name | Octets after the tag | Fields |
|---|---|---|---|
| 3 | Acknowledgement | 1 | contract number |
| 4 | Negative acknowledgement | 2 or 3 | contract request number; reason (0..13, more is an error); for reasons 1, 2 and 7 one more octet: 1, 2 "erroneous octet number", 7 "erroneous tag number" |
| 5 | Noncompliance notification | 2 + groups | contract request number; group count; groups (§2.5) |
| 6 | Cancel emergency mode | 0 | |
| 7 | Basic report | 10 | §2.4 |
| 9 | **Emergency** basic report | 10 | §2.4 |
| 10 | Lateral deviation change event | 10 | §2.4 |
| 12 | Flight ID data | 6 | 8 characters of 6 bits, MSB-first: a value with bit 5 clear gets 0x40 added (A..Z), with bit 5 set it is the character itself (space, digits) |
| 13 | Predicted route | 17 | MSB-first: next waypoint lat 21, lon 21, alt 16, ETA 14 (s); next+1 waypoint lat 21, lon 21, alt 16 |
| 14 | Earth reference data | 5 | MSB-first: true track invalid 1, true track 12, ground speed 13 (÷2 kt), vertical speed 12 |
| 15 | Air reference data | 5 | MSB-first: true heading invalid 1, true heading 12, Mach 13 (÷2000), vertical speed 12 |
| 16 | Meteo data | 4 | MSB-first: wind speed 9 (÷2 kt), wind direction invalid 1, wind direction 9, temperature 12 |
| 17 | Airframe ID | 3 | the ICAO address, most significant octet first (not bit-reversed) |
| 18 | Vertical rate change event | 10 | §2.4 |
| 19 | Altitude range event | 10 | §2.4 |
| 20 | Waypoint change event | 10 | §2.4 |
| 22 | Intermediate projection | 8 | MSB-first: distance 16 (÷8 NM), true track invalid 1, true track 12, alt 16, ETA 14 (s) |
| 23 | Fixed projection | 9 | MSB-first: lat 21, lon 21, alt 16, ETA 14 (s) |

### 2.3 Uplink tags and contract requests

| Tag | Name | Octets | Fields |
|---|---|---|---|
| 1 | Cancel all contracts and terminate connection | 0 | |
| 2 | Cancel contract | 1 | contract number |
| 6 | Cancel emergency mode | 1 | contract number |
| 7 | Periodic contract request | 1 + request tags | contract number, then request tags |
| 8 | Event contract request | 1 + request tags | |
| 9 | Emergency periodic contract request | 1 + request tags | |

After the contract number, request tags follow while the next octet is a request tag number in this table (an octet that is not one ends the request; it is the next uplink tag):

| Request tag | Name | Octets | Fields |
|---|---|---|---|
| 10 | Report when lateral deviation exceeds | 1 | ÷8 NM |
| 11 | Reporting interval | 1 | bits 6..7 scale (0 → 0, 1 → 1, 2 → 8, 3 → 64, as libacars, F-H12), bits 0..5 rate; interval = scale × (rate + 1) seconds (F-H22) |
| 12 | Flight ID | 1 | modulus: every n reports |
| 13 | Predicted route | 1 | modulus |
| 14 | Earth reference data | 1 | modulus |
| 15 | Air reference data | 1 | modulus |
| 16 | Meteo data | 1 | modulus |
| 17 | Airframe ID | 1 | modulus |
| 18 | Report when vertical speed is | 1 | signed 8 bits × 64 ft/min (positive: above, negative: below) |
| 19 | Report when altitude out of range | 4 | ceiling: octets 0..1 big-endian, signed 16 × 4 ft; floor: octets 2..3, same |
| 20 | Report waypoint changes | 0 | |
| 21 | Aircraft intent data | 2 | modulus; projection time (minutes) |

### 2.4 The basic report (tags 7, 9, 10, 18, 19, 20)

10 octets, MSB-first:

| Bits | Field | Value |
|---|---|---|
| 21 | latitude | coordinate (below) |
| 21 | longitude | coordinate |
| 16 | altitude | signed × 4 ft |
| 15 | time | × 0.125 s past the hour (UTC) |
| 7 | flags | bit 0: NAV redundancy (0 lost, 1 OK); bits 1..3: position accuracy (0 none, NAV capability lost; 1 < 30 NM; 2 < 15 NM; 3 < 8 NM; 4 < 4 NM; 5 < 1 NM; 6 < 0.25 NM; 7 < 0.05 NM); bit 4: TCAS (0 not available to ADS, 1 OK) |

**Scales** (v is the signed field value):

| Field | Width | Degrees or units |
|---|---|---|
| coordinate | 21 | v × (180 − 90/2^19) / 0xFFFFF |
| track, heading | 12 | v × (180 − 90/2^10) / 0x7FF; + 360 if negative |
| wind direction | 9 | v × (180 − 90/2^7) / 0xFF; + 360 if negative |
| temperature | 12 | v × (512 − 256/2^10) / 0x7FF, °C |
| vertical speed | 12 | v × 16 ft/min |
| altitude | 16 | v × 4 ft |

Shown as: lat/lon with 7 decimals, altitude in ft, time as seconds past the hour and `:mm:ss.sss`, speeds with 1 decimal kt, Mach with 4 decimals, track/heading with 1 decimal degree and "(invalid)" when the invalid bit is set.

A basic report's position is the message's reported position (`pdu-layers.md` §9) when it is valid (|lat| ≤ 90, |lon| ≤ 180). The report time is the minutes and seconds of the hour of the message's reception time: if that is more than 30 minutes after the reception, the previous hour (F-H11).

### 2.5 Noncompliance groups

Each group: tag number (1 octet); an octet with bit 7 "group unrecognized", bit 6 "whole group unavailable", bits 0..3 parameter count n. If neither flag is set and n > 0: n 4-bit parameter numbers follow, two per octet, high nibble first. The group count says how many groups; fewer octets than that make the tag an error.

### 2.6 NACK reasons

1 duplicate group tag, 2 duplicate reporting interval tag, 3 event contract request with no data, 4 improper operational mode tag, 5 cancel request of a contract which does not exist, 6 requested contract already exists, 7 undefined contract request tag, 8 undefined error, 9 not enough data in request, 10 invalid altitude range (low limit ≥ high limit), 11 vertical speed threshold is 0, 12 aircraft intent projection time is 0, 13 lateral deviation threshold is 0.

## 3 FANS-1/A CPDLC

### 3.1 Encoding

- The message (after the ARINC 622 CRC is removed) is one ASN.1 value of the module `cpdlc-fans1a.asn1`, encoded with **PER, unaligned** (ITU-T X.691): `FANSATCUplinkMessage` for an uplink, `FANSATCDownlinkMessage` for a downlink.
- An empty message (no octets) is not an error: shown as "empty".
- A decoding failure: "unparseable FANS-1/A message", with the octets in hex in the detail.
- A message is a header (message identification number 0..63, optional reference number 0..63, optional timestamp hh:mm:ss) and one message element, optionally followed by up to 4 more (uplink) or more (downlink, as the module says).

### 3.2 Texts

- Each message element is an alternative `uMn…` (uplink) or `dMn…` (downlink). `cpdlc-elements.csv` gives each element's **text**: the standard phraseology with its parameters in brackets, e.g. `CLIMB TO AND MAINTAIN [altitude]`. A message is shown as its elements' texts, then each element's parameter values.
- `cpdlc-types.csv` gives, per ASN.1 type, the **label** shown before a value and how it is shown: `number` values are multiplied by `scale`, shown with `decimals` decimals and the `unit` (e.g. `FANSVerticalRateEnglish`: × 100, `ft/min`); `time hh:mm` and `hh:mm:ss`; `latitude`/`longitude` as degrees, minutes with 1 decimal (the field is tenths of a minute) and the direction (`52 30.5' north`); `squawk code` as 4 digits; `enumerated` as the value's name; `value` as received (text or integer); `structure` as its components, each with its own label.
- A type not in `cpdlc-types.csv` is shown with its ASN.1 component name.
- **As a tree** (`parse/apps.json`, F-H19): `cpdlc-json.csv` gives per ASN.1 type its JSON key and format: `sequence` (an object of its components' keys), `choice` (an object with `choice`, the alternative's name, and `data`, the alternative's value), `element_choice` (the same plus `choice_label`, the element's text from `cpdlc-elements.csv`), `sequence_of` (an array of objects), `number` (`{"val": value × scale, "unit": unit}`), `integer`, `string` (the value as text), `enum` (the value's name), `bool`, `time` (`{hour, min}`), `timestamp` (`{hour, min, sec}`), `latitude`/`longitude` (`{deg, min (tenths ÷ 10, when present), dir}`), `beacon_code` (4 digits as a string), `label_only` (an empty object), `octets`; `omit` and types not in the table produce nothing.

### 3.3 Emergency elements

Downlink elements dM55 `PAN PAN PAN`, dM56 `MAYDAY MAYDAY MAYDAY`, dM57 (fuel and souls on board), dM58 `CANCEL EMERGENCY`, dM59 `DIVERTING TO …`, dM60 `OFFSETTING …`, dM61 `DESCENDING TO …` are the emergency message set. A message containing dM55 or dM56 is an **emergency** (`spec/04-algorithms/06-support.md`, alerts). dM57 to dM61 are shown as emergency only together with dM55 or dM56.

## 4 MIAM (media independent aircraft messaging)

### 4.1 The convergence frame

The text's first character is the frame type; the fields follow without separators (decimal digits unless said otherwise). A text that does not match its frame type's layout is not MIAM (the next application is tried).

| Character | Frame | Fields after it |
|---|---|---|
| `T` | single transfer | a MIAM core PDU (§4.2) |
| `F` | file transfer request | exactly 21 characters: file ID (3), file size (6), validity time `YYMMDDhhmmss` (12) |
| `K` | file transfer accept | exactly 10: file ID (3), segment size (1, hex digit), on-ground segment tempo (3), in-flight segment tempo (3) |
| `S` | file segment | file ID (3), segment ID (3), then segment data (a part of a core PDU) |
| `A` | file transfer abort | exactly 4: file ID (3), reason (1): 0 refused by receiver, 1 segment out of context, 2 stopped by sender, 3 stopped by receiver, 4 segment transmission failed |
| `Y` | file transfer pause | exactly 3: file ID (`FFF` = all) |
| `X` | file transfer resume | exactly 9: file ID (3, `FFF` = all), on-ground tempo (3), in-flight tempo (3) |

"Exactly n" counts the characters after any trailing CR and LF are removed.

**File reassembly:** key registration + file ID; the file transfer request starts it with the file size (segment 0, no data); segments 1, 2, … are appended in order (duplicates ignored, a gap abandons it); the file is complete when the data collected reaches the file size. Timeout 900 s from the request. The complete file is a core PDU, decoded once, with the segment that completed it.

### 4.2 The core PDU

- Text form: body padding character (`0`..`3`: the body is base85 with that many padding octets; `-`: the body is not encoded; `.`: no body), header padding character (`0`..`3`), the header in base85, `|`, the body. No `|`, an empty header, or other padding characters: not MIAM.
- **Base85:** groups of 5 characters, each `c − 33`, give a 32-bit big-endian number (4 octets); `z` alone stands for 4 zero octets. Characters left over (fewer than 5) are ignored. The padding count of octets is removed from the end.
- Header octet 0: bits 0..3 version (1 or 2; else "unsupported MIAM version"), bits 4..7 PDU type: 0 data, 1 ack, 2 aloha, 3 aloha reply (else "unknown PDU type").

**Version 1 data** (header at least 20 octets): octets 1..3 PDU length (big-endian; more than header + body: "message truncated"); 4..10 aircraft ID (7 characters); 11: bits 1..7 message number, bit 0 ack option; compression = ((octet 12 << 2) | (octet 13 >> 6)) & 7 (0 none, 1 deflate); encoding = (octet 13 >> 4) & 3 (0 ISO 5 text, 1 binary); application type = octet 13 & 0xF: 0 ACARS 2-character label, 1 ACARS 4-character (label + sublabel), 2 ACARS 6-character (label, sublabel, MFI), 3 non-ACARS 6-character; others an error. Then the application ID (2, 4 or 6 characters), then the CRC (4 octets, big-endian).

**Version 2 data** (header at least 7 octets): octet 1: message number and ack option as above; compression, encoding and application type from octets 2..3 as in version 1 (octets 12..13); application types 0..3 as version 1, and 8..15 except 13: an ID of `(type & 7) + 1` characters; then the application ID, then the CRC (2 octets, big-endian).

**Body:** deflate (raw, RFC 1951, no zlib header) when compression is 1, else as is. Then the CRC over the body as delivered:

- version 1: CRC-32, polynomial 0x04C11DB7 not reflected, initial 0xFFFFFFFF, final XOR 0xFFFFFFFF (CRC-32/BZIP2);
- version 2: CRC-16, polynomial 0x1021 not reflected, initial 0xFFFF (CRC-16/CCITT-FALSE).

A mismatch: "CRC check failed". A body that is printable text is shown as text, otherwise as hex.

**Ack** (v1: header ≥ 20 octets: PDU length, aircraft ID, octet 11 bits 1..7 acknowledged message number, octet 12 bits 4..7 transfer result, CRC at octets 16..19; v2: header ≥ 8: octet 1 bits 1..7 message number, transfer result = ((octet 1 << 3) | (octet 2 >> 5)) & 0xF, CRC at octets 4..5). Transfer results: 0 ack, 1 nack, 2 time expiry, 3 peer abort, 4 local abort.

**Aloha / aloha reply** (header ≥ 13 octets): PDU length (1..3), aircraft ID (4..10), compression mask (11: bit 0 deflate), networks mask (12: bit 0 ACARS, 1 IP middleware, 2 TCP/IP, 3 Satcom data 3, 4 UDP): what the aircraft supports (aloha) or the ground selects (reply).

## 5 Media advisory (label SA)

Text of at least 10 characters:

| Characters | Field |
|---|---|
| 1 | version: must be `0` |
| 1 | `E` link established, `L` link lost |
| 1 | the link: `V` VHF ACARS, `S` default Satcom, `H` HF, `G` Globalstar Satcom, `C` ICO Satcom, `2` VDL2, `X` Inmarsat Aero H/H+/I/L, `I` Iridium Satcom |
| 6 | time `hhmmss` UTC (hh ≤ 23, mm ≤ 59, ss ≤ 59) |
| until `/` or the end | the links now available, one character each from the same set |
| after `/` | free text |

Anything out of these rules: "unparseable media advisory". Shown as e.g. "HF link established at 12:34:56 UTC; available: VHF ACARS, HF".

## 6 OHMA (label H1)

Onboard health management messages (Boeing 737 MAX), compressed JSON.

- Recognition: the text, optionally preceded by `/` + 7-character ground address + `.` (13 or more characters, `/` at 0 and `.` at 8) or by `/` + 2 characters + `.` (8 or more, `.` at 3), starts with `OHMA` or `RYKO`. If that prefix (from the start of the text through `OHMA`/`RYKO`) appears again later, parsing restarts there (a sender bug repeats the first block). Trailing CR and LF are removed.
- The rest is base64. It must decode, else not OHMA.
- Decoded: at least 3 octets ("message too short"); the first octet's low 4 bits must be 8 (deflate, "unknown compression"); the zlib stream after the first 2 octets inflates as raw deflate ("decompression failed").
- The inflated text is JSON: an object with `version` (string), `message` (string) and optionally `convo_id` (string), `msg_seq` and `msg_total` (integers), `sym_key`, `iv`, `signature` (base64 strings, shown as hex). Otherwise "failed to decode message as JSON" / "unexpected JSON structure", and the inflated text is shown as it is.
- **Fragments:** `msg_seq` > 0 means one fragment of a message; then `convo_id` is required, and the first (`msg_seq` 1) also needs `msg_total`. Key registration + `convo_id`; fragments may arrive **in any order**; complete when `msg_total` fragments are in; timeout 1200 s. The complete message is the `message` strings concatenated in `msg_seq` order.
- The `message` (complete, or of a single message) is shown as text.
