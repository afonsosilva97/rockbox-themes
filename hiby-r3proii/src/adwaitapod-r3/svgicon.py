"""Rasterise GNOME's Adwaita symbolic icons (no dependencies).

Covers what the icons used by adwaitapod-r3 need: <path>, <circle>, <rect>
and <ellipse>, nested <g>, translate/scale/matrix transforms, fill-rule and
fill-opacity/opacity. Masks, clip paths, strokes and gradients are not
supported; icons using them must be avoided.
"""
import math
import re
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"
SS = 4  # supersampling per axis
CURVE_STEPS = 12


def _matrix(spec):
    """SVG transform attribute -> 2x3 affine (a, b, c, d, e, f)."""
    m = (1, 0, 0, 1, 0, 0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", spec or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "matrix":
            t = tuple(v)
        elif name == "rotate":
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                t = _mul(_mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        else:
            raise ValueError(f"unsupported transform {name}")
        m = _mul(m, t)
    return m


def _mul(p, q):
    a, b, c, d, e, f = p
    A, B, C, D, E, F = q
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
            a * E + c * F + e, b * E + d * F + f)


def _apply(m, pt):
    a, b, c, d, e, f = m
    x, y = pt
    return (a * x + c * y + e, b * x + d * y + f)


def _arc(x0, y0, rx, ry, phi, large, sweep, x1, y1):
    """Endpoint arc -> list of points (SVG implementation notes, F.6)."""
    if rx == 0 or ry == 0:
        return [(x1, y1)]
    rx, ry = abs(rx), abs(ry)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0, num / den)) * (-1 if large == sweep else 1)
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x0 + x1) / 2
    cy = sp * cxp + cp * cyp + (y0 + y1) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t0 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(4, int(abs(dt) / (math.pi / 16)))
    pts = []
    for i in range(1, n + 1):
        t = t0 + dt * i / n
        pts.append((cx + rx * math.cos(t) * cp - ry * math.sin(t) * sp,
                    cy + rx * math.cos(t) * sp + ry * math.sin(t) * cp))
    return pts


def path_polygons(d):
    """SVG path data -> list of closed polygons (lists of points)."""
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d)
    polys, cur = [], []
    x = y = sx = sy = 0.0
    last_ctrl = None
    cmd = None
    i = 0

    def num():
        nonlocal i
        v = float(tokens[i])
        i += 1
        return v

    def flag():
        # arc flags are single digits and may be packed: "0 01 2" is 0, 0, 1, 2
        nonlocal i
        t = tokens[i]
        if len(t) > 1:
            tokens[i] = t[1:]
        else:
            i += 1
        return int(t[0])

    def bezier(p0, p1, p2, p3):
        for k in range(1, CURVE_STEPS + 1):
            t = k / CURVE_STEPS
            u = 1 - t
            cur.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                        u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))

    while i < len(tokens):
        if re.match(r"[A-Za-z]", tokens[i]):
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if cur:
                    polys.append(cur)
                cur = []
                x, y = sx, sy
                last_ctrl = None
                continue
        rel = cmd.islower()
        c = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if c == "M":
            if cur:
                polys.append(cur)
            x, y = ox + num(), oy + num()
            sx, sy = x, y
            cur = [(x, y)]
            cmd = "l" if rel else "L"  # further pairs are line-tos
            last_ctrl = None
        elif c == "L":
            x, y = ox + num(), oy + num()
            cur.append((x, y))
            last_ctrl = None
        elif c == "H":
            x = ox + num()
            cur.append((x, y))
            last_ctrl = None
        elif c == "V":
            y = oy + num()
            cur.append((x, y))
            last_ctrl = None
        elif c in "CS":
            if c == "C":
                p1 = (ox + num(), oy + num())
            else:
                p1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            p2 = (ox + num(), oy + num())
            p3 = (ox + num(), oy + num())
            bezier((x, y), p1, p2, p3)
            last_ctrl = p2
            x, y = p3
        elif c in "QT":
            if c == "Q":
                q = (ox + num(), oy + num())
            else:
                q = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            p3 = (ox + num(), oy + num())
            p1 = (x + 2 / 3 * (q[0] - x), y + 2 / 3 * (q[1] - y))
            p2 = (p3[0] + 2 / 3 * (q[0] - p3[0]), p3[1] + 2 / 3 * (q[1] - p3[1]))
            bezier((x, y), p1, p2, p3)
            last_ctrl = q
            x, y = p3
        elif c == "A":
            rx, ry, rot, large, sweep = num(), num(), num(), flag(), flag()
            nx, ny = ox + num(), oy + num()
            cur.extend(_arc(x, y, rx, ry, math.radians(rot), large, sweep, nx, ny))
            x, y = nx, ny
            last_ctrl = None
        else:
            raise ValueError(f"bad path data near token {i}: {d[:40]}")
    if cur:
        polys.append(cur)
    return [p for p in polys if len(p) > 2]


