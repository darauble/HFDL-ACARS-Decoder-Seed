# ACARS in HFDL

The ACARS block an HFDL "enveloped data" HFNPDU carries (`pdu-layers.md` §7), its fields, its check, how blocks of one message are joined, and which application decodes the text. **Normative**. Source: libacars 2.2.3 (MIT), as used by dumphfdl 1.7.0 with the HFDL bearer (F-H09).

## 1 The block

After the HFNPDU's `0xFF 0xFF` comes `SOH` (0x01), then:

| Octets | Field | Notes |
|---|---|---|
| 1 | mode | e.g. `2` |
| 7 | registration | the aircraft's registration, right-aligned, padded on the left with `.` (`.XA-ADC`); dots are trimmed for display and search |
| 1 | technical acknowledgement | `NAK` (0x15) shown as `!`, `ACK` (0x06) as `^`, otherwise the character itself (a block ID being acknowledged) |
| 2 | label | two characters; a second character `DEL` (0x7F) is shown as `d` (`_d`) |
| 1 | block ID | `0`..`9`: a **downlink** block; anything else (`A`..`Z`, …): an uplink block. A NUL block ID is shown as a space |
| 1, optional | `STX` (0x02) | present when there is text |
| n | text | |
| 1 | `ETX` (0x03) or `ETB` (0x17) | ETX: the message's last block; ETB: more blocks follow |
| 2 | block check | CRC, low octet first (§2) |
| 1 | `DEL` (0x7F) | end |

- Characters are 7-bit ASCII with a parity bit in bit 7. The parity is not checked; bit 7 is dropped from every octet before the fields are read (the block check is over the octets with it, §2).
- At least 16 octets after SOH, and the last one `DEL`, the last before the CRC `ETX` or `ETB`: otherwise the block is an **error** (kept, shown as "unparseable ACARS", raw octets in the detail).
- **No text** (the block ends right after the block ID): allowed only for an uplink, e.g. the general response `_d`. A downlink without text is an error.
- A NUL in the text is shown as `.`.

### Downlink text prefix

A downlink's text starts with:

| Characters | Field |
|---|---|
| 3 | message number, e.g. `D01` (with the next one: `D01A`) |
| 1 | message sequence character: `A` for the first block of a message, `B` for the second, … |
| 6 | flight ID, e.g. `SU1003` (spaces trimmed) |

A downlink with less than 10 text characters is an error. The message number shown is the four characters together (`D01A`), as dumphfdl shows it.

### Sublabel and MFI (label H1)

Only for label `H1`, at the start of the remaining text:

- downlink: `#` + 2 characters + `B` (4 characters): the 2 characters are the **sublabel** (`#CFB…` → `CF`);
- uplink: `- #` + 2 characters (5 characters): the sublabel;
- then, only if a sublabel was found: `/` + 2 characters + space (4 characters): the **MFI** (message function identifier).

Both are removed from the text that follows. Without a sublabel, neither is looked for.

## 2 The block check

CRC-16 with the reflected polynomial 0x1021, initial value 0, no final XOR (CRC-16/KERMIT), over the octets from the mode through `ETX`/`ETB`, **with** their parity bits. It is sent low octet first, so the CRC over the octets including it is 0.

- A block whose check fails is still parsed, shown and joined (§3) like any other, marked "CRC error", as libacars does.
- HFDL frames have their own FCS; an ACARS CRC error inside a good LPDU is rare and means a sender fault.

## 3 Reassembly of multi-block messages

A message longer than one block is sent as several. They are joined like this (libacars `la_reasm`, with the HFDL timeouts):

- **Key:** registration + label + message number (all as received). Blocks of different keys never mix.
- **Sequence number:** downlink: the message sequence character − `A` (first block 0); uplink: the block ID − `A`. Uplink numbers wrap: block `A` (0) follows block `W` (22) (… `V`, `W`, `A`, `B`, …). `X` (23) may follow `W`, but nothing wraps after `X` (libacars, `parse/acars.json`).
- **Timeout:** from the first block received: **1260 s downlink, 370 s uplink**. A block arriving after the timeout starts a new message (the old fragments are discarded).
- **Rules,** for each received block with text:
  1. No message being joined for the key:
     - a downlink whose sequence number is not 0 (not the first block): status **out of sequence**, not joined;
     - a final block (`ETX`): status **skipped** (a message of one block, or the earlier blocks were lost); its text is complete as it is;
     - otherwise: start joining with it; status **in progress**.
  2. A message is being joined:
     - the same sequence number as the last joined block, or (without wrap-around) a lower one: **duplicate**, ignored;
     - not the next sequence number: the joining is abandoned; status **out of sequence**;
     - otherwise appended. If it is final (`ETX`): status **complete**, and the message's text is the blocks' texts concatenated in order.
- An uplink without text is not joined (status skipped).
- Every block is a message in the list and in the day file, with its own text and its reassembly status. The block that completes a message also carries the whole text, and the applications (§4) decode the whole text, once (F-H10).
- Applications decode the text of a block whose status is skipped or complete only. A block in progress shows its own text; its applications are not decoded.

## 4 Which application decodes the text

After reassembly, the text (after the sublabel and MFI) is offered to the applications by label, first match wins (libacars `la_acars_apps_parse_and_reassemble`):

| Label | Tried in order |
|---|---|
| `A6`, `AA`, `B6`, `BA` | ARINC 622 (ADS-C, CPDLC) |
| `H1` | ARINC 622, then MIAM, then OHMA |
| `MA` | MIAM |
| `SA` | media advisory |
| any other | none: the text is shown as it is |

The applications are `applications.md`. One that does not recognise the text leaves it to the next one; if none does, the text is shown as it is. A recognised but damaged application message is shown as "unparseable …" with its reason, and the text is shown as well.

## 5 Labels (informative)

The label says what kind of message it is; most are defined by airlines. Common ones in HFDL:

| Label | Meaning |
|---|---|
| `_d` (`_` + DEL) | general response, no information to send (often an acknowledgement) |
| `Q0` | link test |
| `SA` | media advisory: a data link was established or lost |
| `H1` | message to or from an onboard system (often with a sublabel, `#CFB` = central fault display) |
| `A6`, `AA`, `B6`, `BA` | ARINC 622 ATS applications (ADS-C, CPDLC) |
| `MA` | MIAM |
| `5Z`, `80`…`8~`, others | airline defined |

A front end may show a short name for known labels; it MUST show the label itself as well (it is the search term, `spec/07-ui/search-terms.md`).
