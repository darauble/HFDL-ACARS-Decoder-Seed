# Architecture

How the software is divided, and which part may call which. **Normative in its boundaries**: what each component owns, what it must not do, the threading rules. **Names and languages are free.** It is the DSC seed's architecture with HFDL's parts, so that one program can host both (§5).

## 1 Components

```
                    ┌──────────────────────── front end (TUI, GUI, …) ─────────────────────────┐
                    │ draws views, reads input, plays the alert sound; calls the session        │
                    └──────────────▲──────────────────────────────────────────┬──────────────┘
                        events / polling                                  commands
┌──────────────────────────────────┴──────────────────────────────────────────▼─────────────────────────┐
│ SESSION: mode (viewing / live), sources and channels, settings, alert state, the views, enrichment,   │
│ lookups                                                                                                 │
└──┬──────────┬───────────────┬───────────────┬───────────────┬───────────────┬──────────────┬──────────┘
┌──▼──────┐ ┌─▼─────────────┐ ┌▼────────────┐ ┌▼─────────────┐ ┌▼────────────┐ ┌▼────────────┐ ┌▼────────┐
│ CAPTURE │ │ RECEIVER      │ │ PARSER      │ │ STORE        │ │ REFERENCE   │ │ LOOKUP      │ │SETTINGS │
│ I/Q,    │ │ + FRAME DEC.  │ │ one per     │ │ messages in  │ │ ground      │ │ hexdb,      │ │ load,   │
│ audio,  │ │ one per       │ │ session:    │ │ view, day    │ │ stations,   │ │ adsbdb      │ │ merge,  │
│ files,  │ │ channel       │ │ tables,     │ │ files,       │ │ aircraft,   │ │ (HTTP),     │ │ save    │
│ devices │ │               │ │ reassembly  │ │ aircraft     │ │ airlines,   │ │ cache       │ │         │
│         │ │               │ │             │ │ view         │ │ airports    │ │             │ │         │
└─────────┘ └───────────────┘ └─────────────┘ └──────────────┘ └─────────────┘ └─────────────┘ └─────────┘
      PRESENTATION helpers (pure functions): list-row texts, detail fields, search terms and matching, alert text
```

| Component | Owns | Must not |
|---|---|---|
| **Capture** | Reading recordings (WAV, raw I/Q); capturing live I/Q and audio; listing devices. Delivers sample blocks with rate, center frequency and sample position. | Know about HFDL. |
| **Receiver + frame decoder** | One instance per channel (`04-algorithms/01-receiver.md`, `02-frame.md`): samples → frames (mode, time, symbols → octets, signal figures). | Share state with another channel. Parse PDUs. Do I/O. |
| **Parser** | One per session (`03-parser.md`): frames → messages; the AC ID table, the system table in use, the reassembly tables. | Touch the store or the screen. Use the computer clock. |
| **Store** | Messages in view, time-ordered, with a revision; the aircraft and ground-station views derived from them; day-file writing and reading. | Decide what to show. |
| **Reference** | The ground-station table (built-in, persisted updates); the aircraft, airline and airport files; the lookup cache. Thread-safe. | Make network calls. |
| **Lookup** | HTTP GETs to the configured services, by the rules of `04-support.md` §4.11. | Run on a decoding or UI thread. |
| **Settings** | The settings record; load with defaults; save by three-way merge, atomically. | Hold runtime state. |
| **Session** | Mode rules, staging and run control, enrichment at reception, alert decisions, lookups, deferred writes, events. The only component the front end talks to (plus the presentation helpers). | Draw anything. |
| **Presentation helpers** | Pure functions from a message (and context) to texts: list row, detail, search terms, matching, alert text. | Keep state. |
| **Front end** | Layout, input, dialogs, the alert sound, the clipboard. | Parse octets, write files, decide alerts. |

## 2 Data flow of one frame

1. **Capture** delivers sample blocks to each channel's receiver (on the source's thread, or one thread per channel).
2. The **receiver** finds a frame; the **frame decoder** gives its octets, with channel, mode, time and signal figures.
3. The frame goes to the **parser**'s queue. The parser takes frames in the order of `03-parser.md` §3.1 (a short reorder buffer of 1 s across channels is enough) and emits zero or more messages.
4. **Session**, per message: gives it a sequence number; enriches it (`04-support.md` §4.10); adds it to the store (`MessageAdded`), which updates the aircraft and ground-station views; decides the alert; starts lookups or writes the record now.
5. When a lookup finishes: re-enrich, update (`MessageUpdated`), write.

## 3 Commands and events

As the DSC seed's (files, sources/channels, run, settings, messages, queries; events `MessageAdded`, `MessageUpdated`, `ViewReloaded`, `ChannelsChanged`, `ModeChanged`, `Alert`, `Notice`, `ConfigChanged`), with these HFDL additions:

| Area | Commands / events |
|---|---|
| Sources | stage an I/Q source (device or file, center, rate, channels); stage an audio source (device or file, channel frequency); list the channels a band covers |
| Views | aircraft list (snapshot + revision); one aircraft's messages; ground-station list |
| Settings | keyword lists; watch list; alert on caution; watch alerts; aircraft/airline/airport file paths; lookup services on/off, endpoints |
| Events | `GroundStationsChanged` (a newer system table, a squitter heard), `AircraftChanged` (revision) |

## 4 Threading rules (normative)

1. Each channel's receiver runs on a thread no other channel's receiver uses at the same time. A receiver instance is used by one thread only.
2. The parser runs on its own thread (or under one lock); it is the only writer of its tables.
3. Lookups run on worker threads.
4. The store, the reference data and the session state each have their own lock; a read takes a consistent snapshot.
5. Events are delivered never while the session's lock is held.
6. Stopping joins the receivers, then drains the parser (frames already decoded become messages, `NFR-03`).
7. A lookup finishing after the session is gone must not touch it.
8. Settings change only through the session's setters.

## 5 One program, several decoders

A program may implement this seed together with others of the same form (the DSC seed; later NAVTEX, RTTY). Then (`NFR-08`):

- **One session per decoder kind**, each with its own components above, its own message directory (`<data>/<project_name>/hfdl`, `…/dsc`) and its own views. A source (channel) belongs to one kind.
- **Shared:** the front end and its alert banner (an alert says which kind), the settings file (each kind's settings under its own key; shared settings at the top), and the **user's location**, which is one shared setting.
- Each kind still passes its own seed's conformance suite unchanged; nothing in one seed's vectors depends on another seed.

## 6 Files on disk

| File | Location | Format |
|---|---|---|
| Day files | message directory (default `<data>/<project_name>/hfdl`) | `YYYY-MM-DD.ndjson`, `spec/05-data/record.schema.json` |
| Ground-station table | `<data>/<project_name>/hfdl/systable.json` | `spec/05-data/README.md` |
| Aircraft, airlines, airports | paths chosen by the user | CSV, `spec/05-data/README.md` |
| Lookup cache | `<data>/<project_name>/hfdl/lookup-cache.ndjson` | `spec/05-data/README.md` |
| Settings | `<config>/<project_name>/config.json` | `spec/05-data/config.schema.json` |
| Saved message | chosen by the user | plain text, the detail view's lines |
