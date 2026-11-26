# Ground stations and frequencies

**Normative**: the table's meaning, how frequency indices resolve, how the table is updated, and the band grouping. The table's content is the built-in default, replaced in use by newer tables received on the air.

## 1 The table

`ground-stations.csv` is system table **version 52**, as published with dumphfdl 1.7.0 (`etc/systable.conf`, GPL-3.0-or-later; F-H07):

| Column | Meaning |
|---|---|
| `gs_id` | GS ID, 1..127 |
| `name` | place and country, as the user reads it |
| `lat`, `lon` | the station's position, signed decimal degrees |
| `frequencies_khz` | the station's frequencies, space-separated, **in index order**: the first is index 0 |

- A **frequency index** (in a squitter's "frequencies in use", in frequency data's masks, in performance data's frequency) is a position in that station's list. Bit i of a 20-bit mask is index i.
- An index beyond the station's list, or a station not in the table, shows as the number, e.g. `freq #12`.
- The table also names the station in every message (`7 Shannon, Ireland`) and gives its position for distances (`ENR-02`).

## 2 Channels from the table

The set of all frequencies of all stations is the set of HFDL channels a receiver may decode. They group into bands (gap > 300 kHz between neighbours starts a new band):

| Band | Channels (kHz) | Span (kHz) | A center that covers them (kHz) |
|---|---|---|---|
| 2.9 MHz | 2941 … 3016 | 2941 to 3019 | 2980.0 |
| 3.5 MHz | 3455, 3497 | 3455 to 3500 | 3477.5 |
| 3.9 MHz | 3900 | 3900 to 3903 | 3904.5 |
| 4.7 MHz | 4654 … 4687 | 4654 to 4690 | 4672.0 |
| 5.6 MHz | 5451 … 5720 | 5451 to 5723 | 5587.5 |
| 6.6 MHz | 6529 … 6712 | 6529 to 6715 | 6623.5 |
| 8.9 MHz | 8825 … 8977 | 8825 to 8980 | 8902.5 |
| 10 MHz | 10027 … 10093 | 10027 to 10096 | 10058.5 |
| 11.3 MHz | 11184 … 11387 | 11184 to 11390 | 11287.0 |
| 13.3 MHz | 13264 … 13351 | 13264 to 13354 | 13309.0 |
| 15 MHz | 15025 | 15025 to 15028 | 15029.5 |
| 17.9 MHz | 17901 … 17985 | 17901 to 17988 | 17944.5 |
| 22 MHz | 21928 … 21997 | 21928 to 22000 | 21964.0 |

- The span's upper end is the highest channel + 3 kHz (its signal reaches about 2.64 kHz above it).
- The suggested center is the span's middle, moved by up to a few hundred Hz so that no channel's signal (assigned − 1 kHz to assigned + 4 kHz) contains it: an SDR's DC spike then falls between channels. It is informative (bookmarks, recordings).
- A receiver given a center frequency and a sample rate decodes the channels whose whole signal (assigned + 0 to + 3 kHz) lies inside 90 % of the band the rate covers (`CH-…` in `spec/01-requirements.md`).

## 3 Updating the table

- On start, use the table the user last received (persisted, `spec/05-data/`), else the built-in one.
- A complete system table received on the air (`pdu-layers.md` §7.4), without error and **newer** than the one in use, replaces it at once and is persisted. Station names are kept from the old table (the air table carries none); a new station gets no name until the user adds one.
- **Newer** compares 12-bit versions with wrap-around: `new` is newer than `old` if `(new − old) mod 4096` is between 1 and 2047.
- Every squitter says the system table version in use on the air. When it is newer than the table in use, the program says so once ("system table 53 on the air, 52 in use"), until a complete table arrives.
