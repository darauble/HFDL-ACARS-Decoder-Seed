#!/usr/bin/env python3
"""Generates shellsdr-workarea.html: a mockup of the HFDL view in ShellSDR's
Work Area (terminal cells, ShellSDR's Candy theme). Informative.

    python3 shellsdr_workarea.py > shellsdr-workarea.html
"""
import html
import random

W, H = 210, 46          # terminal cells
LEFT, CENTER = 34, 112  # column widths
RIGHT = W - LEFT - CENTER

GREEN, RED, CYAN, WHITE, DIM, YEL, ORG, BG_SEL, BG_KEY = (
    "#7ec97e", "#e06c6c", "#7fd6e0", "#e8e8e8", "#8a8a8a", "#f2c94c", "#ffb347", "#a8a8a8", "#e8b84a")

grid = [[(" ", WHITE, None) for _ in range(W)] for _ in range(H)]


def put(r, c, text, fg=WHITE, bg=None, maxw=None):
    if maxw is not None:
        text = text[:maxw]
    for i, ch in enumerate(text):
        if 0 <= c + i < W and 0 <= r < H:
            grid[r][c + i] = (ch, fg, bg)


def box(r, c, h, w, title="", fg=GREEN, tfg=None):
    put(r, c, "┌" + "─" * (w - 2) + "┐", fg)
    for i in range(1, h - 1):
        put(r + i, c, "│", fg)
        put(r + i, c + w - 1, "│", fg)
    put(r + h - 1, c, "└" + "─" * (w - 2) + "┘", fg)
    if title:
        put(r, c + 1, title, tfg or fg)


# ── global controls
box(0, 0, 4, W, "Global Controls - ShellSDR v0.4.5")
put(1, 1, "[Stop]  Vol[########]  [ ] Mute  [Spectrum:ON] [Waterfall:ON] [Split]")
put(2, 1, "Center: 0 008 902 500 Hz   [Center]  Theme:[Candy]  Panel:[◂ 34 ▸]  [?] Help")

# ── left: bookmarks and schedule
box(4, 0, 22, LEFT, "Bookmarks  List: HFDL")
rows = ["[New] [Rename] [Del] [Hide]", "[Add] [Edit] [Remove] [Tune]", "Sort: Frequency", "Find(/):",
        "  5587.5 HFDL 5.6 MHz", "  6623.5 HFDL 6.6 MHz", "› 8902.5 HFDL 8.9 MHz",
        " 10058.5 HFDL 10 MHz", " 11287.0 HFDL 11.3 MHz", " 13309.0 HFDL 13.3 MHz",
        " 17944.5 HFDL 17.9 MHz", " 21964.0 HFDL 22 MHz", "", "HFDL 500 kS/s  15 channels",
        "Shannon, Reykjavik, Krasnoyarsk,", "Al Muharraq, Canarias, …"]
for i, t in enumerate(rows):
    sel = t.startswith("›")
    put(5 + i, 1, t.ljust(LEFT - 2), WHITE, BG_SEL if sel else None)
box(26, 0, 19, LEFT, "[-] Schedule", RED)
for i, t in enumerate(["Next 19:00 UTC HFDL 8.9 MHz", "Scheduler: [On]", "Auto start/stop: [x]",
                       "[Add] [Edit] [Remove] [Off]", " x 0600-0800 R  HFDL 13.3 MHz", " x 1100-1500 R  HFDL 11.3 MHz",
                       "● 1700-2300 R  HFDL 8.9 MHz", " x 2300-0500 R  HFDL 6.6 MHz"]):
    put(27 + i, 1, t, YEL if t.startswith("●") else WHITE)

# ── center: the HFDL view
c0 = LEFT
box(4, c0, 41, CENTER, "Master: HFDL")
put(5, c0 + 2, "View  Filter  Aircraft  Tools  Help")
put(5, c0 + CENTER - 9, "F9 menu")
put(6, c0 + 2, " LIVE* ", WHITE, "#c0392b")
put(6, c0 + 10, "msgs: 1412   channels: 15 (2 decoding)   aircraft: 63   alerts: 1   [x] hide link  [x] hide joined")
box(7, c0 + 1, 6, CENTER - 2, "")
put(8, c0 + 2, "Channel  GS                 State      Frames  Err  Last      Channel  GS                 State     Frames")
chans = [("8942", "7 Shannon", "decoding", "214", "31", "19:30:11"), ("8977", "3 Reykjavik", "activity", "167", "22", "19:29:02"),
         ("8886", "14 Krasnoyarsk", "silent", "41", "9", "19:12:40"), ("8885", "15 Al Muharraq", "silent", "18", "6", ""),
         ("8948", "17 Canarias", "decoding", "52", "11", "19:29:40"), ("8843", "7 Shannon", "silent", "6", "2", "")]
