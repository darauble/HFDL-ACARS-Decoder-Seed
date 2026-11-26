#!/usr/bin/env python3
"""Builds the support suites from the seed's own rules (a small Python
rendering of spec/04-algorithms/03-parser.md §3.4, §3.6 and 04-support.md):
parse/classify.json, alerts/alerts.json, presentation/search_terms.json,
presentation/search.json, aircraft/aircraft.json, config/merge.json,
ndjson/write.json, ndjson/read.json, time/center.json; and copies the DSC
seed's shared suites (F-H14).

    python3 tools/make_support_vectors.py
"""
import csv
import json
import re
import shutil
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent
DSC = SEED.parent / "DSC-Decoder-Seed/conformance"
C = SEED / "conformance"
GS = {int(r["gs_id"]): r for r in csv.DictReader(open(SEED / "spec/03-domain/ground-stations.csv"))}

EMERGENCY_KW = ["MAYDAY", "PAN PAN", "EMERGENCY", "SQUAWK 7700", "SQUAWK 7600", "SQUAWK 7500", "HIJACK"]
CAUTION_KW = ["FIRE", "SMOKE", "ENG FAIL", "ENGINE FAIL", "ENG SHUTDOWN", "ENGINE SHUTDOWN", "DIVERT", "DIVERSION",
              "MEDICAL", "BOMB", "DEPRESSURIZATION", "DECOMPRESSION", "FUEL LEAK", "LOW FUEL"]
LINK_CLASSES = {"squitter", "logon", "logon_confirm", "logon_resume", "logoff", "logon_denied", "systable",
                "systable_req", "perf", "freq", "echo", "media"}
LPDU_CLASS = {0x8F: "logon", 0xBF: "logon", 0x4F: "logon_resume", 0x9F: "logon_confirm", 0x5F: "logon_confirm",
              0x3F: "logoff", 0x2F: "logon_denied"}
HFNPDU_CLASS = {0xD0: "systable", 0xD1: "perf", 0xD5: "freq", 0xDE: "echo", 0xD2: "systable_req"}


# ── the rules ──────────────────────────────────────────────────────────────

def acars_of(m):
    return m.get("lpdu", {}).get("hfnpdu", {}).get("acars")


def texts(m):
    """Texts searched for keywords (03-parser.md §3.6)."""
    out = []
    a = acars_of(m)
    if a:
        if a.get("msg_text"):
            out.append(a["msg_text"])
        for app in ("miam", "ohma"):
            if app in a:
                out += [v for v in walk_strings(a[app]) if len(v) > 3]
        cp = a.get("arinc622", {}).get("cpdlc")
        if cp:
            out += [v for k, v in walk_items(cp) if isinstance(v, str) and k not in ("choice", "choice_label")]
    return out


