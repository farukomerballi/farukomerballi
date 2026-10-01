#!/usr/bin/env python3
"""
farukomerballi — terminal profile promo.

Renders `terminal.gif`: a looping terminal session that connects, answers
`whoami`, makes one joke, applies an architecture, syncs an idea to production
and signs off.

Everything is drawn with Pillow. No editor, no footage.

    pip install pillow
    python3 assets/promo/generate.py
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- canvas ---
W, H = 880, 440                       # layout units
SS = 2                                # supersample, discarded on export
EXPORT = int(os.environ.get("PROMO_EXPORT", "2"))
DS = SS * EXPORT
FW, FH = W * DS, H * DS
OW, OH = W * EXPORT, H * EXPORT
FRAME_MS = 40                         # 25 fps

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
OUT = os.path.join(HERE, "terminal.gif")


def S(v: float) -> int:
    return int(round(v * DS))


# --------------------------------------------------------------- palette ---
BG     = (0x09, 0x0B, 0x0F)
RAISED = (0x11, 0x14, 0x1A)
LINE   = (0x23, 0x28, 0x31)
FAINT  = (0x4B, 0x53, 0x5F)
MUTED  = (0x7B, 0x84, 0x91)
BODY   = (0xAC, 0xB3, 0xBE)
HEAD   = (0xEE, 0xF1, 0xF5)
ACC    = (0x5E, 0xEA, 0xD4)           # the only saturated value
WHITE  = (0xFF, 0xFF, 0xFF)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def fade(c, t):
    return mix(BG, c, t)


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def ease(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_io(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def prog(t, start, length):
    return clamp((t - start) / max(1e-6, length))


# ----------------------------------------------------------------- fonts ---
_FONT_FILES = {
    "mono": "JetBrainsMono-Regular.ttf",
    "mono_m": "JetBrainsMono-Medium.ttf",
    "mono_b": "JetBrainsMono-Bold.ttf",
    "sans": "Inter-Regular.ttf",
    "sans_m": "Inter-Medium.ttf",
    "display": "InterDisplay-Bold.ttf",
    "display_s": "InterDisplay-SemiBold.ttf",
}
_font_cache: dict = {}


def F(kind: str, size: float):
    key = (kind, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(os.path.join(FONTS, _FONT_FILES[kind]), S(size))
    return _font_cache[key]


def tw(s, size, kind="mono"):
    """Text width in layout units."""
    return F(kind, size).getlength(s) / DS


# ----------------------------------------------------------------- frame ---
class Frame:
    def __init__(self, base):
        self.img = base.copy()
        self.d = ImageDraw.Draw(self.img)
        self.glow = None
        self.gd = None

    def _g(self):
        if self.glow is None:
            self.glow = Image.new("RGB", (FW, FH), (0, 0, 0))
            self.gd = ImageDraw.Draw(self.glow)
        return self.gd

    # text ---------------------------------------------------------------
    def text(self, x, y, s, size, col, kind="mono", anchor="la", glow=0.0, spacing=0.0):
        if not s:
            return
        f = F(kind, size)
        if spacing:
            cx = x
            if anchor[0] == "m":
                cx = x - self.spaced_w(s, size, kind, spacing) / 2
            for ch in s:
                self.d.text((S(cx), S(y)), ch, font=f, fill=col, anchor="l" + anchor[1])
                if glow:
                    self._g().text((S(cx), S(y)), ch, font=f, fill=mix((0, 0, 0), col, glow), anchor="l" + anchor[1])
                cx += tw(ch, size, kind) + spacing
            return
        self.d.text((S(x), S(y)), s, font=f, fill=col, anchor=anchor)
        if glow:
            self._g().text((S(x), S(y)), s, font=f, fill=mix((0, 0, 0), col, glow), anchor=anchor)

    def spaced_w(self, s, size, kind, spacing):
        return sum(tw(ch, size, kind) for ch in s) + spacing * (len(s) - 1)

    def rich(self, x, y, segs, size, kind="mono", limit=None, alpha=1.0):
        """segs: [(text, colour)]; limit: visible character budget."""
        left = limit if limit is not None else 10 ** 9
        cx = x
        for s, col in segs:
            if left <= 0:
                break
            part = s[:left]
            left -= len(part)
            self.text(cx, y, part, size, fade(col, alpha), kind)
            cx += tw(part, size, kind)
        return cx

    # shapes -------------------------------------------------------------
    def line(self, pts, col, w=1.0, glow=0.0):
        p = [(S(a), S(b)) for a, b in pts]
        self.d.line(p, fill=col, width=max(1, S(w)), joint="curve")
        if glow:
            self._g().line(p, fill=mix((0, 0, 0), col, glow), width=max(1, S(w * 3)), joint="curve")

    def rect(self, x0, y0, x1, y1, r=6, fill=None, outline=None, w=1.0, glow=0.0):
        box = (S(x0), S(y0), S(x1), S(y1))
        self.d.rounded_rectangle(box, radius=S(r), fill=fill, outline=outline, width=max(1, S(w)))
        if glow and outline:
            self._g().rounded_rectangle(box, radius=S(r), outline=mix((0, 0, 0), outline, glow), width=max(1, S(w * 3)))

    def dot(self, x, y, r, col, glow=0.0):
        box = (S(x - r), S(y - r), S(x + r), S(y + r))
        self.d.ellipse(box, fill=col)
        if glow:
            g = r * 3.2
            self._g().ellipse((S(x - g), S(y - g), S(x + g), S(y + g)), fill=mix((0, 0, 0), col, glow))

    def finish(self):
        img = self.img
        if self.glow is not None:
            g = self.glow.resize((FW // 8, FH // 8), Image.BILINEAR)
            g = g.filter(ImageFilter.GaussianBlur(4)).resize((FW, FH), Image.BILINEAR)
            img = ImageChops.screen(img, g)
        return img


def polyline_partial(pts, t):
    """First t (0..1) of a polyline, by length."""
    segs = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(segs)
    want = total * clamp(t)
    out = [pts[0]]
    for i, L in enumerate(segs):
        if want >= L:
            out.append(pts[i + 1])
            want -= L
        else:
            if L > 0 and want > 0:
                a, b = pts[i], pts[i + 1]
                out.append((a[0] + (b[0] - a[0]) * want / L, a[1] + (b[1] - a[1]) * want / L))
            break
    return out


def point_on(pts, t):
    p = polyline_partial(pts, t)
    return p[-1]


# ------------------------------------------------------------ background ---
def make_background():
    img = Image.new("RGB", (FW, FH), BG)
    d = ImageDraw.Draw(img)
    # dot grid
    step = 22
    for gx in range(step, W, step):
        for gy in range(step, H - 30, step):
            r = 0.55
            d.ellipse((S(gx - r), S(gy - r), S(gx + r), S(gy + r)), fill=mix(BG, LINE, 0.55))
    # soft centre light
    rad = Image.radial_gradient("L").resize((FW, FH), Image.BILINEAR)
    light = Image.new("RGB", (FW, FH), mix(BG, ACC, 0.05))
    mask = ImageChops.invert(rad).point(lambda v: int(v * 0.85))
    img = Image.composite(light, img, mask)
    # vignette
    vig = Image.radial_gradient("L").resize((FW, FH), Image.BILINEAR).point(lambda v: 255 - int(v * 0.55))
    img = ImageChops.multiply(img, Image.merge("RGB", (vig, vig, vig)))
    return img


def make_scanlines():
    m = Image.new("L", (OW, OH), 255)
    d = ImageDraw.Draw(m)
    for y in range(0, OH, 2 * EXPORT // 2 * 2 if EXPORT > 1 else 2):
        d.line([(0, y), (OW, y)], fill=232)
    return Image.merge("RGB", (m, m, m))


# ---------------------------------------------------------------- scenes ---
MX = 56            # left margin
PROMPT = "❯ "


def prompt(fr, y, cmd, t, start, cps=1.5, cursor=True, size=15):
    n = int(clamp((t - start) * cps, 0, len(cmd))) if t >= start else 0
    x = fr.text(MX, y, PROMPT, size, ACC, "mono_b") or MX
    x = MX + tw(PROMPT, size, "mono_b")
    fr.text(x, y, cmd[:n], size, HEAD, "mono")
    done = n >= len(cmd)
    if cursor and (not done or (int(t) // 12) % 2 == 0):
        cx = x + tw(cmd[:n], size)
        fr.rect(cx + 1, y + 1, cx + 9, y + size + 3, r=1, fill=ACC)
    return done


def scene_ssh(fr, t):
    cmd = "ssh omer@farukomerballi"
    done = prompt(fr, 70, cmd, t, 8, 1.3, cursor=t < 32)
    y = 104
    if t >= 32:
        spin = "|/-\\"[int(t / 2) % 4]
        if t < 46:
            fr.rich(MX + 20, y, [(spin + "  ", ACC), ("connecting to farukomerballi:22", FAINT)], 13)
        else:
            fr.rich(MX + 20, y, [("✓  ", ACC), ("authenticated", BODY), ("  ·  ed25519", FAINT)], 13)
    if t >= 50:
        fr.rich(MX + 20, y + 26, [("welcome back, ", MUTED), ("builder", HEAD), (".", MUTED)], 13,
                limit=int((t - 50) * 2.5))
    if t >= 58:
        prompt(fr, 168, "whoami", t, 60, 1.0)


def iso_cube(cx, cy, r):
    c30 = math.cos(math.radians(30))
    top = (cx, cy - r)
    ur = (cx + r * c30, cy - r / 2)
    lr = (cx + r * c30, cy + r / 2)
    bot = (cx, cy + r)
    ll = (cx - r * c30, cy + r / 2)
    ul = (cx - r * c30, cy - r / 2)
    ctr = (cx, cy)
    outer = [top, ur, lr, bot, ll, ul, top]
    inner = [[ctr, ul], [ctr, ur], [ctr, bot]]
    return outer, inner, [top, ur, ctr, ul]


def draw_cube(fr, cx, cy, r, t, col_out, col_in, glow=0.0, face=0.0):
    outer, inner, topface = iso_cube(cx, cy, r)
    if face > 0:
        fr.d.polygon([(S(a), S(b)) for a, b in topface], fill=fade(ACC, face))
    fr.line(polyline_partial(outer, ease_io(t)), col_out, 1.3, glow)
    k = clamp((t - 0.55) / 0.45)
    for seg in inner:
        if k > 0:
            fr.line(polyline_partial(seg, ease(k)), col_in, 1.3, glow)


def scene_whoami(fr, t):
    a = ease(prog(t, 0, 8))
    fr.text(MX, 62, "WHOAMI", 10, fade(FAINT, a), "mono_m", spacing=3.2)
    # name: wipe in
    name = "Omer Faruk Balli"
    k = ease(prog(t, 4, 20))
    if k > 0:
        nw = tw(name, 56, "display")
        layer = Frame(fr.img)
        layer.text(MX - 2, 84, name, 56, HEAD, "display", glow=0.35)
        clip = Image.new("L", (FW, FH), 0)
        ImageDraw.Draw(clip).rectangle((0, 0, S(MX + (nw + 8) * k), FH), fill=255)
        fr.img.paste(layer.finish(), (0, 0), clip)
        fr.d = ImageDraw.Draw(fr.img)
    # rule
    rk = ease(prog(t, 18, 16))
    if rk > 0:
        fr.line([(MX, 166), (MX + 440 * rk, 166)], ACC, 1.2, glow=0.4)
    # tagline
    if t >= 30:
        fr.rich(MX, 182, [("Not an engineer ", HEAD), (":)", ACC), (" — just someone who loves to build things.", HEAD)],
                19, "sans", limit=int((t - 30) * 2.4))
    rows = [
        ("builds", "platforms · pipelines · lakehouses"),
        ("stack", "kubernetes · kafka · iceberg · argocd"),
        ("rule", "do it twice by hand, the third time it ships as code"),
    ]
    for i, (k_, v) in enumerate(rows):
        ra = ease(prog(t, 62 + i * 6, 8))
        if ra <= 0:
            continue
        y = 238 + i * 25 + (1 - ra) * 6
        fr.text(MX, y, k_, 12, fade(FAINT, ra), "mono")
        fr.text(MX + 82, y, v, 12, fade(BODY, ra), "mono")
    # mark, right side
    ck = prog(t, 22, 40)
    if ck > 0:
        draw_cube(fr, 742, 214, 74, ck, mix(BG, LINE, 1.6) if False else (0x30, 0x37, 0x42), (0x30, 0x37, 0x42))
        if ck >= 1:
            outer, inner, _ = iso_cube(742, 214, 74)
            pk = ease(prog(t, 62, 18))
            fr.line(polyline_partial([inner[1][0], inner[1][1]], pk), ACC, 1.3, glow=0.5)


def scene_kubectl(fr, t):
    prompt(fr, 70, "kubectl get engineers -A", t, 6, 1.4, cursor=t < 30)
    if t >= 30:
        fr.text(MX, 102, "No resources found.", 14, MUTED)
    if t >= 52:
        prompt(fr, 146, "kubectl get builders", t, 54, 1.4, cursor=t < 72)
    if t >= 72:
        cols = [MX, MX + 120, MX + 210, MX + 340]
        for x, h in zip(cols, ["NAME", "READY", "STATUS", "AGE"]):
            fr.text(x, 180, h, 12, FAINT, "mono_m")
    if t >= 77:
        a = ease(prog(t, 77, 6))
        fr.text(cols[0], 204, "omer", 14, fade(HEAD, a))
        fr.text(cols[1], 204, "1/1", 14, fade(BODY, a))
        fr.dot(cols[2] + 5, 213, 3.2, fade(ACC, a), glow=0.6 * a)
        fr.text(cols[2] + 16, 204, "Running", 14, fade(ACC, a))
        fr.text(cols[3], 204, "∞", 14, fade(BODY, a))
    if t >= 88:
        fr.rich(MX, 250, [("# not an engineer — a ", FAINT), ("builder", MUTED), (".", FAINT)], 13,
                limit=int((t - 88) * 2.2))


# architecture graph ------------------------------------------------------
NODES = {
    "events":     (150, 168),
    "api":        (150, 238),
    "sftp":       (150, 308),
    "kafka":      (372, 238),
    "iceberg":    (584, 190),
    "opensearch": (584, 286),
    "doris":      (782, 190),
    "dashboards": (782, 286),
}
NODE_T = {"events": 28, "api": 31, "sftp": 34, "kafka": 44,
          "iceberg": 56, "opensearch": 59, "doris": 70, "dashboards": 73}
EDGES = [("events", "kafka"), ("api", "kafka"), ("sftp", "kafka"),
         ("kafka", "iceberg"), ("kafka", "opensearch"),
         ("iceberg", "doris"), ("opensearch", "dashboards")]
KIND = {"events": "source", "api": "source", "sftp": "source", "kafka": "statefulset",
        "iceberg": "table", "opensearch": "index", "doris": "warehouse", "dashboards": "deployment"}


def node_box(name):
    x, y = NODES[name]
    w = max(84, tw(name, 12) + 34)
    return x - w / 2, y - 15, x + w / 2, y + 15


def edge_pts(a, b):
    ax0, ay0, ax1, ay1 = node_box(a)
    bx0, by0, bx1, by1 = node_box(b)
    sy, ey = NODES[a][1], NODES[b][1]
    sx, ex = ax1, bx0
    if sy == ey:
        return [(sx, sy), (ex, ey)]
    mx = (sx + ex) / 2
    return [(sx, sy), (mx, sy), (mx, ey), (ex, ey)]


def scene_apply(fr, t):
    prompt(fr, 62, "kubectl apply -f architecture.yaml", t, 4, 1.7, cursor=t < 28)
    # rolling log line
    latest = None
    for n, nt in NODE_T.items():
        if t >= nt:
            latest = n
    if latest and t < 82:
        fr.rich(MX, 92, [(f"{KIND[latest]}/", FAINT), (latest, BODY), (" created", FAINT)], 12)
    if t >= 82:
        fr.rich(MX, 92, [("✓ ", ACC), ("8 resources applied", BODY), ("  ·  ", FAINT), ("streaming", ACC)], 12)
        # cover the log line underneath
    # edges
    for a, b in EDGES:
        st = NODE_T[a] + 4
        k = ease_io(prog(t, st, 12))
        if k > 0:
            fr.line(polyline_partial(edge_pts(a, b), k), (0x2C, 0x33, 0x3D), 1.1)
    # packets
    if t >= 84:
        for i, (a, b) in enumerate(EDGES):
            pts = edge_pts(a, b)
            for j in range(2):
                ph = ((t - 84) / 26.0 + i * 0.37 + j * 0.5) % 1.0
                x, y = point_on(pts, ph)
                fr.dot(x, y, 2.0, ACC, glow=0.55)
    # nodes
    for n, nt in NODE_T.items():
        a = ease(prog(t, nt, 7))
        if a <= 0:
            continue
        x0, y0, x1, y1 = node_box(n)
        flash = 1 - prog(t, nt + 4, 14)
        hero = n == "kafka"
        outline = mix(LINE, ACC, max(flash, 0.75 if hero else 0)) if a >= 1 else fade(LINE, a)
        fr.rect(x0, y0, x1, y1, r=7, fill=fade(RAISED, a), outline=outline, w=1.0,
                glow=0.45 if hero and a >= 1 else 0)
        fr.dot(x0 + 14, NODES[n][1], 2.6, fade(ACC if t >= nt + 6 else FAINT, a))
        fr.text(x0 + 24, NODES[n][1], n, 12, fade(HEAD if hero else BODY, a), "mono", anchor="lm")
    # column captions
    ca = ease(prog(t, 76, 10))
    if ca > 0:
        for x, s in [(150, "ingest"), (372, "stream"), (584, "store"), (782, "serve")]:
            fr.text(x, 352, s.upper(), 9.5, fade(FAINT, ca), "mono_m", anchor="mm", spacing=2.6)
    if t >= 92:
        a = ease(prog(t, 92, 10))
        fr.text(W / 2, 384, "data flows  ·  the system breathes", 14, fade(MUTED, a), "sans", anchor="mm")


STAGES = ["idea", "design", "infra", "automate", "live"]


def scene_sync(fr, t):
    prompt(fr, 62, "argocd app sync idea --prune", t, 4, 1.6, cursor=t < 26)
    xs = [130 + i * 155 for i in range(5)]
    y = 178
    beam = ease_io(prog(t, 30, 58))
    bx = xs[0] + (xs[-1] - xs[0]) * beam
    ap = ease(prog(t, 22, 8))
    # rail
    fr.line([(xs[0], y), (xs[-1], y)], fade((0x2C, 0x33, 0x3D), ap), 1.1)
    if beam > 0:
        fr.line([(xs[0], y), (bx, y)], ACC, 1.3, glow=0.5)
        if beam < 1:
            fr.dot(bx, y, 3, ACC, glow=0.8)
    for i, (x, s) in enumerate(zip(xs, STAGES)):
        done = bx >= x - 0.5 and beam > 0
        last = i == len(STAGES) - 1
        w = max(98, tw(s, 13) + 36)
        fill = fade(RAISED, ap)
        if last and done:
            fill = mix(RAISED, ACC, 0.13)
        outline = (ACC if done else fade(LINE, ap))
        fr.rect(x - w / 2, y - 18, x + w / 2, y + 18, r=8, fill=fill, outline=outline, w=1.0,
                glow=(0.5 if (done and last) else 0))
        fr.text(x, y, s, 13, fade(HEAD if done else MUTED, ap), "mono_m" if done else "mono", anchor="mm")
        fr.text(x, y + 36, f"0{i + 1}", 9.5, fade(FAINT, ap), "mono", anchor="mm")
        if done:
            fr.text(x, y + 54, "✓ synced", 10.5, ACC, "mono", anchor="mm")
    # status block
    sa = ease(prog(t, 24, 8))
    if sa > 0:
        fin = t >= 90
        rows = [
            ("Sync Status", "Synced" if fin else ("Syncing" if beam > 0 else "OutOfSync"), ACC if fin else MUTED),
            ("Health Status", "Healthy" if fin else ("Progressing" if beam > 0 else "Missing"), ACC if fin else MUTED),
            ("Revision", "HEAD · v∞", BODY),
        ]
        for i, (k_, v, c) in enumerate(rows):
            yy = 288 + i * 24
            fr.text(MX, yy, k_, 12.5, fade(FAINT, sa))
            fr.text(MX + 170, yy, v, 12.5, fade(c, sa), glow=0.35 if (fin and c == ACC) else 0)


def scene_exit(fr, t):
    ck = prog(t, 4, 30)
    if ck > 0:
        face = 0.10 * ease(prog(t, 28, 10))
        draw_cube(fr, W / 2, 150, 44, ck, ACC, ACC, glow=0.55, face=face)
    a = ease(prog(t, 26, 12))
    if a > 0:
        fr.text(W / 2, 240, "farukomerballi", 32, fade(HEAD, a), "display", anchor="mm", glow=0.25 * a)
    b = ease(prog(t, 34, 12))
    if b > 0:
        fr.text(W / 2, 278, "builder  ·  solution architect at heart", 12.5, fade(MUTED, b), "mono", anchor="mm")
    c = ease(prog(t, 42, 12))
    if c > 0:
        segs = [("github.com/", FAINT), ("farukomerballi", BODY), ("   ·   ", LINE),
                ("linkedin.com/in/", FAINT), ("omerfarukballi", BODY), ("   ·   ", LINE),
                ("x.com/", FAINT), ("farukomerballi", BODY)]
        fr.rich(W / 2 - tw("".join(s_ for s_, _ in segs), 11.5) / 2, 312, segs, 11.5, alpha=c)


SCENES = [
    ("ssh", scene_ssh, 72),
    ("whoami", scene_whoami, 150),
    ("kubectl", scene_kubectl, 118),
    ("apply", scene_apply, 150),
    ("sync", scene_sync, 122),
    ("exit", scene_exit, 92),
]
FADE = 7
POWER_ON = 12
POWER_OFF = 14


def status_bar(fr, idx):
    y0, y1 = 414, 440
    fr.d.rectangle((0, S(y0), FW, FH), fill=RAISED)
    fr.d.line([(0, S(y0)), (FW, S(y0))], fill=LINE, width=max(1, S(0.6)))
    seg = " ◆ omer "
    sw = tw(seg, 11, "mono_b")
    fr.d.rectangle((0, S(y0), S(sw + 10), FH), fill=ACC)
    fr.text(5, (y0 + y1) / 2, seg, 11, BG, "mono_b", anchor="lm")
    x = sw + 22
    for i, (name, _, _) in enumerate(SCENES):
        label = f"{i + 1}:{name}" + ("*" if i == idx else "")
        col = HEAD if i == idx else FAINT
        fr.text(x, (y0 + y1) / 2, label, 11, col, "mono_m" if i == idx else "mono", anchor="lm")
        x += tw(label, 11) + 16
    right = "github.com/farukomerballi"
    rw = tw(right, 11)
    fr.dot(W - 18 - rw - 12, (y0 + y1) / 2, 2.6, ACC)
    fr.text(W - 18 - rw, (y0 + y1) / 2, right, 11, MUTED, anchor="lm")


def total_frames():
    return sum(n for _, _, n in SCENES)


def render_frame(i, base, scan):
    # locate scene
    acc = 0
    for idx, (name, fn, n) in enumerate(SCENES):
        if i < acc + n:
            t = i - acc
            break
        acc += n
    fr = Frame(base)
    fn(fr, t)
    img = fr.finish()
    # scene fades
    a = min(1.0, (t + 1) / FADE if idx > 0 else 1.0, (n - t) / FADE if idx < len(SCENES) - 1 else 1.0)
    if a < 1:
        img = Image.blend(base, img, ease(a))
    bar = Frame(img)
    status_bar(bar, idx)
    img = bar.img.resize((OW, OH), Image.LANCZOS)
    img = ImageChops.multiply(img, scan)
    # power on / off
    total = total_frames()
    k = None
    if i < POWER_ON:
        k = i / POWER_ON
    elif i >= total - POWER_OFF:
        k = (total - 1 - i) / POWER_OFF
    if k is not None:
        img = crt(img, k)
    return img


def crt(img, k):
    """k=0 black, k=1 fully open. Line widens first, then opens vertically."""
    out = Image.new("RGB", (OW, OH), (0, 0, 0))
    d = ImageDraw.Draw(out)
    cy = OH // 2
    if k < 0.35:
        w = OW * ease(k / 0.35)
        d.rectangle((OW / 2 - w / 2, cy - 1, OW / 2 + w / 2, cy + 1), fill=mix(BG, ACC, 0.9))
        return out
    h = OH * ease((k - 0.35) / 0.65)
    box = (0, int(cy - h / 2), OW, int(cy + h / 2))
    if box[3] > box[1]:
        out.paste(img.crop(box), box[:2])
    edge = mix(BG, ACC, 0.7 * (1 - (k - 0.35) / 0.65))
    d.line([(0, box[1]), (OW, box[1])], fill=edge, width=2)
    d.line([(0, box[3]), (OW, box[3])], fill=edge, width=2)
    return out


def build_palette(samples):
    strip = Image.new("RGB", (OW // 4, (OH // 4) * len(samples)))
    for k, s in enumerate(samples):
        strip.paste(s.resize((OW // 4, OH // 4), Image.BILINEAR), (0, k * (OH // 4)))
    # guarantee exact brand values are present
    sw = Image.new("RGB", (OW // 4, 40), BG)
    d = ImageDraw.Draw(sw)
    brand = [BG, RAISED, LINE, FAINT, MUTED, BODY, HEAD, ACC] + [mix(BG, ACC, q / 10) for q in range(1, 10)]
    cw = (OW // 4) / len(brand)
    for j, c in enumerate(brand):
        d.rectangle((j * cw, 0, (j + 1) * cw, 40), fill=c)
    full = Image.new("RGB", (OW // 4, strip.height + 40 * 6))
    full.paste(strip, (0, 0))
    for r in range(6):
        full.paste(sw, (0, strip.height + r * 40))
    return full.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def main():
    base = make_background()
    scan = make_scanlines()
    total = total_frames()
    only = os.environ.get("PROMO_FRAMES")
    if only:
        out_dir = os.environ.get("PROMO_OUT", HERE)
        for i in [int(v) for v in only.split(",")]:
            render_frame(i, base, scan).save(os.path.join(out_dir, f"preview_{i:04d}.png"))
        return

    # Frames go through a disk cache so memory stays flat: holding ~700
    # full-size RGB frames at once does not fit in a small container.
    cache = os.environ.get("PROMO_CACHE") or os.path.join(HERE, ".cache")
    os.makedirs(cache, exist_ok=True)

    def frame(i):
        cp = os.path.join(cache, f"f{i:04d}.png")
        if os.path.exists(cp):
            return Image.open(cp).convert("RGB")
        f = render_frame(i, base, scan)
        f.save(cp, compress_level=1)
        return f

    for i in range(total):
        frame(i)
        if i % 50 == 0:
            print(f"frame {i}/{total}", flush=True)

    pal = build_palette([frame(i) for i in range(0, total, max(1, total // 24))])

    out, dur, prev = [], [], None
    for i in range(total):
        q = frame(i).quantize(palette=pal, dither=Image.Dither.NONE)
        b = q.tobytes()
        if prev is not None and b == prev:
            dur[-1] += FRAME_MS
        else:
            out.append(q)
            dur.append(FRAME_MS)
            prev = b
    out[0].save(OUT, save_all=True, append_images=out[1:], duration=dur, loop=0, optimize=False, disposal=1)
    print(f"wrote {OUT}: {len(out)} frames, {sum(dur) / 1000:.1f}s, {os.path.getsize(OUT) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
