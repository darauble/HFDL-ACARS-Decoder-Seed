# Tools

Scripts that made or checked parts of the seed. An implementation does not need them.

| File | What it does |
|---|---|
| `hfdl_pdu.py` | Builds PDUs (squitter, MPDU, LPDU, HFNPDU, ACARS) as octets, from `spec/03-domain/`. `python3 tools/hfdl_pdu.py` prints its example set. |
| `hfdl_tx.py` | An HFDL transmitter: frames (PDU octets, mode, time, frequency) → complex baseband I/Q (`.cf32` or 16-bit stereo `.wav`), from `spec/03-domain/physical-layer.md` and `physical.json`. |
| `hfdl_apps.py` | Encoders for ACARS application texts: ARINC 622, ADS-C, CPDLC (with `asn1tools`), MIAM, OHMA. |
| `excerpt.py` | Cuts, shifts and decimates an excerpt of a long I/Q recording, or makes the USB audio of one channel. |
| `make_iq_vectors.py` | `conformance/iq/real.json` and its excerpts, from the original recordings and the reference. |
| `make_synthetic.py` | `conformance/frame/decode.json` and `conformance/iq/synthetic.json` with its WAV files. |
| `frame_check.py` | A frame decoder written from `spec/04-algorithms/02-frame.md`; must reproduce `frame/decode.json`. |
| `make_parse_vectors.py` | `conformance/parse/sequence.json` from the reference's output of whole recordings. |
| `make_acars_vectors.py` | `conformance/parse/acars.json`, with `reference/acars_seq.c` on libacars. |
| `make_apps_vectors.py` | `conformance/parse/apps.json`, with libacars' `decode_acars_apps`. |
| `make_support_vectors.py` | The suites computed from the seed's own rules, and the copies of the DSC seed's shared suites. |
| `make_manifest.py` | `conformance/manifest.json`. |
| `reference/reference.patch` | The changes to dumphfdl 1.7.0 for the reference build: frame times from the sample count (`HFDL_SAMPLE_CLOCK_BASE`), the PDUs' octets in its JSON (`raw`). Apply in `dumphfdl-up/` before `docker build`. |
| `roundtrip-frames.json` | The frames of the round trip of F-H01: the example PDUs in all eight modes on 8942 kHz, 48 kS/s centred on 8935 kHz. |
| `reference/Dockerfile` | Builds the reference decoder: dumphfdl 1.7.0 with libacars 2.2.3 and liquid-dsp 1.6.0 (Ubuntu 24.04). Put the libacars and dumphfdl sources (`git clone https://github.com/szpajder/libacars`, `…/dumphfdl`) next to it as `libacars/` and `dumphfdl-up/`. |

## The round trip (F-H01)

```
python3 tools/hfdl_tx.py tools/roundtrip-frames.json /tmp/rt/test.cf32
docker build -t hfdl-ref tools/reference      # with the sources next to the Dockerfile
docker run --rm -v /tmp/rt:/rt hfdl-ref dumphfdl --iq-file /rt/test.cf32 \
    --sample-format CF32 --sample-rate 48000 --centerfreq 8935 8942 --output-mpdus --raw-frames
```

Every frame must come out with the octets `hfdl_pdu.py` printed for it.