def walk_items(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, v
            yield from walk_items(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_items(v)


def walk_strings(o):
    return [v for _, v in walk_items(o) if isinstance(v, str)]


def keyword_hits(m, words):
    hits = []
    for kw in words:
        pat = r"(?<![A-Za-z0-9])" + r"\s+".join(re.escape(w) for w in kw.split()) + r"(?![A-Za-z0-9])"
        if any(re.search(pat, t, re.IGNORECASE) for t in texts(m)):
            hits.append(kw)
    return hits


def cpdlc_choices(m):
    cp = (acars_of(m) or {}).get("arinc622", {}).get("cpdlc", {})
    return [v for k, v in walk_items(cp) if k == "choice"]


def classify(m):
    if "spdu" in m:
        cls = "squitter"
    else:
        lp = m["lpdu"]
        a = acars_of(m)
        if a:
            ar = a.get("arinc622")
            if ar and "cpdlc" in ar:
                cls = "cpdlc"
            elif ar and "adsc" in ar:
                cls = "adsc"
            elif "miam" in a:
                cls = "miam"
            elif "media-adv" in a:
                cls = "media"
            elif "ohma" in a:
                cls = "ohma"
            else:
                cls = "acars"
        elif lp["type"]["id"] in LPDU_CLASS:
            cls = LPDU_CLASS[lp["type"]["id"]]
        elif lp["type"]["id"] in (0x0D, 0x1D) and lp.get("hfnpdu", {}).get("type", {}).get("id") in HFNPDU_CLASS:
            cls = HFNPDU_CLASS[lp["hfnpdu"]["type"]["id"]]
        else:
            cls = "other"
    down = "lpdu" in m and m["lpdu"]["src"]["type"] == "Aircraft"
    emerg = keyword_hits(m, EMERGENCY_KW)
    caution = keyword_hits(m, CAUTION_KW)
    a = acars_of(m) or {}
    tags = [list(t)[0] for t in a.get("arinc622", {}).get("adsc", {}).get("tags", [])]
    if (down and any(c in ("dM55NULL", "dM56NULL") for c in cpdlc_choices(m))) or (down and "emerg_basic_report" in tags) or emerg:
        sev = "emergency"
    elif caution:
        sev = "caution"
    elif cls in LINK_CLASSES or (cls == "acars" and a.get("label") in ("_d", "Q0") and not a.get("msg_text")):
        sev = "link"
    else:
        sev = "routine"
    return cls, sev, emerg + caution


def search_terms(m, ctx):
    t = [str(ctx["freq_khz"])]
    down = "lpdu" in m and m["lpdu"]["src"]["type"] == "Aircraft"
    t.append("downlink" if down else "uplink")
    cls, sev, kws = classify(m)
    t.append(cls)
    if sev in ("emergency", "caution"):
        t.append(sev)
    t += kws
    node = m.get("lpdu") or m.get("spdu")
    gs = node["src"] if node["src"]["type"] == "Ground station" else node.get("dst", {})
    if gs.get("id") is not None:
        t.append(str(gs["id"]))
        if gs["id"] in GS:
            t.append(GS[gs["id"]]["name"])
    ac = node["src"] if node["src"]["type"] == "Aircraft" else node.get("dst", {})
    if ac and ac.get("type") == "Aircraft":
        t.append(str(ac["id"]))
        if "ac_info" in ac:
            t.append(ac["ac_info"]["icao"])
    if "ac_info" in node:
        t.append(node["ac_info"]["icao"])
    a = acars_of(m)
    if a:
        if a.get("reg"):
            t.append(a["reg"].strip("."))
        if a.get("flight"):
            t.append(a["flight"].strip())
        t.append(a["label"])
        if a.get("sublabel"):
            t.append(a["label"] + "/" + a["sublabel"])
        if a.get("mfi"):
            t.append(a["mfi"])
        if a.get("msg_num"):
            t.append(a["msg_num"] + a.get("msg_num_seq", ""))
        if a.get("msg_text"):
            t.append(a["msg_text"])
        names = {"cpdlc": "cpdlc", "adsc": "ads-c", "miam": "miam", "media": "media advisory", "ohma": "ohma"}
        if cls in names:
            t.append(names[cls])
        for k, v in walk_items(a.get("arinc622", {}).get("cpdlc", {})):
            if k == "choice_label":
                t.append(v)
    hf = (m.get("lpdu") or {}).get("hfnpdu", {})
    for k in ("flight_id",):
        if hf.get(k):
            t.append(hf[k].strip())
    if ctx.get("file"):
        t.append(ctx["file"])
    return t


def matches(query, terms):
    low = [x.lower() for x in terms]
    return all(any(w.lower() in x for x in low) for w in query.split())


def alert(m, settings, recent, now):
    cls, sev, _ = classify(m)
    a = acars_of(m) or {}
    if sev == "emergency":
        kind = "emergency"
    elif sev == "caution" and settings["alert_on_caution"]:
        kind = "caution"
    elif settings["watch_alerts"] and watched(m, settings["watch"]):
        kind = "watch"
    else:
        return None
    key = (a.get("reg"), a.get("label"), a.get("msg_num")) if a else (icao_of(m) or (a.get("reg") or ""), kind)
    key = json.dumps(key)
    if key in recent and now - recent[key] < 1800:
        return None
    recent[key] = now
    return kind


def icao_of(m):
    node = m.get("lpdu", {})
    if "ac_info" in node:
        return node["ac_info"]["icao"]
    for side in ("src", "dst"):
        s = node.get(side, {})
        if s.get("type") == "Aircraft" and "ac_info" in s:
            return s["ac_info"]["icao"]
    return None


def watched(m, watch):
    a = acars_of(m) or {}
    ids = {x for x in (icao_of(m), (a.get("reg") or "").strip("."), (a.get("flight") or "").strip(),
                       (m.get("lpdu", {}).get("hfnpdu", {}).get("flight_id") or "").strip()) if x}
    return any(w.strip().upper() in {i.upper() for i in ids} for w in watch)


# ── suites ─────────────────────────────────────────────────────────────────

def load_messages():
    seq = json.load(open(C / "parse/sequence.json"))
    out = []
    for case in seq["cases"]:
        frames = case["input"]["frames"]
        for i, msg in enumerate(case["expected"]["messages"]):
            f = frames[msg["frame"]]
            out.append((f"{case['id']}#{i}", {k: v for k, v in msg.items() if k != "frame"}, f["freq_khz"], f["t"]))
    return out


def pick(msgs):
    """A varied subset: the first of each (class, severity, label)."""
    seen, out = set(), []
    for mid, m, f, t in msgs:
        cls, sev, _ = classify(m)
        a = acars_of(m) or {}
        k = (cls, sev, a.get("label"), m.get("lpdu", {}).get("type", {}).get("id"))
        if k not in seen:
            seen.add(k)
            out.append((mid, m, f, t))
    return out


def synth_messages():
    """Synthetic messages for keywords and emergencies, wrapping application results."""
    apps = {c["description"]: c for c in json.load(open(C / "parse/apps.json"))["cases"]}

    def wrap(cid, label, text, decoded, down=True, reg=".RA73824", flight="U62905"):
        acars = {"err": False, "crc_ok": True, "more": False, "reassembly": "skipped", "reg": reg, "mode": "2",
                 "label": label, "blk_id": "4" if down else "A", "ack": "!", "msg_text": text}
        if down:
            acars["flight"] = flight
            acars["msg_num"] = "C00"
            acars["msg_num_seq"] = "A"
        if decoded:
            acars.update(decoded)
        src = {"type": "Aircraft", "id": 23, "ac_info": {"icao": "152060"}} if down else {"type": "Ground station", "id": 7}
        dst = {"type": "Ground station", "id": 7} if down else {"type": "Aircraft", "id": 23, "ac_info": {"icao": "152060"}}
        return (cid, {"lpdu": {"err": False, "src": src, "dst": dst, "type": {"id": 29, "name": "Unnumbered ack'ed data"},
                               "hfnpdu": {"err": False, "type": {"id": 255, "name": "Enveloped data"}, "acars": acars}}}, 8942, 100.0)
    out = [wrap("fire-loop", "H1", "MPF/DBN /ANRA73824/FISVR2903 /DM221012063700/DAUSSS/DSUCFO/WN22101206370026000002ENG 1 FIRE LOOP B FAULT  (3)", None),
           wrap("firewall-no-match", "H1", "CHECK FIREWALL SEAL", None),
           wrap("mayday-text", "5Z", "MAYDAY MAYDAY ENG 2 FAILURE", None),
           wrap("pan-pan-spaces", "5Z", "PAN   PAN MEDICAL", None),
           wrap("smoke-lowercase", "H1", "smoke in cabin aft", None),
           wrap("uplink-divert", "C1", "PLEASE DIVERT TO EINN", None, down=False),
           wrap("plain-text", "H1", "REQPOS037B", None),
           wrap("empty-ack", "_d", "", None, down=False)]
    for desc, cid in (("CPDLC downlink: MAYDAY MAYDAY MAYDAY, fuel and souls on board", "cpdlc-mayday"),
                      ("CPDLC downlink: PAN PAN PAN, descending to FL100", "cpdlc-panpan"),
                      ("CPDLC downlink free text", "cpdlc-free-text-medical"),
                      ("ADS-C EMERGENCY basic report (tag 9), meteo", "adsc-emergency"),
                      ("CPDLC uplink: CLIMB TO AND MAINTAIN FL350", "cpdlc-uplink-climb")):
        c = apps[desc]
        down = c["input"]["direction"] == "downlink"
        out.append(wrap(cid, c["input"]["label"], c["input"]["text"], c["expected"]["decoded"], down=down))
    return out


def classify_suite(msgs):
    cases = []
    for mid, m, f, t in msgs:
        cls, sev, kw = classify(m)
        cases.append({"id": mid, "source": "real-recording" if "#" in mid else "synthetic", "input": {"message": m},
                      "expected": {"class": cls, "severity": sev, "keywords": kw}, "req": ["PAR-06", "ALR-06"]})
    return {"suite": "parse-classify", "normative": True,
            "description": "A message (a tree as in parse/sequence.json) -> its class, severity and matched keywords with the default keyword lists (03-parser.md §3.4, §3.6).",
            "compare": {"method": "exact; keywords as a list in the order of the default lists (emergency first)"}, "cases": cases}


def alerts_suite(msgs):
    by = {mid: m for mid, m, f, t in msgs}
    on = {"alert_on_caution": True, "watch_alerts": True, "watch": []}
    cases = []
    for mid, m, f, t in msgs:
        recent = {}
        cases.append({"id": mid, "source": "synthetic" if "#" not in mid else "real-recording",
                      "input": {"messages": [{"message": m, "t": 0}], "settings": on},
                      "expected": {"alerts": [alert(m, on, recent, 0)]}, "req": ["ALR-01"]})
    off = dict(on, alert_on_caution=False)
    recent = {}
    cases.append({"id": "caution-off", "source": "synthetic", "input": {"messages": [{"message": by["fire-loop"], "t": 0}], "settings": off},
                  "expected": {"alerts": [alert(by["fire-loop"], off, recent, 0)]}, "req": ["ALR-01"]})
    seqm = [(by["fire-loop"], 0), (by["fire-loop"], 600), (by["fire-loop"], 2400)]
    recent = {}
    cases.append({"id": "once-per-message-30-min", "source": "synthetic",
                  "description": "the same ACARS message key three times: alert, none (10 min later), alert (40 min later)",
                  "input": {"messages": [{"message": m, "t": tt} for m, tt in seqm], "settings": on},
                  "expected": {"alerts": [alert(m, on, recent, tt) for m, tt in seqm]}, "req": ["ALR-01"]})
    w = dict(on, watch=["ra73824"])
    recent = {}
    cases.append({"id": "watched-registration", "source": "synthetic", "input": {"messages": [{"message": by["plain-text"], "t": 0}], "settings": w},
                  "expected": {"alerts": [alert(by["plain-text"], w, recent, 0)]}, "req": ["ALR-01", "AC-04"]})
    return {"suite": "alerts", "normative": True,
            "description": "Messages in order with their times (s) and the settings -> the alert kind each raises (04-support.md §4.7), or null.",
            "compare": {"method": "exact"}, "cases": cases}


def terms_suites(msgs):
    cases, all_msgs = [], []
    for mid, m, f, t in msgs:
        ctx = {"freq_khz": f}
        cases.append({"id": mid, "input": {"message": m, "context": ctx}, "expected": {"terms": search_terms(m, ctx)},
                      "req": ["VIEW-06"]})
        all_msgs.append({"id": mid, "message": m, "context": ctx})
    st = {"suite": "search-terms", "normative": True,
          "description": "A message and its context -> its search terms (spec/07-ui/search-terms.md) without enrichment.",
          "compare": {"method": "every expected term must be among the implementation's terms (extra terms allowed)"}, "cases": cases}
    queries = ["", "fire", "FIRE loop", "shannon", "8977", "uplink", "cpdlc", "ads-c", "152060", "ra73824", "h1/cf",
               "emergency", "mayday", "nothing-matches-this", "media advisory", "logon"]
    qc = []
    for q in queries:
        hit = [x["id"] for x in all_msgs if matches(q, search_terms(x["message"], x["context"]))]
        qc.append({"id": "q-" + (q.replace(" ", "_") or "empty"), "input": {"query": q}, "expected": {"matching_ids": hit},
                   "req": ["VIEW-06"]})
    flt = []
    for name, fn in (("hide-link", lambda m: classify(m)[1] != "link"),
                     ("alerts-only", lambda m: classify(m)[1] in ("emergency", "caution"))):
        flt.append({"id": "filter-" + name, "input": {"query": "", "filter": name},
                    "expected": {"matching_ids": [x["id"] for x in all_msgs if fn(x["message"])]}, "req": ["VIEW-07"]})
    sr = {"suite": "search", "normative": True,
          "description": "Queries and filters over `messages` -> the matching ids, in message order (04-support.md §4.6).",
          "compare": {"method": "exact list"}, "messages": all_msgs, "cases": qc + flt}
    return st, sr


def aircraft_suite(all_msgs):
    """Aircraft view from a real recording's messages (04-support.md §4.9), no enrichment."""
    cases = []
    for rec in sorted({mid.split("#")[0] for mid, _, _, _ in all_msgs}):
        ac = {}
        alias = {}
        ms = [(mid, m, f, t) for mid, m, f, t in all_msgs if mid.startswith(rec)]
        for mid, m, f, t in ms:
            if "spdu" in m:
                continue
            a = acars_of(m) or {}
            icao = icao_of(m)
            reg = (a.get("reg") or "").strip(".") or None
            down = m["lpdu"]["src"]["type"] == "Aircraft"
            key = icao or (alias.get(reg) if reg else None) or reg
            if not key:
                continue
            if icao and reg:
                if reg in ac and reg != icao:
                    old = ac.pop(reg)
                    ac.setdefault(icao, old)
                alias[reg] = icao
            e = ac.setdefault(key, {"icao": None, "registration": None, "flight": None, "messages": 0,
                                    "first_t": t, "last_t": t, "last_freq_khz": f, "position": None})
            if icao:
                e["icao"] = icao
            if reg:
                e["registration"] = reg
            fl = (a.get("flight") or "").strip() or (m["lpdu"].get("hfnpdu", {}).get("flight_id") or "").strip() or None
            if fl:
                e["flight"] = fl
            e["messages"] += 1
            e["last_t"], e["last_freq_khz"] = t, f
            hf = m["lpdu"].get("hfnpdu", {})
            pos = hf.get("pos")
            if down and pos and abs(pos["lat"]) <= 90 and abs(pos["lon"]) <= 180:
                e["position"] = {"lat": pos["lat"], "lon": pos["lon"], "t": t}
        cases.append({"id": rec, "source": "real-recording",
                      "description": "every message of parse/sequence.json's case of the same id, in order",
                      "input": {"sequence_case": rec},
                      "expected": {"aircraft": sorted(ac.values(), key=lambda x: (x["icao"] or "", x["registration"] or ""))},
                      "req": ["AC-01"]})
    return {"suite": "aircraft", "normative": True,
            "description": "The messages of a parse/sequence.json case -> the aircraft view (04-support.md §4.9): identity, flight, message count, first/last time, last frequency, last valid reported position (performance or frequency data of a downlink).",
            "compare": {"method": "as a set keyed by (icao, registration); floats 1e-6"}, "cases": cases}


def merge(base, mine, disk):
    r = dict(mine)
    for k in set(base) | set(mine) | set(disk):
        if mine.get(k) == base.get(k):
            if k in disk:
                r[k] = disk[k]
            else:
                r.pop(k, None)
    return r


def config_suite():
    base = {"location": {"lat": 54.84, "lon": 23.83}, "hfdl": {
        "message_dir": "/home/u/.local/share/app/hfdl", "alert_on_caution": True, "watch": ["RA73824"],
        "keywords_caution": ["FIRE", "SMOKE"], "lookup_hexdb": False,
        "sources": [{"label": "RSPduo", "kind": "iq", "center_khz": 8902.5, "rate": 250000}]}}

    def mut(o, **k):
        o = json.loads(json.dumps(o))
        for path, v in k.items():
            d = o
            parts = path.split("__")
            for p in parts[:-1]:
                d = d[p]
            if v is None:
                d.pop(parts[-1], None)
            else:
                d[parts[-1]] = v
        return o

    def m3(b, mi, di):
        out = {"location": merge({"x": b.get("location")}, {"x": mi.get("location")}, {"x": di.get("location")}).get("x")}
        out = {k: v for k, v in out.items() if v is not None}
        out["hfdl"] = merge(b["hfdl"], mi["hfdl"], di["hfdl"])
        return out
    cases = []
    for cid, desc, mi, di in (
        ("nothing-changed", "no changes", base, base),
        ("mine-watch-theirs-keywords", "I changed the watch list, the other copy the caution keywords: both kept",
         mut(base, hfdl__watch=["RA73824", "G-VZIG"]), mut(base, hfdl__keywords_caution=["FIRE", "SMOKE", "BLEED"])),
        ("both-watch-mine-wins", "both changed the watch list (one unit): mine wins whole",
         mut(base, hfdl__watch=["G-VZIG"]), mut(base, hfdl__watch=["RA73824", "D-ABYT"])),
        ("location-unit", "I changed only the latitude, the other copy the longitude: my location whole",
         mut(base, location={"lat": 55.0, "lon": 23.83}), mut(base, location={"lat": 54.84, "lon": 24.0})),
        ("their-lookup", "the other copy switched hexdb on: kept", base, mut(base, hfdl__lookup_hexdb=True)),
        ("sources-unit", "both changed the sources list: mine whole",
         mut(base, hfdl__sources=[{"label": "RSPduo", "kind": "iq", "center_khz": 11287.0, "rate": 250000}]),
         mut(base, hfdl__sources=[])),
    ):
        cases.append({"id": cid, "description": desc, "input": {"base": base, "mine": mi, "disk": di},
                      "expected": {"saved": m3(base, mi, di)}, "req": ["CFG-02"]})
    return {"suite": "config-merge", "normative": True,
            "description": "Three-way merge of the settings (04-support.md §4.8): per setting (lists and the location are units), keep mine where it differs from base, else take disk.",
            "compare": {"method": "exact"}, "cases": cases}


def center_suite():
    cases = []
    for cid, name, meta, exp in (
        ("shellsdr-hz", "20261125-095421_baseband_8902500Hz-HFDL.wav", None, 8902500),
        ("khz-decimal", "rec_8902.5kHz_2026.wav", None, 8902500),
        ("mhz", "hfdl 8.9025MHz.wav", None, 8902500),
        ("lowercase-unit", "x_10058500hz.wav", None, 10058500),
        ("first-match", "a_5587500Hz_copy_of_8902500Hz.wav", None, 5587500),
        ("none", "recording.wav", None, None),
        ("metadata-wins", "20261125-095421_baseband_8902500Hz-HFDL.wav",
         "format_version=2\nrec_type=baseband\ncenter_freq=8902000\nstart_time=2026-11-25T09:54:21Z\ntimezone=UTC\n", 8902000),
    ):
        exp_time = None
        if meta:
            exp_time = {"utc_iso": "2026-11-25T09:54:21Z"}
        cases.append({"id": cid, "input": {"file_name": name, "riff_comment": meta},
                      "expected": {"center_hz": exp, **({"start": exp_time} if exp_time else {})}, "req": ["DEC-07", "TIM-02"]})
    return {"suite": "file-center", "normative": True,
            "description": "An I/Q recording's center frequency (and, from metadata, its start) from its file name and its RIFF comment (04-support.md §4.1).",
            "compare": {"method": "exact; null: none found"}, "cases": cases}


def ndjson_suites(msgs):
    w, r = [], []
    for mid, m, f, t in msgs[:6]:
        node = m.get("lpdu") or m.get("spdu")
        cls, sev, kw = classify(m)
        rec = {"v": 1, "kind": "lpdu" if "lpdu" in m else "squitter", "utc": "2026-11-25T09:58:09Z", "off": "+00:00",
               "tsrc": "filename", "freq": f, "class": cls, "sev": sev}
        w.append({"id": mid, "input": {"message": m, "utc_epoch": 1795600689, "utc_offset": 0, "time_source": "filename", "freq_khz": f},
                  "expected": {"record_contains": rec}, "req": ["STO-02", "TIM-04"]})
    good = {"v": 1, "kind": "squitter", "utc": "2026-11-25T09:58:09Z", "off": "+00:00", "tsrc": "filename", "freq": 8942,
            "class": "squitter", "sev": "link", "pdu": "00" * 66}
    for cid, line, ok in (("valid", json.dumps(good), True),
                          ("no-pdu", json.dumps({k: v for k, v in good.items() if k != "pdu"}), False),
                          ("odd-hex", json.dumps(dict(good, pdu="abc")), False),
                          ("uppercase-hex", json.dumps(dict(good, pdu="AB" * 66)), False),
                          ("no-kind", json.dumps({k: v for k, v in good.items() if k != "kind"}), False),
                          ("not-json", "{\"v\":1,", False), ("array", "[1,2]", False),
                          ("unknown-keys-ignored", json.dumps(dict(good, extra={"a": 1})), True),
                          ("wrong-type-tsrc", json.dumps(dict(good, tsrc=5)), True)):
        r.append({"id": cid, "input": {"line": line}, "expected": {"accepted": ok}, "req": ["STO-04", "STO-05"]})
    return ({"suite": "ndjson-write", "normative": True, "description": "A message -> its day-file record; the listed keys and values must be in the written object.", "compare": {"method": "subset"}, "cases": w},
            {"suite": "ndjson-read", "normative": True, "description": "One day-file line -> accepted or rejected (spec/05-data/README.md).", "compare": {"method": "exact"}, "cases": r})


def main():
    for d in ("time", "geo", "ndjson", "alerts", "presentation", "config", "aircraft"):
        (C / d).mkdir(parents=True, exist_ok=True)
    for f in ("time/file_name.json", "time/iso8601.json", "geo/distance.json", "geo/parse_location.json", "ndjson/day_file.json"):
        shutil.copy(DSC / f, C / f)
    real = load_messages()
    msgs = pick(real) + synth_messages()
    (C / "parse/classify.json").write_text(json.dumps(classify_suite(msgs), indent=1) + "\n")
    (C / "alerts/alerts.json").write_text(json.dumps(alerts_suite(msgs), indent=1) + "\n")
    st, sr = terms_suites(msgs)
    (C / "presentation/search_terms.json").write_text(json.dumps(st, indent=1) + "\n")
    (C / "presentation/search.json").write_text(json.dumps(sr, indent=1) + "\n")
    (C / "aircraft/aircraft.json").write_text(json.dumps(aircraft_suite(real), indent=1) + "\n")
    (C / "config/merge.json").write_text(json.dumps(config_suite(), indent=1) + "\n")
    (C / "time/center.json").write_text(json.dumps(center_suite(), indent=1) + "\n")
    w, r = ndjson_suites(msgs)
    (C / "ndjson/write.json").write_text(json.dumps(w, indent=1) + "\n")
    (C / "ndjson/read.json").write_text(json.dumps(r, indent=1) + "\n")
    print(len(msgs), "messages in the classify/alerts/search suites")
    for mid, m, f, t in msgs:
        print(f"  {mid:45s} {classify(m)}")


if __name__ == "__main__":
    main()
