#!/usr/bin/env python3
"""Builds conformance/parse/apps.json: ACARS application texts (direction,
label, text) -> what the reference (libacars' decode_acars_apps, in the
`hfdl-ref` image) decodes, as JSON.

    python3 tools/make_apps_vectors.py [REFERENCE_JSON ...]

REFERENCE_JSON: the reference's decoded output of recordings; their ARINC 622,
MIAM and media advisory texts are added as real cases. Synthetic cases come
from tools/hfdl_apps.py (CPDLC needs asn1tools).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE.parent
sys.path.insert(0, str(HERE))
import hfdl_apps as A  # noqa: E402

DOC = [  # libacars' documentation and examples (MIT)
    ("d", "B6", "/BOMASAI.ADS.VT-ANB072501A070A988CA73248F0E5DC10200000F5EE1ABC000102B885E0A19F5", "ADS-C basic report, earth/air reference, meteo"),
    ("d", "B6", "/LPAFAYA.ADS.VQ-BPJ1423CCA85D2D090886301D0D24C7D0704309088442255CC87CE2C90880DF97", "ADS-C report with predicted route"),
    ("d", "H1", "#M1B/B6 LHWE1YA.ADS.N572UP07263B5872A048C9F21C1F0E5B88D700000239", "ADS-C in H1 with sublabel M1 and MFI B6"),
    ("u", "AA", "/AKLCDYA.AT1.9V-SVG21D0755D84AD067448398722949A7521C8AB4A1C8EAB5CE393", "CPDLC uplink"),
    ("u", "AA", "/AKLCDYA.AT1.9M-MTB215B659D84995674293583561CB9906744E9AF40F9EB", "CPDLC uplink"),
    ("d", "B6", "/CTUE1YA.ADS.HB-JNB1424AB686D9308CA2EBA1D0D24A2C06C1B48CA004A248050667908CA004BF6", "ADS-C"),
    ("d", "BA", "/MSTEC7X.AT1.VT-ANE21409DCC3DD03BB52350490502B2E5129D5A15692BA009A08892E7CC831E210A4C06EEBC28B1662BC02360165C80E1F7", "CPDLC downlink"),
    ("u", "H1", "- #MD/AA ATLTWXA.CR1.N856DN203A3AA8E5C1A9323EDD", "CPDLC connect request in H1 (uplink sublabel and MFI)"),
    ("d", "SA", "0EV192001VS", "media advisory"),
    ("d", "H1", "#T2BT-3![[mS0L8ZeIK0?J|EDDF", "MIAM-like text after a sublabel (libacars example)"),
]


def synthetic():
    c = []
    rep = A.basic_report(7, 52.5, 21.25, 36000, 1234.5) + A.flight_id("LOT27") + A.earth_ref(271.5, 487.0, -64) + A.airframe_id(0x48AE1A)
    c.append(("d", "A6", A.arinc622("WAWSAYA", "ADS", "SP-LRA", rep), "ADS-C basic report, flight ID, earth reference, airframe ID"))
    emerg = A.basic_report(9, -12.345, -150.5, 31000, 2.0, accuracy=3, tcas=0) + A.meteo(55.5, 300.0, -48.25)
    c.append(("d", "B6", A.arinc622("PAOFAYA", "ADS", "N784AV", emerg), "ADS-C EMERGENCY basic report (tag 9), meteo"))
    c.append(("d", "B6", A.arinc622("PAOFAYA", "ADS", "N784AV", A.basic_report(7, 10, 20, 30000, 100) + A.air_ref(45.0, 0.82, 1024)), "ADS-C with air reference"))
    c.append(("d", "B6", A.arinc622("REKCAYA", "ADS", "A6-BNI", A.predicted_route(60.1, -20.2, 38000, 900, 61.0, -15.5, 38000) + A.fixed_projection(62, -10, 37000, 1800) + A.intermediate_projection(150.5, 92.5, 37000, 1200)), "ADS-C predicted route, fixed and intermediate projection"))
    c.append(("d", "B6", A.arinc622("REKCAYA", "ADS", "A6-BNI", bytes([3, 12])), "ADS-C acknowledgement"))
    c.append(("d", "B6", A.arinc622("REKCAYA", "ADS", "A6-BNI", bytes([4, 12, 7, 99])), "ADS-C NACK with an erroneous tag number"))
    c.append(("d", "B6", A.arinc622("REKCAYA", "ADS", "A6-BNI", bytes([5, 12, 2, 13, 0x40, 16, 0x03, 0x12, 0x30])), "ADS-C noncompliance: a whole group and three parameters"))
    c.append(("d", "B6", A.arinc622("REKCAYA", "DIS", "A6-BNI", bytes([8])), "ADS-C disconnect, normal"))
    c.append(("u", "A6", A.arinc622("REKCAYA", "ADS", "A6-BNI", A.contract_request(7, 12, 2, 10) + A.event_contract(13, 41000, 29000, -128)), "ADS-C periodic (8 x 10 s) and event contract requests"))
    c.append(("u", "A6", A.arinc622("REKCAYA", "ADS", "A6-BNI", bytes([1])), "ADS-C cancel all contracts"))
    c.append(("d", "B6", A.arinc622("REKCAYA", "ADS", "A6-BNI", bytes([7, 1, 2])), "ADS-C basic report cut short: an error"))
    c.append(("d", "B6", A.arinc622("REKCAYA", "ADS", "A6-BNI", A.basic_report(7, 50, 10, 35000, 60), bad_crc=True), "ADS-C with a bad ARINC 622 CRC: decoded, CRC flagged"))
    c.append(("d", "B6", "/REKCAYA.ADS.A6-BNI07ZZ", "ARINC 622 hex cut by a non-hex character"))
    c.append(("d", "B6", "/REKCAYA-ADS.A6-BNI0701", "no IMI: not ARINC 622"))
    try:
        c.append(("u", "AA", A.arinc622("REKCAYA", "AT1", "A6-BNI", A.cpdlc("u", {"aTCMessageheader": {"msgIdentificationNumber": 5, "timestamp": {"hours": 9, "minutes": 58, "seconds": 7}}, "aTCuplinkmsgelementId": ("uM20Altitude", ("altitudeFlightLevel", 350))})), "CPDLC uplink: CLIMB TO AND MAINTAIN FL350"))
        c.append(("d", "BA", A.arinc622("REKCAYA", "AT1", "N784AV", A.cpdlc("d", {"aTCMessageheader": {"msgIdentificationNumber": 6, "msgReferenceNumber": 5}, "aTCDownlinkmsgelementid": ("dM0NULL", None)})), "CPDLC downlink: WILCO"))
        c.append(("d", "BA", A.arinc622("REKCAYA", "AT1", "N784AV", A.cpdlc("d", {"aTCMessageheader": {"msgIdentificationNumber": 7}, "aTCDownlinkmsgelementid": ("dM56NULL", None), "aTCdownlinkmsgelementid-seqOf": [("dM57RemainingFuelRemainingSouls", {"remainingFuel": {"hours": 2, "minutes": 30}, "remainingSouls": 174})]})), "CPDLC downlink: MAYDAY MAYDAY MAYDAY, fuel and souls on board"))
        c.append(("d", "BA", A.arinc622("REKCAYA", "AT1", "N784AV", A.cpdlc("d", {"aTCMessageheader": {"msgIdentificationNumber": 8}, "aTCDownlinkmsgelementid": ("dM55NULL", None), "aTCdownlinkmsgelementid-seqOf": [("dM61Altitude", ("altitudeFlightLevel", 100))]})), "CPDLC downlink: PAN PAN PAN, descending to FL100"))
        c.append(("d", "BA", A.arinc622("REKCAYA", "AT1", "N784AV", A.cpdlc("d", {"aTCMessageheader": {"msgIdentificationNumber": 9}, "aTCDownlinkmsgelementid": ("dM67FreeText", "MEDICAL EMERGENCY ON BOARD")})), "CPDLC downlink free text"))
        c.append(("d", "BA", A.arinc622("REKCAYA", "CR1", "N784AV", b""), "CPDLC connect request with an empty message"))
        c.append(("d", "BA", A.arinc622("REKCAYA", "AT1", "N784AV", bytes([0xFF, 0xFF, 0xFF])), "CPDLC that does not decode"))
    except ImportError:
        print("asn1tools missing: CPDLC cases skipped")
    c.append(("d", "MA", "T" + A.miam_v2_data(17, "H1", "#DFBTEST MESSAGE FROM MIAM V2\r\n"), "MIAM single transfer, core v2, deflate"))
    c.append(("d", "MA", "T" + A.miam_v2_data(18, "H1DF", "UNCOMPRESSED BODY", compress=False), "MIAM core v2, no compression, 4-character application ID"))
    c.append(("d", "MA", "T" + A.miam_v2_data(19, "H1", "BODY WITH A BAD CRC", bad_crc=True), "MIAM core v2 with a bad CRC"))
    c.append(("d", "MA", "T" + A.miam_v1_data(20, "F-WMIL", "H1", "CORE V1 MESSAGE BODY"), "MIAM single transfer, core v1, CRC-32"))
    c.append(("d", "MA", "F123000045261125120000", "MIAM file transfer request (21 characters)"))
    c.append(("d", "MA", "K1234010060", "MIAM file transfer accept"))
    c.append(("d", "MA", "A1232", "MIAM file transfer abort, stopped by sender"))
    c.append(("d", "MA", "YFFF", "MIAM pause, all files"))
    c.append(("d", "MA", "X123010060", "MIAM resume"))
    c.append(("d", "SA", "0LH095333VS2/TEXT", "media advisory: HF lost, free text"))
    c.append(("d", "SA", "0EI235959", "media advisory of 9 characters (at least 10 needed): unparseable"))
    c.append(("d", "SA", "1EH095333", "media advisory version 1: unparseable"))
    c.append(("d", "SA", "0EQ095333", "media advisory with an unknown link: unparseable"))
    c.append(("d", "H1", A.ohma({"version": "1.0", "message": "{\"fault\":\"ENG 2 BLEED\"}"}), "OHMA single message"))
    c.append(("u", "H1", "/O2." + A.ohma({"version": "1.0", "message": "UPLINK REQUEST"}), "OHMA uplink with /xx. prefix"))
    c.append(("d", "H1", "/RTNBOCR." + A.ohma({"version": "1.0", "convo_id": "c1", "msg_seq": 2, "msg_total": 2, "message": "SECOND"}), "OHMA fragment 2 of 2 (decoded alone: not complete)"))
    c.append(("d", "H1", "OHMA" + "QUJD", "OHMA prefix with base64 that is not zlib: error"))
    return c


def real(paths):
    out = []
    seen = set()
    for p in paths:
        for line in open(p):
            h = json.loads(line)["hfdl"]
            a = h.get("lpdu", {}).get("hfnpdu", {}).get("acars")
            if not a or not any(k in a for k in ("arinc622", "miam", "media-adv", "ohma")):
                continue
            text = a.get("msg_text", "")
            d = "u" if h["lpdu"]["src"]["type"] == "Ground station" else "d"
            label = a["label"]
            kind = next(k for k in ("arinc622", "miam", "media-adv", "ohma") if k in a)
            if (kind == "media-adv" and kind in seen) or (label, text) in seen:
                continue
            seen.add(kind)
            seen.add((label, text))
            out.append((d, label, text, f"real: {kind} from {a.get('reg', '').strip('.')}"))
    return out


def reference(msgs):
    """Run decode_acars_apps once per message in one container."""
    script = "\n".join(
        "LA_JSON=1 decode_acars_apps %s %s %s 2>/dev/null | tail -n +2; echo '<<END>>'" % (
            d, label, "'" + text.replace("'", "'\\''") + "'") for d, label, text, _ in msgs)
    out = subprocess.run(["docker", "run", "--rm", "-i", "hfdl-ref", "bash"], input=script,
                         capture_output=True, text=True, check=True).stdout
    results = []
    for chunk in out.split("<<END>>\n")[:len(msgs)]:
        chunk = chunk.strip()
        results.append(json.loads(chunk) if chunk.startswith("{") else None)
    return results


def main():
    msgs = DOC + real(sys.argv[1:]) + synthetic()
    exp = reference(msgs)
    cases = []
    for i, ((d, label, text, desc), e) in enumerate(zip(msgs, exp)):
        src = "libacars-doc" if i < len(DOC) else ("real-recording" if desc.startswith("real") else "synthetic")
        cases.append({"id": f"app-{i:02d}", "source": src, "description": desc,
                      "input": {"direction": "uplink" if d == "u" else "downlink", "label": label, "text": text},
                      "expected": {"decoded": e}, "req": ["PAR-05"]})
    suite = {"suite": "parse-apps", "normative": True,
             "description": "An ACARS message's direction, label and text (after reassembly; the sublabel and MFI still in it) -> the application decoded (spec/03-domain/acars.md §4, applications.md), in the vocabulary of libacars' JSON output (F-H19). `decoded: null`: no application recognises the text. Each text is decoded alone, without reassembly (that is `parse/sequence.json` and `parse/acars.json`), so reassembly statuses are not compared here.",
             "compare": {"method": "every key of expected present with an equal value; keys not in expected ignored; non_normative_keys not compared",
                         "non_normative_keys": ["descr", "name", "msg_type", "reasm_status"], "float_abs_tolerance": 1e-5},
             "cases": cases}
    (SEED / "conformance/parse/apps.json").write_text(json.dumps(suite, indent=1) + "\n")
    print(len(cases), "cases;", sum(1 for c in cases if c["expected"]["decoded"] is None), "not decoded")


if __name__ == "__main__":
    main()
