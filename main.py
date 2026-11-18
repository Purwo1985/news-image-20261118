#!/usr/bin/env python3
"""news-image-20261118 -- one image summing up Wednesday 18 November 2026.

A pure-stdlib Python 3.13 program. It draws a 1024x1024 newspaper-style
infographic (six stories plus an "also making news" strip) into an RGB
buffer, encodes it as a PNG with a hand-rolled encoder (zlib + struct),
and writes it to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).

No network, no files read, no timestamps, no randomness: two runs write
byte-identical output.

=====================================================================
NEWS DATA -- EDIT ONLY THIS SECTION TO FREEZE THE FINAL CONTENT
=====================================================================
Everything the picture says lives in the constants below (DATE_LINE,
KICKER, SUBHEAD, STORIES, ALSO_LINE, SOURCE_LINE). To update the
content for the final freeze on the evening of 19 November 2026 (WIB):

  1. Edit ONLY the STORIES list (and ALSO_LINE if needed) in this file.
     Each story is one dict with four fields:
       "tag"   -- short section label, e.g. "ASIA - SUMMITS"
       "color" -- (R, G, B) accent colour for the card
       "icon"  -- one of: summit, quad, bridge, radar, alert, ban
       "title" -- headline, UPPERCASE, keep under ~40 characters
       "body"  -- one plain sentence, keep under ~170 characters
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
# Icons: small pictograms drawn with primitives, one per story kind.
# Each draws inside a 56x56 box whose top-left is (x, y).
# ------------------------------------------------------------------

def tint(color, bg, f=0.12):
    return tuple(round(bg[i] + (color[i] - bg[i]) * f) for i in range(3))


def draw_icon(cv, kind, x, y, color):
    cx, cy = x + 28, y + 28
    cv.circle(cx, cy, 27, tint(color, WHITE, 0.15), filled=True)
    cv.circle(cx, cy, 27, color, t=2)
    if kind == "summit":
        # Three flags on poles.
        for i, fx in enumerate((cx - 13, cx, cx + 13)):
            cv.line(fx, cy + 14, fx, cy - 12, color, 2)
            cv.fill_rect(fx + 1, cy - 12, 9 if i != 2 else 8, 6, color)
    elif kind == "quad":
        # Four dots in a diamond, over two waves.
        for dx, dy in ((0, -12), (-12, 0), (12, 0), (0, 12)):
            cv.circle(cx + dx, cy + dy, 4, color, filled=True)
        cv.line(cx - 16, cy + 19, cx - 5, cy + 15, color, 2)
        cv.line(cx - 5, cy + 15, cx + 6, cy + 19, color, 2)
        cv.line(cx + 6, cy + 19, cx + 16, cy + 15, color, 2)
    elif kind == "bridge":
        # Deck, arch and pillars.
        cv.line(cx - 18, cy + 8, cx + 18, cy + 8, color, 3)
        cv.arc(cx, cy + 8, 14, 180, 360, color, 2)
        for px in (cx - 12, cx, cx + 12):
            cv.line(px, cy + 8, px, cy + 16, color, 2)
        cv.line(cx - 18, cy + 16, cx + 18, cy + 16, color, 2)
    elif kind == "radar":
        # Sweeping radar: rings, sweep line, blip.
        cv.circle(cx, cy, 15, color, t=2)
        cv.circle(cx, cy, 7, color, t=2)
        cv.line(cx, cy, cx + 14, cy - 14, color, 2)
        cv.circle(cx + 9, cy - 4, 3, color, filled=True)
        cv.circle(cx, cy, 2, color, filled=True)
    elif kind == "alert":
        # Warning triangle with an exclamation mark.
        cv.line(cx, cy - 16, cx - 16, cy + 12, color, 3)
        cv.line(cx, cy - 16, cx + 16, cy + 12, color, 3)
        cv.line(cx - 16, cy + 12, cx + 16, cy + 12, color, 3)
        cv.fill_rect(cx - 1, cy - 8, 3, 10, color)
        cv.fill_rect(cx - 1, cy + 5, 3, 3, color)
    elif kind == "ban":
        # Prohibition disc: circle with a diagonal bar.
        cv.circle(cx, cy, 15, color, t=3)
        cv.line(cx - 11, cy + 11, cx + 11, cy - 11, color, 3)
    else:
        raise ValueError("unknown icon: %r" % kind)


# ------------------------------------------------------------------
# Layout
# ------------------------------------------------------------------

def draw_header(cv):
    cv.fill_rect(0, 0, W, 200, NAVY)
    cv.fill_rect(0, 200, W, 4, GOLD)
    # Small globe mark above the kicker.
    gx, gy = W // 2, 30
    cv.circle(gx, gy, 11, GOLD_LIGHT, t=2)
    cv.line(gx - 11, gy, gx + 11, gy, GOLD_LIGHT, 1)
    cv.line(gx, gy - 11, gx, gy + 11, GOLD_LIGHT, 1)
    draw_text_centered(cv, W // 2, 52, KICKER, 2, GOLD_LIGHT)
    draw_text_centered(cv, W // 2, 82, DATE_LINE, 5, WHITE)
    draw_text_centered(cv, W // 2, 148, SUBHEAD, 2, MUTED_BLUE)


def draw_card(cv, story, x, y, w, h):
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect_border(x, y, w, h, CARD_BORDER, 1)
    cv.fill_rect(x, y, 8, h, story["color"])
    # Tag chip.
    chip_w = text_width(story["tag"], 2) + 20
    cv.fill_rect(x + 20, y + 14, chip_w, 24, story["color"])
    draw_text(cv, x + 30, y + 20, story["tag"], 2, WHITE)
    # Icon, top right.
    draw_icon(cv, story["icon"], x + w - 76, y + 14, story["color"])
    # Title, up to two lines, left of the icon.
    title_lines = wrap_text(story["title"], 3, w - 20 - 76 - 16 - 8)
    ty = y + 52
    for line in title_lines[:2]:
        draw_text(cv, x + 20, ty, line, 3, INK)
        ty += 26
    # Body, up to five lines, full inner width.
    body_lines = wrap_text(story["body"], 2, w - 40)
    by = ty + 10
    for line in body_lines[:5]:
        draw_text(cv, x + 20, by, line, 2, BODY)
        by += 17


def draw_footer(cv):
    cv.fill_rect(0, 900, W, 124, NAVY_DARK)
    cv.fill_rect(0, 900, W, 2, GOLD)
    lines = wrap_text(ALSO_LINE, 2, W - 48)
    fy = 914
    for line in lines[:3]:
        draw_text(cv, 24, fy, line, 2, WHITE)
        fy += 17
    draw_text(cv, 24, fy + 8, SOURCE_LINE, 2, FOOTER_MUTED)


def render():
    cv = Canvas(W, H, PAPER)
    draw_header(cv)
    # 2 columns x 3 rows of cards.
    margin, gap = 24, 14
    cw = (W - 2 * margin - gap) // 2
    ch = 216
    for i, story in enumerate(STORIES):
        col, row = i % 2, i // 2
        draw_card(cv, story,
                  margin + col * (cw + gap),
                  212 + row * (ch + gap), cw, ch)
    draw_footer(cv)
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
