# 2 Frame decoder

From a frame's data symbols to its octets. **Normative** in its result: the inverse of `physical-layer.md` §3 to §7. Soft decisions are recommended (they decode weaker frames); how soft values are scaled is informative.

```
decode_frame(mode, symbols):                     # N × 30 complex symbols, phase resolved
    p = physical.json modes[mode]
    soft = []
    for i, s in enumerate(symbols):
        if scrambler[i mod 120] == 1: s = −s      # §4: undo the scrambler
        soft += soft_bits(s, p.bits_per_symbol)  # most significant bit first, §3
    table = deinterleaver(p.interleaver_columns, p.interleaver_column_shift)
    for b in soft: table.push(b)                 # §6
    coded = [table.pop() for each bit]
    if p.repetition == 2:                        # 300 bit/s: average the two copies
        coded = [mean(coded[2k], coded[2k+1]) for k]
    bits = viterbi(coded, polynomials 0x6D, 0x4F, start state 0, end state 0)   # §5, F-H23
    octets = pack(bits, least significant bit first)                            # §7
    return octets                                # p.user_octets octets; the last one zero-padded
```

- **Soft bits:** a value per bit from "surely 0" to "surely 1" (dumphfdl: 0..255 from liquid-dsp's soft demodulator). A hard decision (nearest constellation point, Gray bits of §3) is a valid soft value of 0 or 255.
- **Viterbi:** maximum-likelihood decoding of the K=7 code over the whole frame, starting in state 0 and **ending in state 0** (as dumphfdl does; F-H23: ending in the best state instead lost frames whose PDU fills the frame, e.g. 66-octet squitters in a 68-octet frame). With error-free symbols any correct decoder gives exactly the octets that were sent; `frame/decode.json` checks the whole frame (its padding is zero), `iq/*.json` only the PDU's octets.
- The decoded octets go to the parser in full. No check here decides whether the frame is good; the FCS in the parser does.