def _ellipse(cx, cy, rx, ry):
    n = 48
    return [[(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]]


def _rect(x, y, w, h, rx, ry):
    if not rx and not ry:
        return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]]
    rx = min(rx or ry, w / 2)
    ry = min(ry or rx, h / 2)
    pts = []
    for cx, cy, a0 in ((x + w - rx, y + ry, -90), (x + w - rx, y + h - ry, 0),
                       (x + rx, y + h - ry, 90), (x + rx, y + ry, 180)):
        for k in range(9):
            a = math.radians(a0 + 90 * k / 8)
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return [pts]


def load(path):
    """-> (viewbox (x, y, w, h), [(polygons, evenodd, opacity)])."""
    root = ET.parse(path).getroot()
    vb = [float(v) for v in root.get("viewBox", "0 0 16 16").split()]
    shapes = []

    def walk(el, m, opacity, rule):
        tag = el.tag.replace(NS, "")
        if tag in ("defs", "clipPath", "mask", "title", "metadata"):
            return
        if el.get("mask") or el.get("clip-path"):
            raise ValueError(f"{path}: masks and clip paths are not supported")
        m = _mul(m, _matrix(el.get("transform")))
        style = dict(kv.split(":", 1) for kv in (el.get("style") or "").split(";") if ":" in kv)
        attr = lambda k: el.get(k, style.get(k))
        if attr("fill") == "none" or attr("display") == "none":
            return
        opacity *= float(attr("opacity") or 1) * float(attr("fill-opacity") or 1)
        rule = attr("fill-rule") or rule
        g = lambda k: float(el.get(k, 0))
        if tag == "path":
            polys = path_polygons(el.get("d", ""))
        elif tag == "circle":
            polys = _ellipse(g("cx"), g("cy"), g("r"), g("r"))
        elif tag == "ellipse":
            polys = _ellipse(g("cx"), g("cy"), g("rx"), g("ry"))
        elif tag == "rect":
            polys = _rect(g("x"), g("y"), g("width"), g("height"), g("rx"), g("ry"))
        else:
            polys = None
        if polys:
            shapes.append(([[_apply(m, p) for p in poly] for poly in polys], rule == "evenodd", opacity))
        for child in el:
            walk(child, m, opacity, rule)

    walk(root, (1, 0, 0, 1, 0, 0), 1.0, "nonzero")
    return vb, shapes


def coverage(polys, evenodd, size, scale, dx, dy):
    """Fraction of each pixel covered: list of rows of floats."""
    w, h = size
    edges = []
    for poly in polys:
        pts = [(x * scale + dx, y * scale + dy) for x, y in poly]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if y0 != y1:
                edges.append((x0, y0, x1, y1, 1 if y1 > y0 else -1))
    out = [[0.0] * w for _ in range(h)]
    inc = 1 / (SS * SS)
    for py in range(h):
        row = out[py]
        for sy in range(SS):
            y = py + (sy + 0.5) / SS
            xs = []
            for x0, y0, x1, y1, d in edges:
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append((x0 + (y - y0) * (x1 - x0) / (y1 - y0), d))
            if not xs:
                continue
            xs.sort()
            wind = 0
            for k in range(len(xs) - 1):
                wind = (wind + 1) % 2 if evenodd else wind + xs[k][1]
                if not wind:
                    continue
                a, b = xs[k][0], xs[k + 1][0]
                # sample points at x = px + (sx + 0.5) / SS inside [a, b)
                s0 = max(0, math.ceil(a * SS - 0.5))
                s1 = min(w * SS, math.ceil(b * SS - 0.5))
                for s in range(s0, s1):
                    row[s // SS] += inc
    return out


def render(path, px, size=None, offset=(0, 0)):
    """Icon -> alpha rows (0..1), icon scaled to px wide, drawn at offset in size."""
    vb, shapes = load(path)
    size = size or (px, px)
    scale = px / vb[2]
    dx, dy = offset[0] - vb[0] * scale, offset[1] - vb[1] * scale
    alpha = [[0.0] * size[0] for _ in range(size[1])]
    for polys, evenodd, opacity in shapes:
        cov = coverage(polys, evenodd, size, scale, dx, dy)
        for y in range(size[1]):
            ar, cr = alpha[y], cov[y]
            for x in range(size[0]):
                c = min(1.0, cr[x]) * opacity
                if c:
                    ar[x] = c + ar[x] * (1 - c)
    return alpha
