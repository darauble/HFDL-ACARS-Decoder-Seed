# Findings

Questions that came up while writing the seed, and what was decided. The decisions are part of the specification. Each has an ID, cited where it applies.

## F-H01: the source of the physical and PDU layers, and how it was checked

ARINC 635-4 defines HFDL, and it is not public. The only complete open description is the source of **dumphfdl** (Tomasz Lemiech, GPL-3.0-or-later). The seed takes version **1.7.0** (2023, upstream `bb7234b`), not the 1.3.0 of 2022 used for the logs in hand, because 1.7.0 fixes two things that change results: the scrambler under liquid-dsp ≥ 1.6 (F-H02), and uplink MPDUs with several LPDUs for one aircraft (the header pointer advanced by 1 instead of by the LPDU count).

**Decision.** `spec/03-domain/physical-layer.md` and `pdu-layers.md` are written in the seed's own words, as data and rules, not as code. To check that the words are enough, `tools/hfdl_tx.py` and `tools/hfdl_pdu.py` were written from them alone (a transmitter: PDU octets → code → interleaver → PSK → scrambler → frame → I/Q), and dumphfdl 1.7.0 (built with libacars 2.2.3 and liquid-dsp 1.6.0) decoded the result. On 2026-11-25 it decoded all 10 synthetic frames, covering the eight M1 modes (300 to 1800 bit/s, single and double slot), to exactly the octets sent: a squitter, a logon request with frequency data, a logon confirm, performance data, an ACARS H1 downlink and an ACARS uplink acknowledgement.

## F-H02: the scrambler sequence

dumphfdl builds the scrambler with liquid-dsp's `msequence`. liquid-dsp 1.6.0 changed what `msequence_create`'s arguments mean (generator and state bit order), so dumphfdl 1.7.0 passes different numbers per liquid version (genpoly 0x8002 / state 0x6959 before 1.6, 0x4001 / 0x4D4B from 1.6 on), and dumphfdl 1.3.0 passed 0x8003 / 0x6959.

**Decision.** All three were computed with the liquid-dsp code of their versions, and give the same 120 bits. The seed gives the 120 bits as data (`physical.json`, `scrambler`), which is normative, and the LFSR in liquid-dsp ≥ 1.6 terms as how they were made. An implementation needs no m-sequence library.

## F-H03: the prekey's content

dumphfdl does not use the 448 prekey symbols: it searches for the first A sequence. Their content is not in any open source.

**Decision.** A receiver MUST NOT depend on the prekey's content. The synthetic frames send BPSK of a 15-bit m-sequence there. When real recordings are in the suite, their prekeys will be compared; if they show a fixed pattern, it will be recorded here, informatively.

## F-H04: a truncated LPDU

An MPDU's header gives each LPDU's length. If an LPDU would run past the frame's end, dumphfdl drops the whole MPDU's remaining LPDUs and reports the MPDU as an error, but keeps the LPDUs already parsed.

**Decision.** The same: LPDUs before the truncated one are kept, the truncated one and those after it are dropped, and the frame is counted with the error "truncated LPDU".

## F-H05: position 180°

Aircraft send latitude or longitude 180.0 (the 20-bit value 0x7FFFF) when they have no position. The 2022 logs in hand contain such reports; the user's earlier position script dropped them. dumphfdl's position feed requires |lat| ≤ 90 and |lon| ≤ 180, so a latitude of 180 is dropped there too.

**Decision.** A position is valid only if |lat| ≤ 90 and |lon| ≤ 180 (`pdu-layers.md` §7.1). An invalid position is ABSENT: shown as "unknown" in the detail, not used for distances and not cached.

## F-H06: the AC ID table

Most LPDUs name the aircraft only by its AC ID, which the ground station assigns at logon and which is valid on that frequency only. dumphfdl keeps a table (frequency, AC ID) → ICAO address, filled from logon confirms and logon resume confirms, emptied by logoff requests and logon denials, with entries expiring after 1 h.

**Decision.** The same table, the same rules (`pdu-layers.md` §8). It is runtime state of the decoding session, not persisted: after a restart, an aircraft is known again at its next logon. A message decoded with the table records the ICAO address it resolved to, so reading the day file back needs no table. Channels are distinct by frequency, and the table is shared by all channels of one session.

## F-H07: the ground-station table

dumphfdl ships `etc/systable.conf`, system table version 52 (version 51 in 2022; 52 moved Al Muharraq, Bahrain, and changed its frequencies). Ground stations broadcast newer tables on the air, which dumphfdl saves.

**Decision.** `spec/03-domain/ground-stations.csv` is version 52, converted from that file (station names as dumphfdl gives them). A program starts from the last table it received, else the built-in one, and updates it from the air (`ground-stations.md` §3). The station names are not on the air; they come from this table.

