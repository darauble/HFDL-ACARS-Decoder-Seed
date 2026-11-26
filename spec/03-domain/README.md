# Domain: HFDL and ACARS

What is on the air and in the octets, as text and data. Everything here is **normative** unless a section says informative.

| File | Contents |
|---|---|
| `physical-layer.md` + `physical.json` | The channel, the frame (prekey, preamble, training, data), the eight M1 modes, PSK mapping, scrambler, convolutional code, interleaver, bit order |
| `pdu-layers.md` | FCS; SPDU (squitter); MPDU and its headers; LPDU types; HFNPDU (performance data, frequency data, system table, enveloped data); identities and the AC ID table; positions |
| `ground-stations.md` + `ground-stations.csv` | The ground stations (system table version 52): names, positions, frequencies in index order; bands; updates from the air |
| `acars.md` | The ACARS block in HFDL, its check, downlink prefix, sublabel and MFI, reassembly, which application gets the text, labels (informative) |
| `applications.md` | ARINC 622 (ADS-C, FANS-1/A CPDLC), MIAM, media advisory, OHMA |
| `cpdlc-fans1a.asn1` | The FANS-1/A CPDLC ASN.1 module (PER unaligned on the air) |
| `cpdlc-elements.csv` | Every CPDLC message element (uplink uM0..uM182, downlink dM0..dM128) with its text |
| `cpdlc-types.csv` | Labels, units and scales for showing CPDLC values |

The layers, outermost first:

```
 samples ─► frame (physical-layer.md) ─► octets
   ├─ SPDU: squitter ─────────────────────────────────────────── ground-station status
   └─ MPDU ─► LPDU(s) (logon, logoff, data) ─► HFNPDU
                 ├─ performance data, frequency data ───────────── aircraft position
                 ├─ system table (partial) ─► complete table ───── ground stations
                 └─ enveloped data ─► ACARS block ─► reassembly ─► text
                                                     ├─ ARINC 622 ─► ADS-C / CPDLC
                                                     ├─ MIAM ─► core PDU ─► text
                                                     ├─ media advisory
                                                     └─ OHMA ─► JSON
```
