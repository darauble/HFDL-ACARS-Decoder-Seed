# Behaviour: state machines

**Normative.** The DSC seed's state machines (`../DSC-Decoder-Seed/spec/06-behaviour.md`) apply as they are, with "channel" read as **source** (an I/Q device or recording with its channels, or an audio device or recording with its one channel). This file gives only what differs or is added.

## 1 Session mode

As the DSC seed §1 (VIEWING, LIVE; open files and set the message directory only while VIEWING; start needs at least one started source; quitting stops, drains the parser and writes pending lookup records). At program start: load the settings, the ground-station table (persisted, else built-in), the aircraft/airline/airport files and the lookup cache; view today's day file; restore the staged live sources. Decoding never starts by itself.

## 2 Source and channel

A source has the DSC seed's channel states (INACTIVE, IDLE, SILENT, ACTIVITY, DECODING). An I/Q source shows them per **channel** as well:

| Channel state | Meaning |
|---|---|
| SILENT | no frame search progress: the A correlation stays below half the threshold |
| ACTIVITY | an A sequence was found within the last 32 s (a frame started), none decoded in that time |
| DECODING | a frame is being read (between A2 and the last training segment), or one was decoded within the last 3 s |

**Staging rules** (refused otherwise, with a reason):

- An I/Q source needs a center frequency and a rate; its channels are those of `ground-stations.md` §2 that fit, all by default; the user may deselect some. A source whose band covers no channel is refused.
- An audio source needs one channel frequency (kHz).
- Two sources on the same device: refused.
- A recording source needs a readable file of a supported format, and for I/Q a center frequency (`DEC-07`).
- Recordings run until their end, then flush (every frame already found completes or is dropped); they are not saved in the settings.

## 3 A decoded message

As the DSC seed §3: decoded → enriched → IN VIEW (`MessageAdded`) → WRITTEN, with LOOKUP PENDING between when a lookup is needed. The alert decision is made when it enters the view, from the parsed fields and the alert memory (`04-support.md` §4.7).

A message that completes an ACARS (or MIAM, OHMA) reassembly also marks the earlier blocks of that message as joined in the view (so the "hide joined blocks" filter hides them); their records in the day file are not changed.

## 4 Alert

As the DSC seed §4 (NONE ↔ ACTIVE; a newer alert replaces it; the sound and notification when entering ACTIVE). The banner says the kind (emergency, caution, watch), the aircraft and the subject.

## 5 Online lookup

```
 lookups off, or message older than 1 h, or uplink ─────────────────────────► (none)
 no ICAO address and no flight ID needing a lookup (04-support.md §4.11) ───► (none)
 otherwise ─► PENDING (the source shows "lookup pending")
               │  per key, one request at a time, at most 1 per second per service
               ├─ found or not found: cache it, re-enrich, update, write
               └─ failed (network, HTTP error other than 404, bad JSON): write without it; notice once per message
```

## 6 Follow and hold; following day files

As the DSC seed §6 and §7, unchanged. Followed lines are parsed with their stored context (`spec/05-data/`), never touching the session's tables; they enter the aircraft and ground-station views like decoded messages.

## 7 Ground-station table

```
 built-in (v52) ──► persisted table (if valid and newer) ──► in use
 squitter says version V > in use ──► notice once: "system table V on the air, W in use"
 complete system table received, newer ──► in use, persisted, GroundStationsChanged
```

A ground station is **heard** when a squitter from it was decoded; the view keeps the last time and frequency per station.
