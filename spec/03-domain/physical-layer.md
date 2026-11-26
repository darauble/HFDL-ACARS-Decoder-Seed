# The HFDL physical layer

How an HFDL frame is put on the air, from the PDU's octets to the symbols. A receiver undoes it in the reverse order (`spec/04-algorithms/`). The constants are data in `physical.json`; this text says what they mean. **Normative**: the frame structure, the sequences, the scrambler, the interleaver, the code, the mappings and the bit orders. How a receiver finds a frame in noise is not prescribed here.

Source: ARINC 635-4 is the standard (not public). Everything here was taken from the open-source decoder dumphfdl 1.7.0 (GPL-3.0-or-later) and **verified by a round trip**: `tools/hfdl_tx.py` (written from this text) produced frames in all eight modes, and dumphfdl decoded every one of them to the same octets (F-H01).

## 1 Channel

- An HFDL channel is named by its **assigned frequency** in kHz, e.g. `8942`. It is the dial frequency of an upper-sideband receiver.
- The signal is centred **1440 Hz above** the assigned frequency and is about 2.4 kHz wide (roughly assigned + 240 Hz to assigned + 2640 Hz).
- Symbols are sent at **1800 Bd**. The pulse is a root-raised-cosine-like shape; `tools/hfdl_tx.py` and the informative receiver use the 19-tap filter at 3 samples per symbol given in `spec/04-algorithms/01-receiver.md`.
- Each channel is used by one ground station. Ground stations and aircraft take turns in a TDMA frame of 32 s divided into 13 slots of 32/13 s (about 2.46 s). A frame on the air takes one slot or two (section 3).

## 2 Frame structure

One frame, in transmission order:

| Part | Symbols | Modulation | Content |
|---|---|---|---|
| Prekey | 448 | BPSK | for the receiver's gain control; its content is not needed to decode (F-H03) |
| A | 127 | BPSK | the bits `A` of `physical.json` |
| A | 127 | BPSK | `A` again |
| M1 | 127 | BPSK | the mode's `m1` bits: says the data rate and the frame length |
| M2 | 15 | BPSK | the mode's `m2` bits (the first 15 bits of its `m1`) |
| Training | 9 × 15 | BPSK | `T` nine times |
| Data | N × (30 + 15) | per mode | N segments: 30 data symbols, then `T` (15 symbols) |

- N is 72 for a single-slot frame and 168 for a double-slot frame. A single-slot frame is 4219 symbols (2.344 s), a double-slot frame 8539 symbols (4.744 s). The last data segment is followed by its `T` too.
- **BPSK mapping:** bit 0 is the symbol +1, bit 1 is -1.
- A receiver may lock onto the carrier with the opposite phase. Then every BPSK bit comes out inverted, and A correlates negatively. That tells the receiver to invert (section 4).

### The M1 modes

The M1 sequence is one 127-bit pattern, sent with one of eight cyclic shifts. The shift says the mode:

| M1 index | Shift | Slots | Modulation | Code | Data rate | User bits per frame | Octets |
|---|---|---|---|---|---|---|---|
| 0 | 72 | 1 | BPSK | 1/2, each bit twice | 300 bit/s | 540 | 68 |
| 1 | 82 | 1 | BPSK | 1/2 | 600 bit/s | 1080 | 135 |
| 2 | 113 | 1 | 4-PSK | 1/2 | 1200 bit/s | 2160 | 270 |
| 3 | 123 | 1 | 8-PSK | 1/2 | 1800 bit/s | 3240 | 405 |
| 4 | 61 | 2 | BPSK | 1/2, each bit twice | 300 bit/s | 1260 | 158 |
| 5 | 103 | 2 | BPSK | 1/2 | 600 bit/s | 2520 | 315 |
| 6 | 93 | 2 | 4-PSK | 1/2 | 1200 bit/s | 5040 | 630 |
| 7 | 9 | 2 | 8-PSK | 1/2 | 1800 bit/s | 7560 | 945 |

- The data rate is 1800 × bits per symbol ÷ code rate × 30/45 (the training segments take a third of the time).
- "Octets" is the user bits rounded up to whole octets. A PDU is shorter than the frame; the rest is zero (section 8).

## 3 Data symbols: PSK mapping

