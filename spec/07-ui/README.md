# User interface behaviour

What every front end must offer: a terminal UI, a desktop GUI, a view inside another program (ShellSDR's Work Area). Layout, colours, keys and wording are **free** unless a line says otherwise. Normative: the views and what they contain, the commands, the rules of `spec/06-behaviour.md`, and the search terms (`search-terms.md`). The mockups (`mockups/README.md`: a desktop GUI and ShellSDR's Work Area) are informative.

## Views

### Status (always visible)

- the mode, VIEWING or LIVE, unmistakable;
- the alert banner while an alert is ACTIVE (`ALR-02`): kind, aircraft, subject;
- the latest notice.

### Sources

One row per staged source (label, device or file, center and rate or channel frequency, state, level), and under an I/Q source one row per channel: frequency, ground station(s) using it (`ground-stations.csv`), state (`06-behaviour.md` §2), frames decoded / with errors, last frame time. DECODING and "lookup pending" stand out.

### Message list

One row per message after search and filters, time-ordered. Columns (`VIEW-03`):

| Column | Content | Example |
|---|---|---|
| Time | local time; the date visible in the row or the day file name | `19:28:26` |
| Freq | channel, kHz | `8942` |
| Dir | `▲` downlink (from aircraft) / `▼` uplink, or `D`/`U` | `▲` |
| GS | ground station ID and short name | `7 Shannon` |
| Aircraft | registration, else flight, else ICAO address, else AC ID | `RA73824` |
| Flight | flight ID | `U62905` |
| Type | the class; for ACARS the label (and sublabel) | `ACARS H1/CF` |
| Subject | §Subject | `ENG 1 FIRE LOOP B FAULT` |
| Dist | distance to the reported position, km | `2 731` |
| Sev | severity: `E` emergency, `C` caution, ` ` routine, `·` link; and colour | `C` |

- Severity is shown in two independent ways (letter and colour, `VIEW-04`). A watched aircraft is marked too (e.g. `★`).
- An absent value shows as a placeholder (`--` or empty).
- Position "message x of n" and the day file(s) in view (`VIEW-09`).

**Subject**, the first that applies:

1. emergency or caution: the matched keywords' context, e.g. the line of text containing the first match;
2. CPDLC: the first element's text with its values filled in (`CLIMB TO AND MAINTAIN FL350`);
3. ADS-C: the tags' names (`Basic report, Flight ID, Earth reference`); an emergency report first;
4. media advisory: `HF link established 12:34:56`;
5. ACARS with text: the first line of the text, trimmed;
6. performance data / frequency data: `Position 55.12 N 37.77 E`;
7. logon types: the type and ICAO address (`Logon request 151DAD`); squitter: `Squitter: GS 7, 3, 11; systable 51`;
8. otherwise: the class.

### Detail

On demand, for the selected message, following it in FOLLOW mode. Sections, each only when present (`VIEW-05`):

1. **Summary**: severity and its reason (keywords, CPDLC MAYDAY, ADS-C emergency), class, subject.
2. **Aircraft**: ICAO address (and where it came from), registration, flight, type, operator, airline, watched; the reported position with its source and time, and its distance.
3. **Route** (if known): origin and destination airports, with distances.
4. **Ground station**: ID, name, position, distance, frequency (and its index).
5. **HFDL**: direction, MPDU source/destination, LPDU type and fields, HFNPDU type and fields (performance data in full; frequency data per station with frequencies resolved to kHz; system table).
6. **ACARS**: mode, registration, ack, label (and short name), block ID, more, message number, flight, sublabel, MFI, CRC state, reassembly status; the text (joined, when complete) in full, wrapped.
7. **Application**: ARINC 622 (IMI, ground address, CRC); ADS-C tags with every field and unit; CPDLC header and elements with values; MIAM frame and core PDU; media advisory; OHMA.
8. **Reception**: time UTC and local, ISO 8601 with its source; frequency, bit rate (from M1) and slots; level, noise, SNR, frequency error; source and file; the user's location at reception.
9. **Raw**: the PDU octets in hex, 16 per line.

The detail's text is what save and copy produce (`EXP-01`).

### Aircraft

One row per aircraft (`AC-01`), sortable by last heard (default), distance, registration: ICAO, registration, flight, type, operator, last position (lat, lon) and its age, distance, last frequency and ground station, last heard, messages. Selecting one and choosing "messages" filters the message list to it (`AC-02`). Watched aircraft first, marked.

### Ground stations

One row per station of the table in use (`AC-03`): ID, name, position, distance, frequencies (those heard in squitters marked, those "in use" per the last squitter marked), last heard. The system table version in use and the newest seen on the air.

### Dialogs

- Pick files (day files; recordings).
- Stage a source: I/Q (device or file, center: typed or from a list of bands and centers, `ground-stations.md` §2; rate; channels, all by default) or audio (device or file; channel frequency, picked from the channel list or typed).
- Enter a value: location, keyword lists, watch list entries, file paths, lookup endpoints. Invalid input is refused with a message, the dialog stays open.

## Commands

All of `spec/02-architecture.md` §3 for the built groups, plus: move selection; search; the three filters (`VIEW-07`); follow/hold; open/close detail; switch views (messages, aircraft, ground stations); watch / unwatch the selected aircraft; refresh followed files; acknowledge alert; alert sound on/off; save / copy detail; help; about (name, version, licence, credits: dumphfdl and libacars by Tomasz Lemiech); quit. Every command is reachable without a mouse.

## Responsiveness

New messages, channel states and aircraft appear within about a quarter of a second (`NFR-01`). The layout follows the window size; a screen too small says so.