## F-H08: times in dumphfdl's output

dumphfdl time-stamps every frame with the computer's clock when it decoded it, also when reading a file. Its output for a recording therefore has no usable times.

**Decision.** The seed times a frame from its sample position (`physical-layer.md` §9, `DEC-06`), as the DSC seed does. When dumphfdl's output becomes reference output for a recording (`conformance/`), its times are replaced by times computed from the sample position, and the comparison of times uses a tolerance.

## F-H09: the source of the ACARS layer and its applications

ARINC 618, 620, 622 and 745 and RTCA DO-258A define ACARS and its applications, and are not public. libacars (Tomasz Lemiech, MIT) decodes all of them, and is what dumphfdl uses. The seed takes **libacars 2.2.3** (upstream `8840284`), configured as dumphfdl 1.7.0 configures it: the HFDL bearer (reassembly timeouts 1260 s downlink, 370 s uplink) and `decode_fragments` off (a block whose message is still being joined does not have its applications decoded).

**Decision.** `spec/03-domain/acars.md` and `applications.md` describe what libacars does, in the seed's words. Where libacars does something questionable, the seed does the same and says so here, so that the reference output stays comparable (F-H12).

## F-H10: blocks and messages

libacars returns one result per received ACARS block. The block that completes a multi-block message carries the joined text and its decoded applications; the earlier blocks carry their own text and the status "in progress".

**Decision.** The same. Every received block is one message in the list and one line in the day file (nothing is dropped, `STO-01`), with its reassembly status. The completing block is the one that shows the whole message and raises alerts for it. The list can hide the "in progress" blocks of a message that was completed (`spec/07-ui/`).

## F-H11: the time of an ADS-C report

An ADS-C report gives its time as seconds past the hour only.

**Decision.** For the report's position age (`ENR-…`), the report is placed in the hour of the message's reception; if that puts it more than 30 minutes after the reception, in the hour before. The seconds past the hour are shown as received.

## F-H12: the ADS-C reporting interval's scale 0

ADS-C's reporting interval has a 2-bit scaling factor. libacars maps 2 to 8 and 3 to 64 and leaves 0 and 1 as they are, so scale 0 gives an interval of 0 seconds.

**Decision.** The same (0 → 0, 1 → 1, 2 → 8, 3 → 64), so that the output matches the reference. Should the standard be found to say otherwise, this finding will change, with the vectors.

## F-H13: the FANS-1/A ASN.1 module

libacars ships C code generated by asn1c from an ASN.1 module, which its repository carried until 2019 (`src/libacars/asn1/fans-cpdlc.asn1`, last at commit `1568a7b`) and which now lives in a separate, private repository.

**Decision.** `spec/03-domain/cpdlc-fans1a.asn1` is that 2019 module. The set of its type names equals the set of types in the code libacars 2.2.3 generates, so no type was added or removed since. The element texts (`cpdlc-elements.csv`) and the value labels and units (`cpdlc-types.csv`) were extracted from libacars 2.2.3's text formatter.

## F-H14: algorithms shared with the DSC seed

Times from file names, ISO 8601 text, day files, distances, the user's location, search and the settings merge are the same problems in both seeds.

**Decision.** `spec/04-algorithms/04-support.md` §4.1 to §4.6 and §4.8 take the DSC seed's rules unchanged and only add what HFDL needs (the center frequency from the file name, the filters, the HFDL setting units). A program implementing both seeds implements them once. Their vectors in `conformance/` are copies of the DSC seed's, plus HFDL cases.

## F-H15: online lookups and their data

Two free services answer aircraft (by ICAO address) and route (by callsign) questions without a key: hexdb.io and adsbdb.com (checked 2026-11-25). Neither states rate limits. adsbdb's README says its route data belongs to David Taylor and Jim Mason and may not be copied, published or built into other databases without permission; hexdb credits PlaneBase/PlanePlotter, Jim Mason and others.

**Decision.** Both are optional and off by default; hexdb is tried first. Requests are limited to 1 per second per service and to keys not answered within 24 h (aircraft) or 6 h (route). Results are cached only to show them (and stored in the message records that used them, as what was known at reception); the program offers no export or bulk download of them.

## F-H16: the frame's padding

The PDU fills the start of a frame. The 2026-11-25 recordings show that the rest of the frame is not zero: e.g. a 300 bit/s frame with a 47-octet MPDU ends in `…000000003500`. So the convolutional encoder does not end in state 0, and a decoder cannot rely on it.

**Decision.** The padding's content is unspecified (`physical-layer.md` §8). Only the PDU's own octets are compared in `iq/` vectors; the end state of the Viterbi decoder is free (`02-frame.md`). Synthetic frames pad with zeros, so `frame/decode.json` compares whole frames.

