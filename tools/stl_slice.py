"""Cut an STL with a plane and return the closed loops of the section (stdlib only).

Used by tools/kicad_templates.py to draw each case at its board plane.
"""
import math
import struct


def load(path):
    """Triangles of a binary or ASCII STL as [(x, y, z), (x, y, z), (x, y, z)]."""
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        tris, cur = [], []
        for line in data.decode(errors="ignore").splitlines():
            p = line.split()
            if p and p[0] == "vertex":
                cur.append(tuple(map(float, p[1:4])))
                if len(cur) == 3:
                    tris.append(cur)
                    cur = []
        return tris
    n = struct.unpack_from("<I", data, 80)[0]
    return [[v[3:6], v[6:9], v[9:12]] for v in (struct.unpack_from("<12f", data, 84 + 50 * i) for i in range(n))]


def section(tris, axis, at):
    """Closed loops where the plane {axis = at} cuts the mesh, in the two other coordinates."""
    o = [a for a in range(3) if a != axis]
    adj = {}
    for t in tris:
        pts = []
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            da, db = a[axis] - at, b[axis] - at
            if (da < 0) != (db < 0):
                s = da / (da - db)
                pts.append((round(a[o[0]] + s * (b[o[0]] - a[o[0]]), 4), round(a[o[1]] + s * (b[o[1]] - a[o[1]]), 4)))
        if len(pts) == 2:
            adj.setdefault(pts[0], []).append(pts[1])
            adj.setdefault(pts[1], []).append(pts[0])
    seen, loops = set(), []
    for start in adj:
        if start in seen:
            continue
        loop, cur, prev = [start], start, None
        seen.add(start)
        while True:
            nxt = [p for p in adj[cur] if p != prev and p not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            loop.append(cur)
        if len(loop) > 2:
            loops.append(loop)
    return loops


def area(loop):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]))) / 2


def simplify(loop, tol=0.05):
    """Ramer-Douglas-Peucker on a closed loop: keep the shape within tol mm."""
    if len(loop) < 4:
        return loop
    far = max(range(len(loop)), key=lambda k: math.dist(loop[k], loop[0]))
    return _rdp(loop[:far + 1], tol)[:-1] + _rdp(loop[far:] + [loop[0]], tol)[:-1]


def _rdp(pts, tol):
    keep = {0, len(pts) - 1}
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        (ax, ay), (bx, by) = pts[i], pts[j]
        d = math.hypot(bx - ax, by - ay)
        best, at = 0.0, None
        for k in range(i + 1, j):
            px, py = pts[k]
            dist = (abs((bx - ax) * (ay - py) - (by - ay) * (ax - px)) / d) if d else math.hypot(px - ax, py - ay)
            if dist > best:
                best, at = dist, k
        if at is not None and best > tol:
            keep.add(at)
            stack += [(i, at), (at, j)]
    return [pts[k] for k in sorted(keep)]