- A data symbol carries `b` bits: 1 (BPSK), 2 (4-PSK) or 3 (8-PSK). The bits are taken **most significant first**.
- The `b` bits form a number `g`. The symbol's phase index is `k = gray_decode(g)`, and the symbol is `exp(j·2π·k / 2^b)`. So phase 0 (the symbol +1) is `000`, and neighbouring phases differ in one bit.
- `gray_decode` is the inverse of `gray_encode(k) = k XOR (k >> 1)`.

| 8-PSK k (phase) | 0 (0°) | 1 (45°) | 2 (90°) | 3 (135°) | 4 (180°) | 5 (225°) | 6 (270°) | 7 (315°) |
|---|---|---|---|---|---|---|---|---|
| bits | 000 | 001 | 011 | 010 | 110 | 111 | 101 | 100 |

4-PSK: k 0..3 at 0°, 90°, 180°, 270° are `00 01 11 10`. BPSK: `0` at 0°, `1` at 180°.

## 4 Scrambler

- Data symbols (not the preamble, not the training segments) are **multiplied by -1** where the scrambler bit is 1. For 8-PSK and 4-PSK that is a 180° turn, not an XOR of the bits.
- The scrambler bits are the 120-bit string `scrambler` of `physical.json`, applied to data symbols 0, 1, 2, … of the frame, and restarted every 120 data symbols. 120 divides both frames' data symbol counts (2160 and 5040), so every frame starts at its beginning.
- The string is the output of a 15-bit LFSR: `state = 0x4D4B`; per bit: `b = parity(state AND 0x4001)`, `state = ((state << 1) OR b) AND 0x7FFF`, output `b`. The data file is normative; the LFSR is how it was made (F-H02).
- A receiver that locked with the opposite phase (section 2) also turns every data symbol by 180°, before it applies the scrambler.

## 5 Convolutional code

- Code rate 1/2, constraint length 7. The register starts at 0. For each input bit `x`: `reg = ((reg << 1) OR x) AND 0x7F`; output `c0 = parity(reg AND 0x6D)`, then `c1 = parity(reg AND 0x4F)`.
- These are the libfec `viterbi27` polynomials (the K=7 code with octal 133 and 171, bit-reversed). No tail bits are added, and the bits after the PDU are not necessarily zero (section 8), so the register's final state is unknown. Only the PDU's own octets are guaranteed; a PDU always ends well before the frame does.
- **300 bit/s** (modes 0 and 4): each coded bit is sent twice, back to back: `c0 c0 c1 c1 …`. The receiver averages the two copies.

## 6 Interleaver

The coded bits are spread over the frame so that a fade destroys scattered bits, not a run. It is defined by the receiver's table: 40 rows, `C` columns (`interleaver_columns`: coded bits per frame ÷ 40) and a column shift `S` (`interleaver_column_shift`: 17 single slot, 23 double slot).

**Push** (the bits as received, in symbol order, most significant bit of each symbol first): start at row 0, column 0. For each bit:

```
table[row][col] = bit
row = row + 1
if row == 40: row = 0; col = col + 1
col = col - S
if col < 0: col = col + C
```

**Pop** (the bits in code order, to the decoder): start at row 0, column 0. For each bit:

```
bit = table[row][col]
row = (row + 9) mod 40
if row == 0: col = col + 1
```

Push and pop each visit every cell once. A transmitter puts the k-th coded bit where pop reads its k-th bit, and sends the cells in push order (`tools/hfdl_tx.py`, `interleaver_maps`).

## 7 Bit order of the user data

- The PDU's octets are sent first octet first, and within an octet **least significant bit first**. That bit stream is the code's input (section 5).
- A decoder that collects decoded bits most significant first per octet must reverse each octet's bits (dumphfdl does).

## 8 What a frame carries

- One frame carries the bits of one PDU (an MPDU or an SPDU, `pdu-layers.md`), from the first decoded bit. The rest of the frame, after the PDU, is padding of **unspecified** content: real frames carry non-zero octets there (F-H16). Synthetic frames (`tools/hfdl_tx.py`) send zeros.
- The receiver hands all the frame's octets (68 to 945, per mode) to the PDU parser. The parser takes the PDU's length from its header; it never relies on the zeros.
- The first octet tells the kind: its least significant bit is 1 for an MPDU, 0 for an SPDU.

## 9 Timing of a frame

- A frame's **time** is the instant its first symbol (the prekey) began: the instant the second A ended, minus (448 + 2 × 127) symbol periods. In a recording, it is the recording's start time plus the sample position, converted with the sample rate (`DEC-06`).
- The bits, octets and parsed fields do not depend on the time.
