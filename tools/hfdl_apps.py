#!/usr/bin/env python3
"""Encoders for ACARS application texts, written from
spec/03-domain/applications.md, for synthetic vectors: ARINC 622 with ADS-C
and FANS-1/A CPDLC (CPDLC needs the Python package asn1tools), MIAM, media
advisory and OHMA.
"""
import base64
import json
import struct
import zlib
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent


# ── checks ──────────────────────────────────────────────────────────────────

def crc16_ccitt_false(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def crc32_bzip2(data):
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
    return crc ^ 0xFFFFFFFF


# ── ARINC 622 ──────────────────────────────────────────────────────────────

def arinc622(gs_addr, imi, reg, payload, slash=True, bad_crc=False):
    """Text of an ARINC 622 message: [/]GSADDR.IMI REG(7) HEX(payload + CRC)."""
    reg7 = reg.rjust(7, ".")[:7]
    body = (imi + reg7).encode() + bytes(payload)
    c = crc16_ccitt_false(body) ^ 0xFFFF          # sent complemented, high octet first
    crc = bytes([c >> 8, c & 0xFF])
    assert crc16_ccitt_false(body + crc) == 0x1D0F
    if bad_crc:
        crc = bytes([crc[0] ^ 0x01, crc[1]])
    return ("/" if slash else "") + f"{gs_addr}.{imi}{reg7}" + (bytes(payload) + crc).hex().upper()


# ── ADS-C ──────────────────────────────────────────────────────────────────

class Bits:
    def __init__(self):
        self.v, self.n = 0, 0

    def put(self, value, width):
        self.v = (self.v << width) | (value & ((1 << width) - 1))
        self.n += width
        return self

    def octets(self):
        pad = (-self.n) % 8
        return (self.v << pad).to_bytes((self.n + pad) // 8, "big")


def coord21(deg):
    return round(deg * 0xFFFFF / (180 - 90 / 2 ** 19))


def angle(deg, width, lsb_exp):
    if deg > 180:
        deg -= 360
    return round(deg * ((1 << (width - 1)) - 1) / (180 - 90 / 2 ** lsb_exp))


def basic_report(tag, lat, lon, alt_ft, ts_s, redundancy=1, accuracy=7, tcas=1):
    b = Bits().put(coord21(lat), 21).put(coord21(lon), 21).put(alt_ft // 4, 16).put(round(ts_s * 8), 15)
    b.put((tcas << 4) | (accuracy << 1) | redundancy, 7)
    return bytes([tag]) + b.octets()


def flight_id(fid):
    b = Bits()
    for ch in fid.ljust(8)[:8]:
        o = ord(ch)
        b.put(o - 0x40 if 0x41 <= o <= 0x5A else o, 6)
    return bytes([12]) + b.octets()


def earth_ref(track_deg, gs_kt, vs_fpm, invalid=0):
    b = Bits().put(invalid, 1).put(angle(track_deg, 12, 10), 12).put(round(gs_kt * 2), 13).put(vs_fpm // 16, 12)
    return bytes([14]) + b.octets()


def air_ref(hdg_deg, mach, vs_fpm, invalid=0):
    b = Bits().put(invalid, 1).put(angle(hdg_deg, 12, 10), 12).put(round(mach * 2000), 13).put(vs_fpm // 16, 12)
    return bytes([15]) + b.octets()


def meteo(wind_kt, wind_dir, temp_c, invalid=0):
    t = round(temp_c * 0x7FF / (512 - 256 / 2 ** 10))
    b = Bits().put(round(wind_kt * 2), 9).put(invalid, 1).put(angle(wind_dir, 9, 7), 9).put(t, 12)
    return bytes([16]) + b.octets()


def airframe_id(icao):
    return bytes([17]) + icao.to_bytes(3, "big")


def predicted_route(lat1, lon1, alt1, eta1, lat2, lon2, alt2):
    b = Bits().put(coord21(lat1), 21).put(coord21(lon1), 21).put(alt1 // 4, 16).put(eta1, 14)
    b.put(coord21(lat2), 21).put(coord21(lon2), 21).put(alt2 // 4, 16)
    return bytes([13]) + b.octets()


def fixed_projection(lat, lon, alt, eta):
    b = Bits().put(coord21(lat), 21).put(coord21(lon), 21).put(alt // 4, 16).put(eta, 14)
    return bytes([23]) + b.octets()


def intermediate_projection(dist_nm, track, alt, eta):
    b = Bits().put(round(dist_nm * 8), 16).put(0, 1).put(angle(track, 12, 10), 12).put(alt // 4, 16).put(eta, 14)
    return bytes([22]) + b.octets()


def contract_request(tag, contract, interval_scale, interval_rate, modulus_tags=(13, 15)):
    out = bytes([tag, contract, 11, (interval_scale << 6) | interval_rate])
    for t in modulus_tags:
        out += bytes([t, 1])
    return out


def event_contract(contract, alt_ceiling, alt_floor, vs_threshold):
    out = bytes([8, contract, 19]) + (alt_ceiling // 4).to_bytes(2, "big", signed=True) + (alt_floor // 4).to_bytes(2, "big", signed=True)
    out += bytes([18, (vs_threshold // 64) & 0xFF, 20])
    return out


# ── CPDLC ──────────────────────────────────────────────────────────────────

_cpdlc = None


def cpdlc(direction, value):
    global _cpdlc
    if _cpdlc is None:
        import asn1tools
        _cpdlc = asn1tools.compile_files(str(SEED / "spec/03-domain/cpdlc-fans1a.asn1"), "uper")
    return _cpdlc.encode("FANSATCUplinkMessage" if direction == "u" else "FANSATCDownlinkMessage", value)


# ── MIAM ───────────────────────────────────────────────────────────────────

def base85(data):
    pad = (-len(data)) % 4
    data += bytes(pad)
    out = ""
    for i in range(0, len(data), 4):
        v = int.from_bytes(data[i:i + 4], "big")
        if v == 0:
            out += "z"
            continue
        digits = []
        for _ in range(5):
            digits.append(chr(v % 85 + 33))
            v //= 85
        out += "".join(reversed(digits))
    return out, pad


def deflate_raw(data):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()


def miam_v2_data(msg_num, app_id, text, compress=True, encoded_body=True, bad_crc=False):
    body_plain = text.encode()
    crc = crc16_ccitt_false(body_plain)
    if bad_crc:
        crc ^= 0x0101
    comp = 1 if compress else 0
    app_type = {2: 0, 4: 1, 6: 2}[len(app_id)]
    hdr = bytes([0x02, (msg_num << 1) | 0, (comp >> 2) & 1, ((comp & 3) << 6) | (0 << 4) | app_type])
    hdr += app_id.encode() + crc.to_bytes(2, "big")
    body = deflate_raw(body_plain) if compress else body_plain
    h85, hpad = base85(hdr)
    if encoded_body:
        b85, bpad = base85(body)
        return f"{bpad}{hpad}{h85}|{b85}"
    return f"-{hpad}{h85}|{body.decode('latin-1')}"


def miam_v1_data(msg_num, aircraft, app_id, text):
    body_plain = text.encode()
    crc = crc32_bzip2(body_plain)
    body = deflate_raw(body_plain)
    app_type = {2: 0, 4: 1, 6: 2}[len(app_id)]
    hdr = bytes([0x01]) + bytes(3) + aircraft.rjust(7, ".")[:7].encode()
    hdr += bytes([(msg_num << 1) | 1, 0, (1 << 6) | app_type]) + app_id.encode() + crc.to_bytes(4, "big")
    total = len(hdr) + len(body)
    hdr = hdr[:1] + total.to_bytes(3, "big") + hdr[4:]
    h85, hpad = base85(hdr)
    b85, bpad = base85(body)
    return f"{bpad}{hpad}{h85}|{b85}"


# ── OHMA ───────────────────────────────────────────────────────────────────

def ohma(obj, prefix="OHMA"):
    z = zlib.compress(json.dumps(obj, separators=(",", ":")).encode(), 9)
    return prefix + base64.b64encode(z).decode()
