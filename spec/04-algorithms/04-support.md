# 4 Support algorithms

**Normative.** The small algorithms around the decoder. §4.1 to §4.5 and §4.8 are the DSC seed's (`../DSC-Decoder-Seed/spec/04-algorithms/04-support.md`) word for word in their rules, so a program implementing both seeds has one copy of them (F-H14); the HFDL additions are marked.

## 4.1 Recording start time and center frequency from a file name

Test: `time/file_name.json`. **Start time:** first the WAV's metadata: ShellSDR's RIFF `LIST/INFO/ICMT` comment lines `start_time=` (ISO 8601, `Z` or an offset) and `timezone=`; ShellSDR names its files in the time zone that `timezone=` gives (UTC by default, F-H18). Without metadata, exactly as the DSC seed §4.1 (`base_time(name)` scanning for `YYYY MM DD [≤ 3 non-digits] hh mm ss`, local to UTC with the explicit DST rule; failing that, the file's modification time, then the current time).

**Center frequency (HFDL addition).** For an I/Q recording, the first match in the file name, case-insensitive, of a number directly followed by a unit: `digits[.digits]` + `Hz`, `kHz` or `MHz` (`_8902500Hz`, `8902.5kHz`, `8.9025MHz`). A WAV's metadata wins when present: the SDR++ / ShellSDR RIFF comment or `auxi` chunk center frequency. Neither: the user must give it; decoding the file is refused until then.

## 4.2 ISO 8601 text

Test: `time/iso8601.json`. As the DSC seed §4.2: UTC `YYYY-MM-DDTHH:MM:SSZ`; local the date and time of `utc + offset` and `±HH:MM`.

## 4.3 Which day file a message goes to

Test: `ndjson/day_file.json`. As the DSC seed §4.3: the **local** date at reception, `YYYY-MM-DD.ndjson`, in the HFDL message directory (`spec/05-data/`).

## 4.4 Distance

Test: `geo/distance.json`. As the DSC seed §4.4: haversine on R = 6371.0088 km; NM = km / 1.852.

## 4.5 The user's location

Test: `geo/parse_location.json`. As the DSC seed §4.5: two signed decimal numbers, latitude then longitude, separated by white space or a comma; anything else invalid.

## 4.6 Search and filters

Test: `presentation/search.json`. **Search** as the DSC seed §4.6: whitespace-separated words, each a case-insensitive (ASCII) substring of one of the message's search terms (`spec/07-ui/search-terms.md`), all words must match.

**Filters (HFDL),** combined with the search and with each other by AND:

| Filter | Keeps | Default |
|---|---|---|
| hide link traffic | messages whose severity is not `link` | **on** |
| alerts only | severity `emergency` or `caution`, and messages of a watched aircraft (§4.9) | off |
| hide joined blocks | not the blocks with status `in_progress` of a message that was later completed (the completing block shows the whole) | on |

## 4.7 Alerts

Test: `alerts/alerts.json` (only the `alert` flag is normative).

```
alert(message, settings, recent):
    if message.severity == emergency: kind = emergency
    elif message.severity == caution and settings.alert_on_caution: kind = caution
    elif settings.watch_alerts and watched(message): kind = watch            # §4.9
    else: return none
    key = acars_message_key(message) or (message.icao or registration, kind)
    if key alerted within the last 30 minutes (recent): return none         # once per message or aircraft
    remember key with the message time
    return kind
```

- `acars_message_key` is the reassembly key (registration, label, message number) when the message has an ACARS block: the blocks and the joined whole of one message alert once.
- `alert_on_caution` defaults to **on**; watch alerts to on.
- Uplinks and downlinks are treated alike: a ground station's text with a keyword alerts too.
- Alerts come only from decoding and followed lines, never from opening files (`ALR-05`). The alert text is informative.

## 4.8 Merging settings

Test: `config/merge.json`. As the DSC seed §4.8 (three-way merge; units compare and copy whole). HFDL units: the location (one unit); the channel list (one unit); each keyword list (one unit each); the watch list (one unit); each enrichment file path and lookup setting (one setting each).

## 4.9 Aircraft (HFDL)

The aircraft view lists every aircraft heard. Messages are joined to an aircraft by:

1. its ICAO address when the message has one (`icao`);
2. else its registration (ACARS, trimmed of dots);
3. else nothing (squitters, uplinks to an unknown AC ID): not in the view.

When a message carries both an ICAO address and a registration, the aircraft known by either becomes one (the ICAO address wins as the key). The same for an ADS-C airframe ID. A flight ID (HFNPDU, ACARS, ADS-C) is recorded as the aircraft's current flight.

Per aircraft: ICAO address, registration, flight, enrichment (§4.10), first and last heard (time, frequency, ground station), messages count, the **last valid reported position** with its time and source, and its distance from the user's location. A position older than 2 hours is shown as such ("2 h 15 min ago"), never as current.

**Watched:** a message is watched if its ICAO address, registration or flight ID equals (case-insensitive, after trimming) an entry of the watch list. Entries are typed by the user; a 6-hex-digit entry is an ICAO address.

## 4.10 Enrichment (HFDL, group `enrich`)

At reception, a message is enriched with what is known then (stored with it, `ENR-…`):

| What | From | Key |
|---|---|---|
| aircraft: registration, ICAO type code, type, operator | the aircraft file (`spec/05-data/`), else the online lookup cache | ICAO address; else registration |
| airline name | the airlines file | the flight ID's first 3 letters (ICAO airline code), else its first 2 characters (IATA) |
| ground station: name, position, distance | the ground-station table | GS ID |
| aircraft position: distance | the message's reported position | user's location |
| route: origin and destination airports with position and distance | the online route lookup (§4.11), else CPDLC departure/destination airports with the airports file | flight ID |

Distances need the user's location; without it, none is shown or stored.

## 4.11 Online lookups (HFDL, group `lookup`)

Off by default; each service is switched on separately. No key is needed by either.

| Service | Aircraft | Route |
|---|---|---|
| hexdb.io (default) | `GET https://hexdb.io/api/v2/aircraft/{icao}`: `registration`, `icao_type_code`, `type`, `manufacturer`, `registered_owner`, `operator_flag_code` | `GET https://hexdb.io/api/v2/routes/{callsign}`: `origin`, `destination` each `icao`, `iata`, `name`, `latitude`, `longitude` |
| adsbdb.com | `GET https://api.adsbdb.com/v0/aircraft/{icao}`: `response.aircraft`: `registration`, `icao_type`, `type`, `manufacturer`, `registered_owner`, `registered_owner_operator_flag_code` | `GET https://api.adsbdb.com/v0/callsign/{callsign}`: `response.flightroute.origin` / `.destination`: `icao_code`, `iata_code`, `name`, `latitude`, `longitude` |

- The endpoints are settings with `{icao}` and `{callsign}` placeholders (an API's version may change).
- **When:** a downlink message with an ICAO address or a flight ID that has no cache entry younger than 24 hours (aircraft) or 6 hours (route). At most one request per key at a time; at most 1 request per second per service.
- **Not found** (HTTP 404) is cached too (as "unknown", 24 h), so it is not asked again.
- **Order:** the first switched-on service that answers wins; with both on, hexdb first.
- **Caching:** results are kept in a cache file (`spec/05-data/`) for display only. They are never exported, shared or bulk-downloaded: adsbdb's route data may not be copied into other databases (F-H15).
- As the DSC seed's lookups: off the decoding and UI paths; the message is shown at once and written after the lookup ends with its result; a failure is told once per message; quitting writes pending records without results (`LKP-…`).
