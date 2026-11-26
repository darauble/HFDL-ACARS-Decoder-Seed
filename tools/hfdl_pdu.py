#!/usr/bin/env python3
"""Builds HFDL PDUs (octets) for synthetic test vectors, from
spec/03-domain/pdu-layers.md and acars.md. Import it, or run it to print the
PDUs of a small built-in example set as hex.

Fields this builder does not model (reserved, slot selection, acknowledgement
codes) are sent as zero.
"""

import math


# ── checks ──────────────────────────────────────────────────────────────────

def crc16_x25(data):
    """HFDL FCS: CRC-16, reflected poly 0x1021 (0x8408), init 0xFFFF, final
    XOR 0xFFFF (CRC-16/X-25). Sent low octet first."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc ^ 0xFFFF


def crc16_kermit(data):
    """ACARS block check: CRC-16, reflected poly 0x1021, init 0, no final
    XOR (CRC-16/KERMIT). Sent low octet first; over the received block
    including it, the CRC is 0."""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc


def with_fcs(data):
    c = crc16_x25(data)
    return bytes(data) + bytes([c & 0xFF, c >> 8])


def rev8(b):
    return int(f"{b:08b}"[::-1], 2)


def icao_octets(icao):
    """An ICAO 24-bit address in an LPDU: three octets, most significant
    first, each bit-reversed."""
    return bytes(rev8((icao >> s) & 0xFF) for s in (16, 8, 0))


def coord20(deg):
    """A coordinate: 20-bit two's complement, deg * 0x7FFFF / 180."""
    v = int(round(deg * 0x7FFFF / 180.0))
    return v & 0xFFFFF


def latlon(lat, lon):
    a, b = coord20(lat), coord20(lon)
    return bytes([a & 0xFF, (a >> 8) & 0xFF, ((a >> 16) & 0x0F) | ((b & 0x0F) << 4),
                  (b >> 4) & 0xFF, (b >> 12) & 0xFF])


def u16(v):
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


# ── SPDU (squitter) ────────────────────────────────────────────────────────

def spdu(gs_id, utc_sync=True, version=0, rls=False, iso=False, change_note=0,
         frame_index=0, frame_offset=0, min_priority=0, systable_version=51,
         freqs_in_use=0, others=((0, False, 0), (0, False, 0))):
    b = bytearray(64)
    b[0] = (rls << 1) | ((version & 3) << 2) | (iso << 5) | ((change_note & 3) << 6)
    b[1] = (gs_id & 0x7F) | (0x80 if utc_sync else 0)
    b[2] = frame_index & 0xFF
    b[3] = ((frame_index >> 8) & 0x0F) | ((frame_offset & 0x0F) << 4)
    b[52] = min_priority & 0x0F
    b[53] = systable_version & 0xFF
    b[54] = ((systable_version >> 8) & 0x0F) | ((freqs_in_use & 0x0F) << 4)
    b[55] = (freqs_in_use >> 4) & 0xFF
    b[56] = (freqs_in_use >> 12) & 0xFF
    (id1, s1, f1), (id2, s2, f2) = others
    b[57] = (id1 & 0x7F) | (0x80 if s1 else 0)
    b[58] = f1 & 0xFF
    b[59] = (f1 >> 8) & 0xFF
    b[60] = ((f1 >> 16) & 0x0F) | ((id2 & 0x0F) << 4)
    b[61] = ((id2 >> 4) & 0x07) | (0x08 if s2 else 0) | ((f2 & 0x0F) << 4)
    b[62] = (f2 >> 4) & 0xFF
    b[63] = (f2 >> 12) & 0xFF
    return with_fcs(b)


# ── MPDU ───────────────────────────────────────────────────────────────────

def mpdu_downlink(src_ac, dst_gs, lpdus):
    n = len(lpdus)
    assert 1 <= n <= 15
    hdr = bytearray(6)
    hdr[0] = 0x01 | 0x02 | (n << 2)
    hdr[1] = dst_gs & 0x7F
    hdr[2] = src_ac & 0xFF
    hdr += bytes(len(l) - 1 for l in lpdus)
    return with_fcs(hdr) + b"".join(lpdus)