for i, (f, g, s, fr, er, la) in enumerate(chans):
    r, cc = 9 + i % 3, c0 + 2 + (i // 3) * 61
    put(r, cc, f"{f:<9}{g:<19}", WHITE)
    put(r, cc + 28, f"{s:<10}", YEL if s == "decoding" else (WHITE if s == "activity" else DIM))
    put(r, cc + 38, f"{fr:>6}" + (f"  {er:>3}  {la}" if i < 3 else ""))
put(12, c0 + 3, "… 9 more channels, silent", DIM)

put(13, c0 + 2, "[Messages]  Aircraft (63)  Ground stations (16)", CYAN)
lw = 70
box(14, c0 + 1, 28, lw, "Messages: 1412 of 1412  Pages: 118 of 118  File: 2022-10-12")
box(14, c0 + 1 + lw, 28, CENTER - 2 - lw, "Message details")
put(15, c0 + 2, "TIME     S FREQ ▲ AIRCRAFT FLIGHT TYPE        SUBJECT", WHITE)
msgs = [("19:21:03", " ", "8977", "▲", "TC-JNH", "THY6TY", "ADS-C", "Basic report, Flight ID"),
        ("19:21:40", " ", "8942", "▼", "TC-JNH", "", "ADS-C", "Periodic contract 1024 s"),
        ("19:22:17", " ", "8942", "▲", "RA73752", "SU1003", "ACARS H1/DF", "A320,000430,1,1,TB000000"),
        ("19:23:05", " ", "8977", "▲", "N784AV", "AVA071", "CPDLC", "REQUEST CLIMB TO FL370"),
        ("19:23:44", " ", "8977", "▼", "N784AV", "", "CPDLC", "CLIMB TO AND MAINTAIN FL370"),
        ("19:24:19", " ", "8942", "▲", "EI-FNH", "ASL54K", "MEDIA ADV", "HF link established 19:24"),
        ("19:25:52", " ", "8886", "▲", "B-1402", "CCA931", "ACARS 5Z", "/ETA UUEE 2155"),
        ("19:26:30", " ", "8942", "▲", "G-VZIG", "VIR401", "ACARS H1", "#M1BPOSN52317W020194,TUN"),
        ("19:28:26", "C", "8942", "▲", "RA73824", "U62905", "ACARS H1/CF", "ENG 1 FIRE LOOP B FAULT"),
        ("19:29:02", "★", "8977", "▲", "D-ABYT", "DLH400", "ACARS 80", "OOOI ON 1929"),
        ("19:29:40", " ", "8948", "▲", "EC-NVN", "IBE6253", "FREQ DATA", "Position 31.82 N 22.40 W"),
        ("19:30:11", "C", "8942", "▲", "RA73824", "U62905", "ACARS H1/CF", "ENG 1 FIRE LOOP B FAULT (3)")]
for i, m in enumerate(msgs):
    t, s, f, d, a, fl, ty, su = m
    line = f"{t} {s} {f} {d} {a:<8} {fl:<6} {ty:<11} {su}"
    last = i == len(msgs) - 1
    fg = ORG if s == "C" else (YEL if s == "★" else WHITE)
    put(16 + i, c0 + 2, line.ljust(lw - 2), "#000" if last else fg, BG_KEY if last else None, maxw=lw - 2)
dc = c0 + 2 + lw
details = [("Severity", "CAUTION: keyword FIRE"), ("Type", "ACARS H1, sublabel CF"), ("Aircraft", "RA73824  ICAO 152060"),
           ("", "A320, Ural Airlines"), ("Flight", "U62905"), ("Position", "57.312 N 41.884 E"),
           ("", "[freq data 19:27:58]"), ("", "1806 km (975 NM)"), ("Route", "USSS → UUDD [hexdb]"),
           ("GS", "7 Shannon, Ireland"), ("", "2144 km, 8942 kHz"), ("ACARS", "mode 2 blk 6 msg C00C"),
           ("Reasm", "complete (3 blocks)"), ("Text", "MPF/DBN /ANRA73824/FISVR"), ("", "2903 /DM221012063700/DA"),
           ("", "USSS/DSUCFO/WN22101206370"), ("", "026000002ENG 1 FIRE LOOP"), ("", "B FAULT (3)"),
           ("UTC", "2022-10-12T16:30:11Z"), ("Signal", "600 bps S -81.8 dBFS")]
for i, (k, v) in enumerate(details):
    put(15 + i, dc, f"{k:<9}", DIM)
    put(15 + i, dc + 9, (": " if k else "  ") + v, ORG if k == "Severity" else WHITE, maxw=CENTER - lw - 14)
put(41, c0 + 2 + lw + CENTER - lw - 10, "1/3", DIM)
keys = ["1Help", "2Save", "3View", "4Watch", "5Copy", "6Detail", "7Search", "8Follow", "9Menu"]
kw = (CENTER - 2) // len(keys)
for i, k in enumerate(keys):
    put(42, c0 + 1 + i * kw, k[0], WHITE)
    put(42, c0 + 2 + i * kw, k[1:].ljust(kw - 1), "#000", BG_KEY)
put(43, c0 + 2, " CAUTION 19:28:26 RA73824 U62905: ENG 1 FIRE LOOP B FAULT   [Ack: Ctrl+K] ", "#000", ORG)

# ── right: bookmarks strip, spectrum with channel marks, waterfall
r0 = LEFT + CENTER
box(4, r0, 5, RIGHT, "Bookmarks  UTC 16:30, Local: 19:30")
put(6, r0 + 18, "HFDL 8.9 MHz", WHITE, BG_SEL)
box(9, r0, 14, RIGHT, "Spectrum  [-128..-58 dB auto]")
random.seed(3)
span = (8652.5, 9152.5)
chs = [8825, 8834, 8843, 8885, 8886, 8894, 8912, 8921, 8927, 8936, 8939, 8942, 8948, 8957, 8977]
plotw = RIGHT - 8
heights = []
for x in range(plotw):
    f = span[0] + (span[1] - span[0]) * x / plotw
    h = 1 + random.random() * 1.5
    for c in chs:
        if abs(f - (c + 1.44)) < 2.5:
            h += {8942: 7, 8977: 5, 8948: 6}.get(c, 2.5)
    heights.append(min(10, h))
put(10, r0 + 1, "-58", WHITE)
put(15, r0 + 1, "-93", WHITE)
put(20, r0 + 1, "-128", WHITE)
put(21, r0 + 1, "", WHITE)
for x, h in enumerate(heights):
    top = 20 - int(h)
    for rr in range(top, 21):
        put(rr, r0 + 6 + x, "⠒" if rr == 20 else "│", RED)
for c in chs:
    x = int((c + 1.44 - span[0]) / (span[1] - span[0]) * plotw)
    put(11, r0 + 6 + x, "▾", YEL if c in (8942, 8948) else CYAN)
put(21, r0 + 4, "8.7 MHz        8.8 MHz        8.9 MHz         9.0 MHz        9.1 MHz", WHITE)
box(23, r0, 22, RIGHT, "Waterfall")
palette = ["#1d3b5c", "#2a5c7a", "#2f7f8a", "#3f9f8a", "#7fbf6a", "#d9c94a", "#f08a3a"]
for r in range(24, 44):
    for x in range(plotw):
        f = span[0] + (span[1] - span[0]) * x / plotw
        v = random.random() * 1.2
        for c in chs:
            if abs(f - (c + 1.44)) < 2.5 and random.random() < {8942: 0.7, 8977: 0.5, 8948: 0.6}.get(c, 0.25):
                v += 3 + random.random() * 2.5
        put(r, r0 + 6 + x, " ", WHITE, palette[min(len(palette) - 1, int(v))])

put(45, 0, "ShellSDR  |  SDRplay Dev0 RSPduo 22340A6E34 - Master  |  Running  |  HFDL 15 ch  |  DSP 31%  |  REC 20221012T190000_hfdl.ndjson", WHITE)

# ── HTML
out = ['<!doctype html><html><head><meta charset="utf-8"><title>ShellSDR HFDL Work Area mockup</title>',
       '<style>body{margin:0;background:#000}pre{margin:6px;font:15px/18px "DejaVu Sans Mono",monospace;color:#e8e8e8}</style>',
       '</head><body><pre>']
for row in grid:
    line = []
    for ch, fg, bg in row:
        st = f"color:{fg}" + (f";background:{bg}" if bg else "")
        line.append(f'<span style="{st}">{html.escape(ch)}</span>')
    out.append("".join(line))
out.append("</pre></body></html>")
print("\n".join(out))
