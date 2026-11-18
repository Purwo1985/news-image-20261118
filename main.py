#!/usr/bin/env python3
"""news-image-20261118 -- one image summing up Wednesday 18 November 2026.

A pure-stdlib Python 3.13 program. It draws a 1024x1024 newspaper-style
infographic -- masthead, a world map with a numbered pin per story, six
story cards with scene banners, plus an "also making news" strip -- into
an RGB buffer, encodes it as a PNG with a hand-rolled encoder
(zlib + struct), and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output).

No network, no files read, no timestamps, no randomness: two runs write
byte-identical output.

=====================================================================
NEWS DATA -- EDIT ONLY THIS SECTION TO FREEZE THE FINAL CONTENT
=====================================================================
Everything the picture says lives in the constants below (DATE_LINE,
KICKER, SUBHEAD, STORIES, ALSO_LINE, SOURCE_LINE). To update the
content for the final freeze on the evening of 19 November 2026 (WIB):

  1. Edit ONLY the STORIES list (and ALSO_LINE if needed) in this file.
     Each story is one dict with five fields:
       "tag"   -- short section label, e.g. "ASIA - SUMMITS"
       "color" -- (R, G, B) accent colour for the card
       "icon"  -- one of: summit, quad, bridge, radar, alert, ban
       "title" -- headline, UPPERCASE, keep under ~40 characters
       "body"  -- one plain sentence, keep under ~170 characters
     The map pin for a story is placed from place names in its title
     and body (cities first, then countries), falling back to the
     region in its tag, and the "WHERE IT HAPPENED" panel lists the
     tags -- so keep the tag format "REGION - BEAT" and keep place
     names in the title/body.
  2. Keep titles and bodies in plain ASCII (letters, digits and
     . , : ; ! ? ' " - ( ) / % & + = only) -- the built-in 5x7 font
     below covers exactly that set, and the program raises an error
     on any character it cannot draw.
  3. Keep six stories. If a story must be dropped, replace it with
     the next most consequential story of 18 November 2026; do not
     leave a card empty and do not add a seventh card.
  4. Re-run:  MAKEFUN_OUTPUT_DIR=out python3 main.py
     then check the PNG (size, 1024x1024, two runs byte-identical)
     and look at the image before committing.
=====================================================================
"""

import os
import struct
import zlib

# ------------------------------------------------------------------
# NEWS DATA (see the block above for how to replace it on 19 Nov)
# ------------------------------------------------------------------

DATE_LINE = "WEDNESDAY 18 NOVEMBER 2026"
KICKER = "WORLD NEWS IN ONE IMAGE"
SUBHEAD = "Six stories from a day of summits, strikes and storms"

# Provisional content, researched on 18 Nov 2026 (morning WIB) from
# wire reports of that day. Every main story below was first reported
# on 18 November 2026; the footer strip carries items from the same
# news cycle. Final freeze: evening of 19 Nov 2026 (WIB), once the
# day has ended everywhere on Earth.
STORIES = [
    {
        "tag": "ASIA - SUMMITS",
        "color": (27, 108, 168),
        "icon": "summit",
        "title": "APEC OPENS AS TRUMP HEADS TO CHINA",
        "body": "Leaders gather in Shenzhen for the APEC summit. Trump "
                "travels on for a first-ever three-way meeting with Xi "
                "Jinping and Vladimir Putin, due on 19 November.",
    },
    {
        "tag": "ASIA-PACIFIC - SECURITY",
        "color": (14, 124, 102),
        "icon": "quad",
        "title": "QUAD ANNOUNCES NEW MARITIME PLAN",
        "body": "The US, India, Japan and Australia, meeting in Manila, "
                "unveil a new maritime exercise and joint work on AI "
                "and cybersecurity.",
    },
    {
        "tag": "EUROPE - WAR",
        "color": (169, 50, 38),
        "icon": "bridge",
        "title": "UKRAINE HITS CRIMEAN BRIDGE",
        "body": "Ukraine damaged the Crimean Bridge in a major strike, "
                "as Russia hit bridges around Kyiv, with both sides "
                "targeting crossings.",
    },
    {
        "tag": "MIDDLE EAST - CONFLICT",
        "color": (122, 62, 150),
        "icon": "radar",
        "title": "IRAN CLAIMS DRONE STRIKE ON US BASE",
        "body": "Iran's Revolutionary Guard said it hit a US military "
                "radar system at Sheikh Isa Air Base in Bahrain, its "
                "third strike on the country in five days.",
    },
    {
        "tag": "ASIA - DISASTER",
        "color": (93, 109, 126),
        "icon": "alert",
        "title": "RUSSIAN MILITARY PLANE CRASHES",
        "body": "A Russian military plane crashed in Siberia, killing "
                "19 people. Investigators are examining the wreckage "
                "to find the cause.",
    },
    {
        "tag": "EUROPE - DIPLOMACY",
        "color": (46, 125, 50),
        "icon": "ban",
        "title": "BRITAIN SANCTIONS SETTLEMENT FIRMS",
        "body": "Britain sanctioned Israeli settlement firms in a push "
                "to protect the two-state solution, targeting companies "
                "linked to West Bank settlements.",
    },
]