def mpdu_uplink(src_gs, per_aircraft, utc_sync=True):
    """per_aircraft: [(ac_id, [lpdu, ...]), ...] (1..8 aircraft)."""
    assert 1 <= len(per_aircraft) <= 8
    hdr = bytearray(2)
    hdr[0] = 0x01 | ((len(per_aircraft) - 1) << 4)
    hdr[1] = (src_gs & 0x7F) | (0x80 if utc_sync else 0)
    data = b""
    for ac_id, lpdus in per_aircraft:
        hdr += bytes([ac_id & 0xFF, (len(lpdus) & 0x0F) << 4])
        hdr += bytes(len(l) - 1 for l in lpdus)
        data += b"".join(lpdus)
    return with_fcs(hdr) + data


# ── LPDU ───────────────────────────────────────────────────────────────────

UNNUMBERED_DATA = 0x0D
UNNUMBERED_ACKED_DATA = 0x1D
LOGON_DENIED = 0x2F
LOGOFF_REQUEST = 0x3F
LOGON_RESUME = 0x4F
LOGON_RESUME_CONFIRM = 0x5F
LOGON_REQUEST_NORMAL = 0x8F
LOGON_CONFIRM = 0x9F
LOGON_REQUEST_DLS = 0xBF


def lpdu(ltype, body=b""):
    return with_fcs(bytes([ltype]) + bytes(body))


def lpdu_logon_request(icao, hfnpdu=b"", ltype=LOGON_REQUEST_DLS):
    return lpdu(ltype, icao_octets(icao) + hfnpdu)


def lpdu_logon_confirm(icao, ac_id, ltype=LOGON_CONFIRM):
    return lpdu(ltype, icao_octets(icao) + bytes([ac_id, 0, 0, 0]))


def lpdu_logoff(icao, reason, ltype=LOGOFF_REQUEST):
    return lpdu(ltype, icao_octets(icao) + bytes([reason]))


# ── HFNPDU ─────────────────────────────────────────────────────────────────

def flight6(fid):
    return fid.encode("ascii")[:6].ljust(6, b" ")