## F-H17: which frames of a real recording are required

HF reception has weak frames near the decoder's threshold. Whether they are decoded depends on the decoder's state (gain control, carrier and timing loops), so even the reference finds a different set of weak frames in an excerpt than in the whole recording it was cut from (2026-11-25: 19 common, 6 and 2 different in the first excerpt; an uncut slice at the full rate behaved the same). An exact frame count cannot be required of a different decoder.

**Decision.** In `iq/real.json` each frame is `required` when the reference found it both in the excerpt and in the whole recording, with a signal-to-noise ratio of at least 8 dB; otherwise `optional`. A decoder passes a case when it finds every required frame (channel and PDU octets exact, time within 0.5 s). Optional frames and frames the reference did not find are allowed: any frame whose FCS is good is a correct frame. Synthetic cases (`iq/synthetic.json`) have only required frames.

## F-H18: the recordings

Two recordings by the seed's author, 2026-11-25 from 09:54 UTC, 37 minutes each, made with ShellSDR on the two tuners of an SDRplay RSPduo near Vilnius, 250 kS/s 16-bit I/Q: 8.9 MHz band (center 8902.5 kHz; ground stations 7 Shannon and 3 Reykjavik heard, 1012 messages) and 10 MHz band (center 10058.5 kHz; 2 Molokai, 187 messages). The ShellSDR file names give the start time in **UTC** (the files' metadata says `timezone=UTC`). The excerpts in `iq/` were cut and decimated by `tools/excerpt.py`, with the times, centers and rates in `tools/make_iq_vectors.py`; the originals are not in the seed (2.2 GB each).

## F-H19: the vocabulary of the parse vectors

The parse suites need the decoded fields of every layer, from the HFDL headers to CPDLC message elements. Inventing a new vocabulary for all of them would add a second translation on top of the reference's, with its own errors.

**Decision.** `parse/sequence.json`, `parse/acars.json` and `parse/apps.json` give the expected results as trees in the key names of the reference's JSON output: dumphfdl 1.7.0's (`spdu`, `lpdu`, `hfnpdu`, …) and libacars 2.2.3's (`acars`, `arinc622`, `adsc`, `cpdlc`, `miam`, `media-adv`, `ohma`). It is a documented, widely used format. An implementation's test runner maps its own model to these names (as it maps enumerations in the DSC seed's vectors). Display wording (`name`, `descr`) is not compared. Keys an implementation produces beyond the expected ones are ignored. The vectors were made by the reference (`tools/reference/`), not by hand; their content was spot-checked against `spec/03-domain/` (F-H20, F-H21 record what that found).

## F-H20: an ARINC 622 message whose hex is cut short

libacars stops hex decoding at the first non-hex character. If fewer than 2 octets remain, it still decodes the (empty) application: an ADS-C message with no tags and no error, and a bad CRC.

**Decision.** The same (`parse/apps.json`, case `app-26`), so the output matches the reference.

## F-H21: the wrap of uplink block IDs

`acars.md` first said uplink block IDs wrap after `X`. The reference (libacars' `seq_num_wrap = 'X' - 'A'`, checked as "the previous number + 1 equals it") wraps after `W`: `V, W, A` joins, `W, X, A` breaks at `A`.

**Decision.** `acars.md` §3 says what libacars does; `parse/acars.json` has both cases.

## F-H22: two ADS-C details found while implementing

Writing a decoder from `applications.md` against `parse/apps.json` (ShellSDR 0.4.5) showed two places where the text did not say what libacars does: the reporting interval is `scale × (rate + 1)` seconds, and a `DIS` message's reason is the octet's high four bits. Both are visible in the vectors (`app-11`: interval 0 from scale 0; `app-21`: reason 0 from the octet 8).

**Decision.** `applications.md` says what libacars does. The CPDLC tree vocabulary is now data too: `spec/03-domain/cpdlc-json.csv`, extracted from libacars 2.2.3's JSON formatter.

## F-H23: the Viterbi decoder's end state (amends F-H16)

F-H16 concluded from a frame's non-zero tail that the convolutional encoder does not end in state 0 and that the decoder's end state should be free. Building a receiver (ShellSDR 0.4.5) against `iq/real.json` showed the opposite in practice: ending in the best state, 5 required frames were decoded with one wrong octet near the end (66-octet squitters in 68-octet frames, whose PDU reaches the frame's last bits); forcing state 0, as dumphfdl does, decoded 2 more of them. The non-zero tail seen in F-H16 is what a state-0 traceback produces from whatever was sent there; it does not show the encoder's state.

**Decision.** The decoder ends in state 0 (`02-frame.md`). The padding's content stays unspecified, and `iq/` vectors still compare only the PDU's octets.
