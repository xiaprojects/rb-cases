"""Shaded PNG views of FreeCAD shapes, for the generators that run in freecad.cmd,
where the 3-D view is not available. Shared by tools/display_cases.py and
tools/joystick_grip.py.
"""
import math

import MeshPart

LABEL_FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def render(items, path, az, el, width=1400, labels=()):
    """Shaded orthographic view with outlines, drawn with a z-buffer: items are (shape, rgb),
    labels (text, 3-D point). az 0 looks from the front, 90 from the right; el from above."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    a, e = math.radians(az), math.radians(el)
    d = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])  # towards the camera
    rgt = np.cross(-d, [0.0, 0.0, 1.0])
    rgt /= np.linalg.norm(rgt)
    up = np.cross(rgt, -d)
    light = 0.6 * d + 0.7 * up - 0.3 * rgt
    light /= np.linalg.norm(light)
    tris, cols = [], []
    for shape, rgb in items:
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.15, AngularDeflection=math.radians(20))
        pts, fac = mesh.Topology
        p = np.array([[q.x, q.y, q.z] for q in pts])
        tris.append(p[np.array(fac, dtype=int)])
        cols.append(np.tile(np.array(rgb, float), (len(fac), 1)))
    t, c = np.concatenate(tris), np.concatenate(cols)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-12
    t, c, n = t[ok], c[ok], n[ok] / ln[ok, None]
    front = n @ d > 0
    t, c, n = t[front], c[front], n[front]
    c = c * (0.42 + 0.58 * np.clip(n @ light, 0, 1))[:, None]
    sx, sy, sz = t @ rgt, t @ up, t @ d
    ss = 2  # supersampling
    x0, x1, y0, y1 = sx.min(), sx.max(), sy.min(), sy.max()
    m = 0.03 * (x1 - x0)
    k = width * ss / (x1 - x0 + 2 * m)
    W, H = int(width * ss), int((y1 - y0 + 2 * m) * k)
    px, py = (sx - x0 + m) * k, (y1 + m - sy) * k
    zbuf = np.full((H, W), -np.inf)
    img = np.full((H, W, 3), 255.0)
    nbuf = np.zeros((H, W, 3))
    for i in range(len(px)):
        xa, xb, xc = px[i]
        ya, yb, yc = py[i]
        ix0, ix1 = max(int(min(xa, xb, xc)), 0), min(int(max(xa, xb, xc)) + 1, W - 1)
        iy0, iy1 = max(int(min(ya, yb, yc)), 0), min(int(max(ya, yb, yc)) + 1, H - 1)
        if ix1 < ix0 or iy1 < iy0:
            continue
        area = (xb - xa) * (yc - ya) - (xc - xa) * (yb - ya)
        if abs(area) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(ix0, ix1 + 1) + 0.5, np.arange(iy0, iy1 + 1) + 0.5)
        w0 = ((xb - gx) * (yc - gy) - (xc - gx) * (yb - gy)) / area
        w1 = ((xc - gx) * (ya - gy) - (xa - gx) * (yc - gy)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * sz[i, 0] + w1 * sz[i, 1] + w2 * sz[i, 2]
        zs = zbuf[iy0:iy1 + 1, ix0:ix1 + 1]
        hit = inside & (z > zs)
        zs[hit] = z[hit]
        img[iy0:iy1 + 1, ix0:ix1 + 1][hit] = c[i]
        nbuf[iy0:iy1 + 1, ix0:ix1 + 1][hit] = n[i]
    # outlines: silhouettes, creases, and depth steps found by the second difference
    # of depth, which stays near zero across a sloping face
    bg = ~np.isfinite(zbuf)
    zf = np.where(bg, -1e6, zbuf)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a_, b_ = (slice(0, H - dy), slice(0, W - dx)), (slice(dy, H), slice(dx, W))
        crease = ((nbuf[a_] * nbuf[b_]).sum(axis=2) < 0.82) | (bg[a_] != bg[b_])
        edge[a_] |= crease & ~bg[a_]
        edge[b_] |= crease & ~bg[b_]
        c_ = (slice(2 * dy, H), slice(2 * dx, W))
        a2 = (slice(0, H - 2 * dy), slice(0, W - 2 * dx))
        m2 = (slice(dy, H - dy), slice(dx, W - dx))
        edge[m2] |= (np.abs(zf[a2] - 2 * zf[m2] + zf[c_]) > 0.3) & ~bg[m2]
    img[edge] *= 0.3
    im = Image.fromarray(img.clip(0, 255).astype("uint8")).resize((W // ss, H // ss), Image.LANCZOS)
    if labels:
        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype(LABEL_FONT, 22)
        for text, p in labels:
            q = np.array([p.x, p.y, p.z])
            lx, ly = ((q @ rgt) - x0 + m) * k / ss, (y1 + m - (q @ up)) * k / ss
            draw.text((lx, ly), text, font=font, fill=(20, 24, 28), anchor="mm", stroke_width=4, stroke_fill=(255, 255, 255))
    im.save(path, optimize=True)