def utc2(h, m, s):
    return u16((h * 3600 + m * 60 + s) // 2)


def hfnpdu_frequency_data(flight, lat, lon, hms, prop):
    """prop: [(gs_id, propagating_mask, tuned_mask), ...] (0..6)."""
    b = bytes([0xFF, 0xD5]) + flight6(flight) + latlon(lat, lon) + utc2(*hms)
    for gs, pf, tf in prop:
        b += bytes([gs & 0x7F, pf & 0xFF, (pf >> 8) & 0xFF,
                    ((pf >> 16) & 0x0F) | ((tf & 0x0F) << 4), (tf >> 4) & 0xFF, (tf >> 12) & 0xFF])
    return b


def hfnpdu_performance_data(flight, lat, lon, hms, version=1, flight_leg=1, gs_id=0,
                            freq_id=0, freq_change_code=7):
    b = bytearray([0xFF, 0xD1]) + flight6(flight) + latlon(lat, lon) + utc2(*hms)
    b += bytes([version, flight_leg, gs_id & 0x7F, freq_id])
    b += bytes(46 - 19)            # leg statistics, MPDU and SPDU counts
    b += bytes([freq_change_code & 0x0F])
    assert len(b) == 47
    return bytes(b)


def hfnpdu_enveloped(acars_block):
    return bytes([0xFF, 0xFF]) + acars_block


def bcd_freq(khz):
    """A frequency as 3 BCD octets, units of 100 Hz, least significant digit first."""
    d = f"{int(round(khz * 10)):06d}"[::-1]          # 100 Hz digits, least significant first
    return bytes([int(d[0]) | int(d[1]) << 4, int(d[2]) | int(d[3]) << 4, int(d[4]) | int(d[5]) << 4])


def systable_parts(version, stations, nparts):
    """A complete system table split into `nparts` HFNPDUs (pdu-layers.md §7.4).
    stations: [(gs_id, utc_sync, lat, lon, spdu_version, [(khz, master_slot), ...]), ...]"""
    data = b""
    for gs, sync, lat, lon, ver, freqs in stations:
        data += bytes([(gs & 0x7F) | (0x80 if sync else 0)]) + latlon(lat, lon)
        data += bytes([(ver & 7) | (len(freqs) << 3)])
        for khz, slot in freqs:
            data += bcd_freq(khz) + bytes([slot & 0x0F])
    size = -(-len(data) // nparts)
    parts = []
    for i in range(nparts):
        chunk = data[i * size:(i + 1) * size]
        parts.append(bytes([0xFF, 0xD0, ((nparts - 1) << 4) | i, (version & 0x0F) << 4, (version >> 4) & 0xFF]) + chunk)
    return parts


# ── ACARS ──────────────────────────────────────────────────────────────────

def odd_parity(c):
    c &= 0x7F
    return c | (0x80 if bin(c).count("1") % 2 == 0 else 0)


def acars(mode, reg, label, block_id, text="", ack=0x15, msg_num=None, flight=None,
          final=True):
    """One ACARS block as carried in HFDL: SOH, then mode, registration
    (7, right-aligned with dots), ack, label, block id, [STX text],
    ETX or ETB, CRC (2 octets), DEL. Characters carry odd parity; the CRC is
    over the octets with parity, from mode through ETX/ETB."""
    body = mode + reg.rjust(7, ".")[:7]
    body = [ord(c) for c in body] + [ack] + [ord(c) for c in label] + [ord(block_id)]
    if text or msg_num is not None:
        txt = ""
        if msg_num is not None:
            txt += msg_num + (flight or "").ljust(6)[:6]
        txt += text
        body += [0x02] + [ord(c) for c in txt]
    body += [0x03 if final else 0x17]
    body = [odd_parity(c) for c in body]
    crc = crc16_kermit(bytes(body))
    return bytes([0x01]) + bytes(body) + bytes([crc & 0xFF, crc >> 8, 0x7F])


# ── example set ────────────────────────────────────────────────────────────

def examples():
    """A few PDUs of each kind, used by conformance/synthetic/."""
    ex = {}
    ex["spdu-shannon"] = spdu(7, frame_index=1235, systable_version=51, freqs_in_use=0b111,
                              others=((3, True, 0b10), (11, True, 0b1000)))
    ex["logon-request-freq-data"] = mpdu_downlink(
        255, 3, [lpdu_logon_request(0x151DAD, hfnpdu_frequency_data(
            "SU1735", 62.2671934, 48.9167193, (10, 58, 12), [(3, 0b111, 0b1), (7, 0b11, 0)]))])
    ex["logon-confirm"] = mpdu_uplink(3, [(46, [lpdu_logon_confirm(0x151DAD, 46)])])
    ex["performance-data"] = mpdu_downlink(
        46, 3, [lpdu(UNNUMBERED_DATA, hfnpdu_performance_data(
            "SU1003", 55.1234567, 37.7654321, (8, 9, 0), gs_id=3, freq_id=1))])
    ex["acars-h1-downlink"] = mpdu_downlink(
        23, 7, [lpdu(UNNUMBERED_ACKED_DATA, hfnpdu_enveloped(acars(
            "2", "RA73824", "H1", "4", "#CFBMPF/ENG 1 FIRE LOOP B FAULT", msg_num="C00A",
            flight="U62905")))])
    ex["acars-uplink-ack"] = mpdu_uplink(7, [(115, [lpdu(UNNUMBERED_DATA, hfnpdu_enveloped(
        acars("2", "XA-ADC", "_\x7f", "N", ack=ord("8"))))])])
    return ex


if __name__ == "__main__":
    for k, v in examples().items():
        print(k, len(v), v.hex())
