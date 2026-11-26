# Data formats

Every file the software reads or writes. **Normative**: files outlive program versions, and users move them between machines and implementations.

| File | Format | Spec |
|---|---|---|
| Day file `YYYY-MM-DD.ndjson` | NDJSON, one record per line | `record.schema.json`, below |
| Settings `config.json` | JSON object | `config.schema.json` |
| Ground-station table `systable.json` | JSON | below |
| Aircraft, airlines, airports | CSV with a header | below |
| Lookup cache `lookup-cache.ndjson` | NDJSON, append-only | below |
| Saved message `.txt` | UTF-8 text | the detail view's lines |

## Day files

As the DSC seed's day files: one per **local** date; UTF-8, one JSON object per line ending in `\n`; append only, one append per record (`STO-03`); the file that has the name at write time, reopened per record (`STO-08`); read line by line, invalid lines skipped (`STO-04`). A line is invalid if it is not a JSON object, has no `kind`, `pdu` or `freq`, or `pdu` is not even-length lowercase hex.

On reading, a record's fields are derived from `pdu` and the `x-stored` context keys exactly as when it was decoded (`STO-05`): the parser is run on `pdu` with `icao`, `reasm`, `joined`, `joined_app`, `systable` taken from the line instead of from the session's tables. Nothing a reader does changes the session's tables.

**Example** (one line, wrapped here):

```
{"v":1,"kind":"lpdu","utc":"2022-10-12T16:28:26Z","off":"+03:00","tsrc":"filename","freq":8942,"m1":1,
 "lvl":-81.8,"noise":-84.5,"ferr":-1.7,"dir":"down","gs":7,"ac":23,"icao":"152060","icao_src":"table",
 "reasm":"in_progress","class":"acars","sev":"caution","kw":["FIRE"],"reg":"RA73824","flight":"U62905",
 "label":"H1","text":"MPF/DBN …","gs_st":{"name":"Shannon, Ireland","lat":52.744089,"lon":-8.926752,"km":2144.1},
 "rx":{"lat":54.84104,"lon":23.83097},"pdu":"1dffff0132…"}
```

## Ground-station table `systable.json`

The table in use when it came from the air (`ground-stations.md` §3); absent: the built-in one.

```
{"version": 53, "received": "2026-11-25T10:00:00Z",
 "stations": [{"gs_id": 7, "name": "Shannon, Ireland", "lat": 52.744, "lon": -8.927, "utc_sync": true,
               "frequencies_khz": [11384, 10081, 8942, 8843, 6532, 5547, 3455, 2998]}, …]}
```

A file that is not valid, or older than the built-in table, is ignored.

## Aircraft, airline and airport files (group `enrich`)

The user downloads them and names them in the settings; the program does not fetch them (no network, `NFR-04`). Each is CSV, comma-separated, with a header line, UTF-8, quoted fields as RFC 4180. Columns are found by **header name** (case-insensitive); other columns are ignored. A row without its key is skipped.

| File | Key column | Columns used | Known sources (their own formats map to these names) |
|---|---|---|---|
| aircraft | `icao24` (6 hex digits) | `registration`, `typecode`, `model`, `manufacturername`, `operator`, `owner` | OpenSky Network aircraft database (`aircraftDatabase.csv` uses these names) |
| airlines | `icao` (3 letters) | `iata`, `name`, `callsign`, `country` | OpenFlights `airlines.dat` with a header added |
| airports | `ident` or `gps_code` (ICAO) | `iata_code`, `name`, `municipality`, `iso_country`, `latitude_deg`, `longitude_deg` | OurAirports `airports.csv` (public domain) uses these names |

Their licences are the user's to check; the program only reads them.

## Lookup cache `lookup-cache.ndjson`

One line per answer: `{"svc":"hexdb","what":"aircraft","key":"4010EE","t":"2026-11-25T10:00:00Z","found":true,"data":{…}}`. `data` holds the fields of `04-support.md` §4.11 under the names of `record.schema.json`'s `acft` and `route`. The last line for (`svc`, `what`, `key`) wins. The file may be deleted at any time; it is never exported (`LKP-05`).