ALSO_LINE = ("ALSO MAKING NEWS: US loses measles-free status, health "
             "officials say - Cyclone Akvan nears India's Andhra coast, "
             "landfall due 20 Nov - Dhoni retires from the IPL and "
             "becomes CSK mentor - Mongolia's president resigns amid "
             "graft charges.")

SOURCE_LINE = "Compiled from wire reports published on 18 November 2026."

# ------------------------------------------------------------------
# 5x7 bitmap font (hand-written). Each glyph is 7 rows of 5 pixels.
# "1" is ink, "0" is empty. Covers A-Z, a-z, 0-9 and common punctuation.
# ------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "00010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11110", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
}

# ------------------------------------------------------------------
# Canvas and drawing primitives
# ------------------------------------------------------------------

W, H = 1024, 1024

PAPER = (247, 243, 236)
INK = (24, 32, 44)
BODY = (56, 62, 70)
NAVY = (13, 42, 71)
NAVY_DARK = (9, 30, 52)
GOLD = (201, 162, 60)
GOLD_LIGHT = (226, 196, 110)
MUTED_BLUE = (178, 196, 214)
CARD_BORDER = (214, 208, 196)
WHITE = (255, 255, 255)
FOOTER_MUTED = (150, 168, 186)


class Canvas:
    """A plain RGB pixel buffer with a few drawing helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def rect_border(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        """Bresenham line with a square brush of thickness t."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = t // 2
        while True:
            self.fill_rect(x0 - half, y0 - half, t, t, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, filled=False, t=1):
        """Midpoint circle; outline (thickness t) or filled disc."""
        x, y, d = 0, r, 1 - r
        pts = set()
        while x <= y:
            for sx, sy in ((x, y), (y, x), (-x, y), (-y, x),
                           (x, -y), (y, -x), (-x, -y), (-y, -x)):
                pts.add((cx + sx, cy + sy))
            if filled:
                for xx in range(cx - x, cx + x + 1):
                    self.set_px(xx, cy + y, color)
                    self.set_px(xx, cy - y, color)
                for xx in range(cx - y, cx + y + 1):
                    self.set_px(xx, cy + x, color)
                    self.set_px(xx, cy - x, color)
            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5
                y -= 1
            x += 1
        if filled:
            self.fill_rect(cx - r, cy, 2 * r + 1, 1, color)
            return
        for px, py in pts:
            self.fill_rect(px - t // 2, py - t // 2, t, t, color)

    def arc(self, cx, cy, r, a0, a1, color, t=1):
        """Arc from angle a0 to a1 (degrees, 0 = east, clockwise in y)."""
        import math
        steps = max(8, int(abs(a1 - a0) * r / 12))
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            px = round(cx + r * math.cos(a))
            py = round(cy + r * math.sin(a))
            self.fill_rect(px - t // 2, py - t // 2, t, t, color)


# ------------------------------------------------------------------
# Text: measurement, wrapping, rendering
# ------------------------------------------------------------------

def text_width(text, scale):
    """Pixel width of text at the given scale (advance 6 units/char)."""
    return len(text) * 6 * scale - scale if text else 0


def draw_text(cv, x, y, text, scale, color):
    """Draw text with its top-left corner at (x, y)."""
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            raise ValueError("character not in font: %r" % ch)
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    cv.fill_rect(x + col * scale, y + row * scale,
                                 scale, scale, color)
        x += 6 * scale
    return x


def draw_text_centered(cv, cx, y, text, scale, color):
    draw_text(cv, cx - text_width(text, scale) // 2, y, text, scale, color)


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines fitting max_width."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, scale) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


# ------------------------------------------------------------------
# World map: simplified continent outlines (lon, lat) + a small
# gazetteer so each story gets a numbered pin on the map. Pins are
# placed from place names found in the story's title/body first
# (cities, then countries), falling back to the tag's region -- so
# the freeze only has to edit STORIES and the map follows.
# ------------------------------------------------------------------

MAP_X, MAP_Y, MAP_W, MAP_H = 24, 128, 640, 184
PANEL_X, PANEL_Y, PANEL_W, PANEL_H = 676, 128, 324, 184
MAP_LAT_TOP, MAP_LAT_BOT = 75.0, -60.0

OCEAN = (176, 208, 226)
LAND = (233, 224, 192)
LAND_EDGE = (122, 112, 82)
GRID = (198, 221, 235)
MAP_LABEL = (74, 88, 102)
PIN_RING = (255, 255, 255)

CONTINENTS = [
    # North America
    [(-168, 66), (-161, 58), (-153, 58), (-146, 60), (-140, 60), (-135, 57),
     (-130, 54), (-126, 50), (-124, 46), (-124, 40), (-120, 34), (-114, 29),
     (-110, 24), (-105, 20), (-97, 16), (-93, 15), (-88, 13), (-84, 12),
     (-80, 9), (-77, 7), (-79, 9), (-81, 13), (-83, 15), (-86, 16),
     (-88, 21), (-90, 21), (-91, 19), (-96, 19), (-97, 22), (-97, 26),
     (-94, 29), (-90, 29), (-85, 30), (-82, 28), (-80, 26), (-81, 31),
     (-78, 34), (-76, 37), (-74, 40), (-70, 42), (-68, 44), (-66, 45),
     (-63, 46), (-60, 47), (-56, 48), (-60, 52), (-64, 58), (-68, 58),
     (-72, 62), (-78, 62), (-82, 66), (-88, 66), (-93, 66), (-95, 69),
     (-102, 68), (-110, 68), (-118, 69), (-126, 70), (-134, 69), (-142, 70),
     (-150, 70), (-158, 71), (-165, 68), (-168, 66)],
    # Greenland
    [(-58, 64), (-55, 60), (-49, 60), (-43, 60), (-40, 63), (-35, 66),
     (-30, 68), (-25, 70), (-22, 70), (-22, 74), (-28, 76), (-35, 76),
     (-42, 77), (-50, 76), (-55, 74), (-58, 71), (-60, 68), (-58, 64)],
    # South America
    [(-78, 7), (-76, 10), (-73, 11), (-70, 12), (-64, 10), (-61, 9),
     (-57, 6), (-52, 5), (-51, 1), (-50, -2), (-45, -3), (-40, -5),
     (-35, -8), (-37, -12), (-39, -17), (-41, -22), (-46, -24), (-49, -28),
     (-53, -33), (-58, -36), (-62, -39), (-65, -41), (-66, -45), (-68, -49),
     (-69, -52), (-71, -54), (-74, -52), (-74, -48), (-73, -42), (-73, -36),
     (-72, -30), (-70, -24), (-70, -19), (-75, -15), (-77, -12), (-79, -8),
     (-81, -5), (-81, -1), (-80, 3), (-78, 7)],
    # Europe
    [(-10, 36), (-9, 38), (-9, 43), (-4, 44), (-2, 44), (-1, 46), (-5, 48),
     (-2, 49), (0, 50), (2, 51), (4, 52), (7, 54), (8, 55), (8, 57),
     (10, 58), (7, 59), (5, 60), (5, 62), (10, 63), (13, 65), (16, 68),
     (20, 70), (25, 71), (30, 70), (32, 68), (35, 67), (40, 68), (44, 68),
     (48, 69), (52, 68), (55, 69), (58, 69), (60, 68), (66, 69), (68, 67),
     (66, 64), (62, 60), (58, 57), (55, 54), (52, 52), (48, 50), (44, 48),
     (40, 47), (36, 46), (32, 46), (28, 45), (25, 42), (23, 40), (20, 40),
     (19, 42), (16, 43), (13, 44), (9, 44), (6, 43), (3, 42), (0, 40),
     (-2, 37), (-6, 36), (-9, 37), (-10, 36)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51),
     (-3, 50), (-5, 50)],
    # Africa
    [(-17, 15), (-16, 19), (-15, 24), (-14, 28), (-11, 30), (-7, 33),
     (-5, 35), (-1, 35), (3, 37), (9, 37), (11, 34), (15, 32), (19, 31),
     (23, 32), (27, 31), (30, 31), (32, 31), (34, 28), (36, 25), (37, 22),
     (38, 20), (40, 16), (43, 12), (46, 11), (51, 11), (51, 5), (48, 0),
     (44, -4), (40, -9), (38, -15), (36, -19), (35, -23), (33, -26),
     (31, -29), (28, -33), (24, -34), (19, -35), (17, -32), (15, -27),
     (13, -21), (12, -17), (13, -12), (12, -8), (10, -4), (9, -1), (9, 4),
     (6, 4), (2, 6), (-3, 5), (-8, 5), (-12, 8), (-15, 11), (-17, 13),
     (-17, 15)],
    # Madagascar
    [(44, -16), (47, -15), (50, -16), (49, -20), (47, -24), (44, -25),
     (43, -21), (44, -16)],
    # Asia (mainland)
    [(30, 70), (35, 68), (40, 68), (44, 68), (48, 69), (52, 68), (56, 69),
     (60, 69), (64, 69), (68, 68), (70, 72), (75, 73), (80, 73), (85, 74),
     (90, 75), (95, 76), (100, 77), (105, 77), (110, 74), (115, 73),
     (120, 73), (125, 72), (130, 72), (135, 71), (140, 72), (145, 72),
     (150, 70), (155, 69), (160, 69), (162, 66), (160, 62), (158, 58),
     (156, 52), (150, 59), (142, 55), (142, 50), (140, 45), (138, 40),
     (135, 36), (130, 35), (127, 35), (126, 38), (122, 39), (120, 35),
     (122, 31), (120, 28), (118, 25), (112, 22), (110, 20), (108, 18),
     (106, 10), (105, 9), (103, 7), (101, 6), (100, 8), (98, 10), (97, 15),
     (94, 17), (92, 21), (90, 22), (88, 22), (86, 20), (83, 18), (80, 15),
     (78, 10), (77, 8), (75, 12), (73, 17), (71, 20), (68, 23), (66, 25),
     (63, 25), (60, 25), (57, 26), (56, 28), (54, 28), (52, 28), (50, 29),
     (48, 30), (46, 29), (43, 29), (41, 30), (39, 31), (37, 33), (35, 36),
     (33, 36), (30, 36), (28, 37), (27, 38), (30, 40), (32, 42), (34, 44),
     (36, 45), (38, 46), (40, 47), (42, 48), (44, 50), (46, 52), (48, 54),
     (50, 56), (52, 58), (55, 60), (58, 62), (60, 64), (62, 66), (65, 68),
     (68, 69), (66, 69), (60, 69), (55, 69), (50, 69), (45, 68), (40, 68),
     (35, 68), (30, 70)],
    # Japan (Honshu + Hokkaido)
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 37), (140, 39),
     (141, 41), (141, 44), (143, 43), (141, 40), (140, 37), (138, 35),
     (136, 33), (133, 34), (131, 32), (130, 31)],
    [(140, 42), (142, 42), (144, 43), (145, 44), (143, 45), (141, 45),
     (140, 43), (140, 42)],
    # Sumatra, Borneo, Java, New Guinea, Philippines
    [(95, 5), (98, 3), (101, 0), (104, -3), (106, -5), (104, -6), (101, -4),
     (98, 0), (95, 5)],
    [(109, 1), (111, 2), (114, 4), (117, 2), (119, -1), (117, -4),
     (114, -4), (111, -3), (109, 1)],
    [(105, -6), (108, -7), (111, -7), (114, -8), (114, -9), (111, -8),
     (108, -8), (105, -7)],
    [(131, -1), (134, -2), (137, -3), (140, -4), (143, -6), (146, -7),
     (149, -9), (147, -9), (144, -8), (141, -8), (138, -7), (135, -4),
     (132, -2), (131, -1)],
    [(120, 18), (121, 16), (122, 14), (122, 11), (124, 10), (122, 8),
     (121, 10), (120, 13), (119, 16), (120, 18)],
    # Australia + Tasmania + New Zealand
    [(113, -22), (114, -26), (115, -31), (115, -35), (118, -35), (122, -34),
     (126, -32), (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (143, -39), (147, -39), (150, -37), (152, -33), (153, -28), (153, -24),
     (150, -22), (147, -19), (145, -16), (142, -11), (141, -13), (139, -15),
     (136, -12), (135, -12), (132, -11), (130, -12), (127, -14), (124, -15),
     (122, -17), (119, -20), (116, -21), (113, -22)],
    [(145, -41), (147, -41), (148, -42), (147, -43), (146, -44), (145, -42),
     (145, -41)],
    [(167, -45), (169, -43), (171, -42), (173, -41), (175, -40), (176, -38),
     (178, -37), (176, -39), (174, -41), (172, -43), (169, -46), (167, -45)],
]

# Cities / named places first (checked before countries).
PLACES = {
    "SHEIKH ISA": (50.5, 26.2), "WEST BANK": (35.3, 32.0),
    "CRIMEAN": (34.0, 45.0), "SHENZHEN": (114.1, 22.5),
    "MANILA": (121.0, 14.6), "SIBERIA": (105.0, 62.0),
    "KYIV": (30.5, 50.4), "KIEV": (30.5, 50.4), "BAHRAIN": (50.5, 26.2),
    "GAZA": (34.5, 31.5), "JERUSALEM": (35.2, 31.8), "TEL AVIV": (34.8, 32.1),
    "BEIJING": (116.4, 39.9), "SHANGHAI": (121.5, 31.2),
    "TOKYO": (139.7, 35.7), "SEOUL": (127.0, 37.5),
    "DELHI": (77.2, 28.6), "MUMBAI": (72.9, 19.1),
    "BANGKOK": (100.5, 13.8), "JAKARTA": (106.8, -6.2),
    "HANOI": (105.8, 21.0), "CAIRO": (31.2, 30.0), "LAGOS": (3.4, 6.5),
    "NAIROBI": (36.8, -1.3), "SYDNEY": (151.2, -33.9),
    "MELBOURNE": (145.0, -37.8), "PARIS": (2.35, 48.85),
    "BERLIN": (13.4, 52.5), "ROME": (12.5, 41.9), "MADRID": (-3.7, 40.4),
    "LONDON": (-0.1, 51.5), "MOSCOW": (37.6, 55.8), "TEHRAN": (51.4, 35.7),
    "BAGHDAD": (44.4, 33.3), "RIYADH": (46.7, 24.6), "DOHA": (51.5, 25.3),
    "DUBAI": (55.3, 25.2), "ANKARA": (32.9, 39.9),
    "ISLAMABAD": (73.1, 33.7), "KABUL": (69.2, 34.5),
    "DHAKA": (90.4, 23.8), "KATHMANDU": (85.3, 27.7),
    "COLOMBO": (79.9, 6.9), "YANGON": (96.2, 16.8),
    "KUALA LUMPUR": (101.7, 3.1), "SINGAPORE": (103.8, 1.35),
    "WELLINGTON": (174.8, -41.3), "AUCKLAND": (174.8, -36.8),
    "OTTAWA": (-75.7, 45.4), "TORONTO": (-79.4, 43.7),
    "MEXICO CITY": (-99.1, 19.4), "SAO PAULO": (-46.6, -23.5),
    "RIO DE JANEIRO": (-43.2, -22.9), "BUENOS AIRES": (-58.4, -34.6),
    "SANTIAGO": (-70.7, -33.4), "LIMA": (-77.0, -12.0),
    "BOGOTA": (-74.1, 4.7), "HAVANA": (-82.4, 23.1),
    "CARACAS": (-66.9, 10.5), "ANDHRA": (80.0, 16.0),
    "MONGOLIA": (106.0, 47.0), "TAIWAN": (121.0, 23.5),
    "KOREA": (127.0, 37.0), "HONG KONG": (114.2, 22.3),
    "GREENLAND": (-42.0, 72.0), "ALASKA": (-152.0, 64.0),
    "HAWAII": (-157.8, 21.3), "TEXAS": (-99.0, 31.0),
    "FLORIDA": (-81.5, 27.5), "CALIFORNIA": (-119.0, 36.5),
    "NEW YORK": (-74.0, 40.7), "WASHINGTON": (-77.0, 38.9),
}

COUNTRIES = {
    "UNITED STATES": (-98.0, 39.0), "AMERICA": (-98.0, 39.0),
    "CANADA": (-106.0, 56.0), "MEXICO": (-102.0, 23.0),
    "BRAZIL": (-52.0, -10.0), "ARGENTINA": (-64.0, -34.0),
    "CHILE": (-71.0, -31.0), "PERU": (-75.0, -9.0),
    "COLOMBIA": (-73.0, 4.0), "VENEZUELA": (-66.0, 8.0),
    "CUBA": (-79.0, 21.5), "PANAMA": (-80.0, 8.5),
    "CHINA": (104.0, 35.0), "INDIA": (79.0, 22.0),
    "JAPAN": (138.0, 37.0), "INDONESIA": (114.0, -2.0),
    "PAKISTAN": (70.0, 30.0), "BANGLADESH": (90.0, 24.0),
    "VIETNAM": (108.0, 14.0), "THAILAND": (101.0, 15.0),
    "MALAYSIA": (102.0, 4.0), "PHILIPPINES": (122.0, 13.0),
    "MYANMAR": (96.0, 21.0), "NEPAL": (84.0, 28.0),
    "SRI LANKA": (80.7, 7.0), "KAZAKHSTAN": (68.0, 48.0),
    "AFGHANISTAN": (66.0, 33.0), "AUSTRALIA": (134.0, -25.0),
    "NEW ZEALAND": (172.0, -41.0), "RUSSIA": (95.0, 62.0),
    "UKRAINE": (32.0, 49.0), "BELARUS": (28.0, 53.0),
    "POLAND": (19.0, 52.0), "GERMANY": (10.0, 51.0),
    "FRANCE": (2.0, 46.0), "ITALY": (12.5, 42.5),
    "SPAIN": (-4.0, 40.0), "PORTUGAL": (-8.0, 39.5),
    "BRITAIN": (-1.5, 52.5), "BRITISH": (-1.5, 52.5),
    "ENGLAND": (-1.5, 52.5), "IRELAND": (-8.0, 53.0),
    "NETHERLANDS": (5.5, 52.0), "BELGIUM": (4.5, 50.5),
    "SWITZERLAND": (8.0, 46.8), "AUSTRIA": (14.0, 47.5),
    "GREECE": (24.0, 38.0), "TURKEY": (35.0, 39.0),
    "TURKIYE": (35.0, 39.0), "SWEDEN": (18.0, 62.0),
    "NORWAY": (10.0, 62.0), "DENMARK": (10.0, 56.0),
    "FINLAND": (26.0, 64.0), "ICELAND": (-18.0, 65.0),
    "ROMANIA": (25.0, 45.8), "HUNGARY": (19.0, 47.0),
    "BULGARIA": (25.0, 42.7), "SERBIA": (21.0, 44.0),
    "CROATIA": (16.0, 45.0), "GEORGIA": (43.5, 42.0),
    "ARMENIA": (45.0, 40.0), "AZERBAIJAN": (47.5, 40.0),
    "MOLDOVA": (28.8, 47.0), "ESTONIA": (25.0, 59.0),
    "LATVIA": (25.0, 57.0), "LITHUANIA": (24.0, 55.5),
    "ISRAEL": (34.8, 31.0), "PALESTINE": (35.2, 31.9),
    "IRAN": (53.0, 32.0), "IRAQ": (44.0, 33.0), "SYRIA": (38.0, 35.0),
    "LEBANON": (35.8, 33.9), "JORDAN": (36.0, 31.0), "EGYPT": (30.0, 26.0),
    "SAUDI": (45.0, 24.0), "YEMEN": (47.5, 15.5), "OMAN": (57.0, 21.5),
    "QATAR": (51.2, 25.3), "KUWAIT": (47.5, 29.3), "LIBYA": (17.0, 26.0),
    "SUDAN": (30.0, 15.0), "ETHIOPIA": (39.0, 9.0),
    "KENYA": (38.0, 0.5), "NIGERIA": (8.0, 9.0), "GHANA": (-1.0, 8.0),
    "SOUTH AFRICA": (25.0, -29.0), "MOROCCO": (-6.0, 32.0),
    "ALGERIA": (3.0, 28.0), "TUNISIA": (9.5, 34.0),
}

REGION_XY = [
    ("MIDDLE EAST", (47.0, 29.0)),
    ("ASIA-PACIFIC", (125.0, 5.0)),
    ("SOUTH AMERICA", (-60.0, -15.0)),
    ("NORTH AMERICA", (-100.0, 40.0)),
    ("LATIN AMERICA", (-60.0, -15.0)),
    ("AMERICAS", (-90.0, 25.0)),
    ("EUROPE", (15.0, 52.0)),
    ("AFRICA", (20.0, 5.0)),
    ("OCEANIA", (140.0, -25.0)),
    ("PACIFIC", (150.0, 0.0)),
    ("ASIA", (100.0, 35.0)),
    ("WORLD", (0.0, 20.0)),
]


def story_pin_xy(story, i):
    """Lon/lat for a story's map pin, from its text, then its region."""
    text = (story["title"] + " " + story["body"]).upper()
    for table in (PLACES, COUNTRIES):
        for name in sorted(table, key=len, reverse=True):
            if name in text:
                lon, lat = table[name]
                break
        else:
            continue
        break
    else:
        lon, lat = 100.0, 35.0
        for key, (x, y) in REGION_XY:
            if key in story["tag"]:
                lon, lat = x, y
                break
    lon += ((i * 37) % 5 - 2) * 1.5
    lat += ((i * 23) % 3 - 1) * 1.5
    return lon, lat


def map_xy(lon, lat):
    x = MAP_X + (lon + 180.0) / 360.0 * MAP_W
    y = MAP_Y + (MAP_LAT_TOP - lat) / (MAP_LAT_TOP - MAP_LAT_BOT) * MAP_H
    return round(x), round(y)


def fill_polygon(cv, pts, color, clip):
    """Scanline fill of a polygon in pixel coords, clipped to clip."""
    if len(pts) < 3:
        return
    cx0, cy0, cx1, cy1 = clip
    ys = [p[1] for p in pts]
    y0 = max(cy0, min(ys))
    y1 = min(cy1, max(ys))
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x0, ya = pts[i]
            x1, yb = pts[(i + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(x0 + (y - ya) * (x1 - x0) / (yb - ya))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = max(cx0, int(xs[k]))
            xb = min(cx1, int(xs[k + 1]))
            if xb >= xa:
                cv.fill_rect(xa, y, xb - xa + 1, 1, color)


def draw_map(cv):
    clip = (MAP_X, MAP_Y, MAP_X + MAP_W - 1, MAP_Y + MAP_H - 1)
    cv.fill_rect(MAP_X, MAP_Y, MAP_W, MAP_H, OCEAN)
    # Graticule (drawn first so land covers it).
    for lon in range(-150, 151, 30):
        gx, _ = map_xy(lon, 0)
        cv.line(gx, MAP_Y, gx, MAP_Y + MAP_H - 1, GRID, 1)
    for lat in (60, 30, 0, -30):
        _, gy = map_xy(0, lat)
        cv.line(MAP_X, gy, MAP_X + MAP_W - 1, gy, GRID, 1)
    # Continents.
    for poly in CONTINENTS:
        pts = []
        for lon, lat in poly:
            px, py = map_xy(lon, lat)
            pts.append((max(MAP_X, min(MAP_X + MAP_W - 1, px)),
                        max(MAP_Y, min(MAP_Y + MAP_H - 1, py))))
        fill_polygon(cv, pts, LAND, clip)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            cv.line(x0, y0, x1, y1, LAND_EDGE, 1)
    # Region + ocean labels.
    for label, lon, lat in (
            ("NORTH AMERICA", -102, 54), ("SOUTH AMERICA", -60, -20),
            ("EUROPE", -16, 61), ("AFRICA", 16, 4), ("ASIA", 92, 54),
            ("AUSTRALIA", 117, -27), ("PACIFIC OCEAN", -150, -5)):
        lx, ly = map_xy(lon, lat)
        draw_text(cv, lx, ly, label, 2, MAP_LABEL)
    # Numbered pins, nudged apart where neighbours would overlap.
    pins = []
    for i, story in enumerate(STORIES):
        lon, lat = story_pin_xy(story, i)
        pins.append(list(map_xy(lon, lat)))
    for _ in range(3):
        moved = False
        for i in range(len(pins)):
            for j in range(i):
                dx = pins[i][0] - pins[j][0]
                dy = pins[i][1] - pins[j][1]
                if dx * dx + dy * dy < 22 * 22:
                    pins[i][1] += 12
                    moved = True
        if not moved:
            break
    for i, (px, py) in enumerate(pins):
        color = STORIES[i]["color"]
        cv.circle(px, py, 10, color, filled=True)
        cv.circle(px, py, 10, PIN_RING, t=2)
        num = str(i + 1)
        draw_text(cv, px - text_width(num, 2) // 2, py - 7, num, 2, WHITE)
    cv.rect_border(MAP_X, MAP_Y, MAP_W, MAP_H, INK, 2)


def draw_side_panel(cv):
    cv.fill_rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, WHITE)
    cv.rect_border(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, CARD_BORDER, 1)
    draw_text(cv, PANEL_X + 16, PANEL_Y + 8, "WHERE IT HAPPENED", 2, INK)
    cv.fill_rect(PANEL_X + 16, PANEL_Y + 26, PANEL_W - 32, 2, GOLD)
    for i, story in enumerate(STORIES):
        ry = PANEL_Y + 32 + i * 25
        cx, cy = PANEL_X + 26, ry + 12
        cv.circle(cx, cy, 9, story["color"], filled=True)
        num = str(i + 1)
        draw_text(cv, cx - text_width(num, 2) // 2, cy - 7, num, 2, WHITE)
        draw_text(cv, PANEL_X + 44, ry + 5, story["tag"], 2, INK)


def tint(color, bg, f=0.12):
    return tuple(round(bg[i] + (color[i] - bg[i]) * f) for i in range(3))


def draw_scene(cv, kind, sx, y, sw, h, color):
    """Scene inside a card's strip, drawn only in the box (sx, y, sw, h)
    left visible beside the tag chip. Elements scale to sw, so a long
    tag (narrow scene) still gets a readable motif, never spillover."""
    mid = tint(color, WHITE, 0.45)
    if sw < 40:
        return
    if kind == "summit":
        # Skyline with three flags and a sun.
        n = max(2, sw // 38)
        bw = sw // n
        for i in range(n):
            bh = 10 + ((i * 37) % 3) * 7
            cv.fill_rect(sx + i * bw + 2, y + h - 4 - bh, bw - 6, bh, mid)
        for f in (0.25, 0.55, 0.85):
            fx = sx + int(sw * f)
            cv.line(fx, y + 8, fx, y + h - 4, color, 2)
            cv.fill_rect(fx + 2, y + 8, 13, 7, color)
        if sw >= 150:
            cv.circle(sx + sw - 12, y + 11, 6, color, filled=True)
    elif kind == "quad":
        # Waves, ships, four dots.
        for wy in (y + 12, y + 22, y + 32):
            wx = sx
            while wx < sx + sw - 16:
                cv.line(wx, wy, wx + 8, wy - 3, color, 2)
                cv.line(wx + 8, wy - 3, wx + 16, wy, color, 2)
                wx += 16
        ships = (0.12,) if sw < 150 else (0.12, 0.55)
        for f in ships:
            shx = sx + int(sw * f)
            cv.fill_rect(shx, y + 18, 36, 7, mid)
            cv.line(shx + 18, y + 18, shx + 18, y + 6, mid, 2)
            cv.fill_rect(shx + 18, y + 6, 10, 6, mid)
        cx = sx + sw - 26
        for dx, dy in ((0, -10), (-13, 0), (13, 0), (0, 10)):
            cv.circle(cx + dx, y + 20 + dy, 3, color, filled=True)
    elif kind == "bridge":
        # Deck, arch below the deck, pillars, water, burst.
        cx = sx + sw // 2
        cv.line(sx, y + 18, sx + sw, y + 18, color, 3)
        cv.arc(cx, y + 18, 11, 0, 180, color, 2)
        for f in (0.08, 0.5, 0.92):
            px = sx + int(sw * f)
            cv.line(px, y + 18, px, y + 30, color, 2)
        cv.line(sx, y + 30, sx + sw, y + 30, color, 2)
        wx = sx
        while wx < sx + sw - 12:
            cv.line(wx, y + 35, wx + 12, y + 35, mid, 2)
            wx += 24
        for dx, dy in ((-8, 0), (8, 0), (0, -7), (0, 7),
                       (-6, -6), (6, 6), (-6, 6), (6, -6)):
            cv.line(cx, y + 8, cx + dx, y + 8 + dy, color, 2)
    elif kind == "radar":
        # Radar rings, sweep, blips, dot grid.
        cx, cy = sx + sw - 34, y + 20
        for r in (7, 13, 19):
            cv.circle(cx, cy, r, color, t=2)
        cv.line(cx, cy, cx + 17, cy - 10, color, 2)
        cv.circle(cx - 8, cy + 5, 3, color, filled=True)
        cv.circle(cx + 6, cy + 8, 3, mid, filled=True)
        cv.circle(cx, cy, 2, color, filled=True)
        gx = sx + 6
        while gx < sx + sw - 70:
            for gy in (y + 10, y + 30):
                cv.circle(gx, gy, 2, mid, filled=True)
            gx += 22
    elif kind == "alert":
        # Mountains, plane (wide scenes only), warning triangle.
        end = sx + sw - 46
        cv.line(sx + 2, y + 34, sx + (end - sx) // 3, y + 10, color, 3)
        cv.line(sx + (end - sx) // 3, y + 10, end, y + 34, color, 3)
        cv.line(sx + (end - sx) // 2, y + 34,
                sx + (end - sx) * 3 // 4, y + 18, color, 3)
        cv.line(sx + (end - sx) * 3 // 4, y + 18, end, y + 34, color, 3)
        if sw > 160:
            px, py = sx + sw - 92, y + 14
            cv.fill_rect(px, py, 30, 5, mid)
            cv.line(px + 7, py + 5, px + 12, py + 12, mid, 2)
            cv.line(px + 23, py + 5, px + 18, py + 12, mid, 2)
        tx, ty = sx + sw - 24, y + 20
        cv.line(tx, ty - 12, tx - 13, ty + 10, color, 3)
        cv.line(tx, ty - 12, tx + 13, ty + 10, color, 3)
        cv.line(tx - 13, ty + 10, tx + 13, ty + 10, color, 3)
        cv.fill_rect(tx - 1, ty - 6, 3, 8, color)
        cv.fill_rect(tx - 1, ty + 4, 3, 3, color)
    elif kind == "ban":
        # Document, stamp, seal.
        dw = min(84, int(sw * 0.45))
        cv.fill_rect(sx + 4, y + 6, dw, 28, WHITE)
        cv.rect_border(sx + 4, y + 6, dw, 28, color, 2)
        for ly in (y + 13, y + 20, y + 27):
            cv.fill_rect(sx + 12, ly, max(10, dw - 16), 3, mid)
        sx2, sy = sx + sw - 46, y + 20
        cv.circle(sx2, sy, 13, color, t=3)
        cv.line(sx2 - 9, sy + 9, sx2 + 9, sy - 9, color, 3)
        cv.circle(sx + sw - 12, y + 12, 6, color, filled=True)
    else:
        raise ValueError("unknown icon: %r" % kind)


# ------------------------------------------------------------------
# Layout
# ------------------------------------------------------------------

def draw_header(cv):
    cv.fill_rect(0, 0, W, 120, NAVY)
    cv.fill_rect(0, 120, W, 4, GOLD)
    # Small globe mark above the kicker.
    gx, gy = W // 2, 22
    cv.circle(gx, gy, 10, GOLD_LIGHT, t=2)
    cv.line(gx - 10, gy, gx + 10, gy, GOLD_LIGHT, 1)
    cv.line(gx, gy - 10, gx, gy + 10, GOLD_LIGHT, 1)
    draw_text_centered(cv, W // 2, 40, KICKER, 2, GOLD_LIGHT)
    draw_text_centered(cv, W // 2, 62, DATE_LINE, 5, WHITE)
    draw_text_centered(cv, W // 2, 100, SUBHEAD, 2, MUTED_BLUE)


def draw_card(cv, story, num, x, y, w, h):
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect_border(x, y, w, h, CARD_BORDER, 1)
    # Scene strip (40px): light tint, scene in the part the numbered
    # tag chip does not cover, chip on top at the left.
    cv.fill_rect(x, y, w, 40, tint(story["color"], WHITE, 0.88))
    chip = "%d - %s" % (num, story["tag"])
    chip_w = text_width(chip, 2) + 20
    draw_scene(cv, story["icon"], x + 10 + chip_w + 8, y,
               w - 18 - chip_w, 40, story["color"])
    cv.fill_rect(x + 10, y + 8, chip_w, 24, story["color"])
    draw_text(cv, x + 20, y + 14, chip, 2, WHITE)
    # Title, up to two lines.
    title_lines = wrap_text(story["title"], 3, w - 40)
    ty = y + 48
    for line in title_lines[:2]:
        draw_text(cv, x + 20, ty, line, 3, INK)
        ty += 24
    # Body, up to five lines, full inner width.
    body_lines = wrap_text(story["body"], 2, w - 40)
    by = y + 102
    for line in body_lines[:5]:
        draw_text(cv, x + 20, by, line, 2, BODY)
        by += 16


def draw_footer(cv):
    cv.fill_rect(0, 892, W, 132, NAVY_DARK)
    cv.fill_rect(0, 892, W, 2, GOLD)
    lines = wrap_text(ALSO_LINE, 2, W - 48)
    fy = 906
    for line in lines[:3]:
        draw_text(cv, 24, fy, line, 2, WHITE)
        fy += 17
    draw_text(cv, 24, 968, SOURCE_LINE, 2, FOOTER_MUTED)
    regions = len({s["tag"].split(" - ")[0] for s in STORIES})
    summary = "%d STORIES ACROSS %d REGIONS - ONE DAY, ONE PAGE" % (
        len(STORIES), regions)
    draw_text_centered(cv, W // 2, 992, summary, 2, GOLD_LIGHT)
    cv.fill_rect(0, 1014, W, 1, GOLD)
    cv.fill_rect(0, 1018, W, 1, GOLD)


def add_grain(cv, amp=2):
    """Light newsprint grain: a fixed pseudo-random +/-amp speckle on
    every second pixel. Deterministic -- no time or random state."""
    for yy in range(0, cv.h, 2):
        row = yy * cv.w * 3
        for xx in range(0, cv.w, 2):
            hh = (xx * 374761393 + yy * 668265263) & 0xFFFFFFFF
            hh ^= hh >> 13
            d = ((hh >> 5) % 5) - 2  # -2..2
            if d:
                i = row + xx * 3
                dv = d * amp // 2
                for k in range(3):
                    v = cv.buf[i + k] + dv
                    cv.buf[i + k] = 0 if v < 0 else (255 if v > 255 else v)


def render():
    cv = Canvas(W, H, PAPER)
    draw_header(cv)
    draw_map(cv)
    draw_side_panel(cv)
    # 2 columns x 3 rows of cards.
    margin, gap = 24, 10
    cw = (W - 2 * margin - gap) // 2
    ch = 184
    for i, story in enumerate(STORIES):
        col, row = i % 2, i // 2
        draw_card(cv, story, i + 1,
                  margin + col * (cw + gap),
                  320 + row * (ch + gap), cw, ch)
    draw_footer(cv)
    add_grain(cv)
    return cv


# ------------------------------------------------------------------
# Hand-rolled PNG encoder (filter 0, zlib level 9, no ancillary data)
# ------------------------------------------------------------------

def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.buf[y * cv.w * 3:(y + 1) * cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            _chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(render())
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
