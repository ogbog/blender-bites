# SPDX-License-Identifier: GPL-3.0-or-later
"""Challenge checks. Every check is data in the lesson JSON, dispatched here.

Generic checks ("space", "object", "count") read any RNA path, so most new
bites need no Python at all. Comparison ops: eq (default), ne, approx (with
tol), ge, gt, le, lt, in.
"""
import math
import re
import time

import bpy
from mathutils import Vector

from . import explain
from .learnmode import find_view3d


# ---- helpers ---------------------------------------------------------
def _objs(spec, key="object", prefix_key="prefix"):
    """Objects named by spec: exact name, or every scene object with a prefix."""
    otype = spec.get("object_type")
    scene_objs = bpy.context.scene.objects
    if spec.get("any"):
        found = list(scene_objs)
    elif spec.get(prefix_key):
        found = [o for o in scene_objs if o.name.startswith(spec[prefix_key])]
    else:
        o = bpy.data.objects.get(spec.get(key, "Cube"))
        found = [o] if o is not None and o.name in scene_objs else []
    if otype:
        found = [o for o in found if o.type == otype]
    return found


def _obj(spec):
    found = _objs(spec)
    return found[0] if found else None


def _bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def _bbox_center(obj):
    lo, hi = _bbox(obj)
    return (lo + hi) / 2


_MISSING = object()
_TOKEN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(\(\))?((?:\[[^\]]+\])*)")


def _resolve(root, path):
    """Walk an RNA path. Supports attr, attr[0], attr['Name'], and method().
    Anything missing (None parent, bad key) resolves to _MISSING, never raises."""
    cur = root
    for part in path.split("."):
        if cur is None or cur is _MISSING:
            return _MISSING
        m = _TOKEN.fullmatch(part)
        if not m:
            return _MISSING
        name, call, idx = m.groups()
        try:
            cur = getattr(cur, name)
            if call:
                cur = cur()
            for key in re.findall(r"\[([^\]]+)\]", idx or ""):
                key = key.strip()
                if key[0] in "'\"":
                    cur = cur[key[1:-1]]
                else:
                    cur = cur[int(key)]
        except Exception:
            return _MISSING
    return cur


def _match(want, got):
    if isinstance(want, (list, tuple)):
        try:
            got = tuple(got)
        except TypeError:
            return False
        if len(want) != len(got):
            return False
        return all(_match(w, g) for w, g in zip(want, got))
    if isinstance(want, bool) or isinstance(got, bool):
        return bool(want) == bool(got)
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return abs(want - got) < 1e-3
    return want == got


def _cmp(got, op="eq", want=None, tol=1e-3):
    if got is _MISSING or (got is None and op in ("present", "missing")):
        return op == "missing"
    if op == "present":
        return True
    if op == "eq":
        return _match(want, got)
    if op == "ne":
        return not _match(want, got)
    if op == "approx":
        return abs(float(got) - float(want)) <= tol
    if op == "in":
        return got in want
    got, want = float(got), float(want)
    return {"ge": got >= want, "gt": got > want, "le": got <= want, "lt": got < want}.get(op, False)


def _freeze(v):
    if isinstance(v, (str, bool, int, float)) or v is None or v is _MISSING:
        return v
    try:
        return tuple(_freeze(x) for x in v)
    except TypeError:
        return v


def _spec_cmp(got, spec, snap=None, key=None):
    """Compare per spec. op "changed" compares against the value seen on the
    first evaluation after the bite was armed."""
    op = spec.get("op", "eq")
    if op == "changed":
        if snap is None:
            return False
        base = snap.setdefault("_base", {})
        k = (id(spec), key)
        now = _freeze(got)
        if k not in base:
            base[k] = now
            return False
        return not _match(base[k], now) if now is not _MISSING else False
    return _cmp(got, op, spec.get("value"), spec.get("tol", 1e-3))


def snapshot(object_names=("Cube",)):
    v = find_view3d()
    rv = v[4] if v else None
    scene = bpy.context.scene
    snap = {"objs": {}, "t": time.monotonic(),
            "names": {o.name for o in scene.objects},
            "cursor": scene.cursor.location.copy()}
    if rv:
        snap["view_rot"] = rv.view_rotation.copy()
        snap["view_dist"] = rv.view_distance
        snap["view_loc"] = rv.view_location.copy()
    for i, o in enumerate(scene.objects):
        if i > 400:
            break
        snap["objs"][o.name] = {
            "loc": o.matrix_world.translation.copy(),
            "scale": o.scale.copy(),
            "matrix": o.matrix_world.copy(),
        }
    return snap


def _rv3d():
    v = find_view3d()
    return v[4] if v else None


# ---- view checks -----------------------------------------------------
def c_read(spec, snap, log):
    return False


def c_view_rotated(spec, snap, log):
    rv = _rv3d()
    if not rv or "view_rot" not in snap:
        return False
    ang = snap["view_rot"].rotation_difference(rv.view_rotation).angle
    return math.degrees(ang) >= spec.get("degrees", 25)


def c_view_zoomed(spec, snap, log):
    rv = _rv3d()
    if not rv or not snap.get("view_dist"):
        return False
    ratio = rv.view_distance / snap["view_dist"]
    f = spec.get("factor", 1.4)
    return ratio >= f or ratio <= 1.0 / f


def c_view_panned(spec, snap, log):
    rv = _rv3d()
    if not rv or "view_loc" not in snap:
        return False
    return (rv.view_location - snap["view_loc"]).length >= spec.get("distance", 0.6)


def c_view_axis(spec, snap, log):
    rv = _rv3d()
    if not rv:
        return False
    look = rv.view_rotation @ Vector((0.0, 0.0, -1.0))
    return look.dot(Vector(spec["direction"]).normalized()) > 0.995


def c_view_framed(spec, snap, log):
    rv, o = _rv3d(), _obj(spec)
    if not rv or not o:
        return False
    near = (rv.view_location - _bbox_center(o)).length < spec.get("tolerance", 0.35)
    moved = (rv.view_location - snap.get("view_loc", rv.view_location)).length > 0.05
    return near and moved


# ---- object checks ---------------------------------------------------
def c_selected(spec, snap, log):
    o = _obj(spec)
    return bool(o and o.select_get() and bpy.context.view_layer.objects.active == o)


def c_moved(spec, snap, log):
    for o in _objs(spec):
        before = snap["objs"].get(o.name)
        if before and (o.matrix_world.translation - before["loc"]).length >= spec.get("distance", 0.3):
            return True
    return False


def c_scale_is(spec, snap, log):
    o = _obj(spec)
    if not o:
        return False
    return (o.scale - Vector(spec.get("scale", (1, 1, 1)))).length < spec.get("tolerance", 0.01)


def _root(name):
    v = find_view3d()
    win = bpy.context.window_manager.windows[0]
    scene = bpy.context.scene
    if name == "space":
        return v[3] if v else _MISSING
    if name == "rv3d":
        return v[4] if v else _MISSING
    if name == "scene":
        return scene
    if name == "tool_settings":
        return scene.tool_settings
    if name == "render":
        return scene.render
    if name == "window":
        return win
    if name == "screen":
        return win.screen
    if name == "data":
        return bpy.data
    if name == "view_layer":
        return bpy.context.view_layer
    if name.startswith("area:"):
        kind = name[5:]
        found = [a for a in win.screen.areas if a.type == kind or a.ui_type == kind]
        return max(found, key=lambda a: a.width * a.height) if found else _MISSING
    return _MISSING


def c_prop(spec, snap, log):
    """Any property path from a root: space, rv3d, scene, tool_settings, render,
    window, screen, data, view_layer, area:<TYPE or ui_type>."""
    root = _root(spec.get("root", "space"))
    if root is _MISSING:
        return False
    return _spec_cmp(_resolve(root, spec["path"]), spec, snap)


def c_space(spec, snap, log):
    """Any property path on the main 3D View space, e.g. shading.type."""
    return c_prop(dict(spec, root="space"), snap, log) if "root" not in spec else c_prop(spec, snap, log)


def c_object(spec, snap, log):
    """Any property path on an object (or any object with a prefix)."""
    return any(_spec_cmp(_resolve(o, spec["path"]), spec, snap, o.name) for o in _objs(spec))


def _mesh_counts(o):
    if o.type != 'MESH':
        return None
    if o.mode == 'EDIT':
        import bmesh
        bm = bmesh.from_edit_mesh(o.data)
        return {"verts": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
                "sel_verts": sum(v.select for v in bm.verts),
                "sel_edges": sum(e.select for e in bm.edges),
                "sel_faces": sum(f.select for f in bm.faces),
            "max_mat": max((f.material_index for f in bm.faces), default=0)}
    me = o.data
    return {"verts": len(me.vertices), "edges": len(me.edges), "faces": len(me.polygons),
            "sel_verts": sum(v.select for v in me.vertices),
            "sel_edges": sum(e.select for e in me.edges),
            "sel_faces": sum(p.select for p in me.polygons),
            "max_mat": max((p.material_index for p in me.polygons), default=0)}


def c_mesh(spec, snap, log):
    """Geometry counts: verts/edges/faces/sel_*. "rel": true compares the change
    since the bite started (baseline taken on first evaluation)."""
    what = spec.get("what", "faces")
    for o in _objs(spec):
        counts = _mesh_counts(o)
        if counts is None:
            continue
        got = counts[what]
        if spec.get("rel"):
            base = snap.setdefault("_base", {})
            k = (id(spec), o.name, what)
            if k not in base:
                base[k] = got
                continue
            got = got - base[k]
        if _cmp(got, spec.get("op", "ge"), spec.get("value", 1)):
            return True
    return False


def c_modifier(spec, snap, log):
    """An object carries a modifier of a type, optionally with property values."""
    want = spec.get("props", {})
    need = spec.get("count", 1)
    for o in _objs(spec):
        hits = 0
        for md in getattr(o, "modifiers", ()):
            if spec.get("mod_type") and md.type != spec["mod_type"]:
                continue
            if all(_spec_cmp(_resolve(md, k), v if isinstance(v, dict) else {"value": v}) for k, v in want.items()):
                hits += 1
        if hits >= need:
            return True
    return False


def c_modifier_count(spec, snap, log):
    return any(_cmp(len(o.modifiers), spec.get("op", "ge"), spec.get("value", 1)) for o in _objs(spec))


def _materials(o):
    return [s.material for s in getattr(o, "material_slots", ()) if s.material is not None]


def c_node(spec, snap, log):
    """A material node of a type exists; with "linked_to", it feeds that input
    (by name) of any node, e.g. TEX_NOISE into Base Color."""
    for o in _objs(spec):
        for mat in _materials(o):
            nt = getattr(mat, "node_tree", None)
            if nt is None:
                continue
            if not any(n.type == spec["node_type"] for n in nt.nodes):
                continue
            target = spec.get("linked_to")
            if not target:
                return True
            for link in nt.links:
                if link.from_node.type == spec["node_type"] and link.to_socket.name == target:
                    return True
    return False


def _fcurves(o):
    ad = getattr(o, "animation_data", None)
    if ad is None or ad.action is None:
        return []
    try:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
        return list(cb.fcurves) if cb else []
    except Exception:
        return list(getattr(ad.action, "fcurves", []))


def c_keyframes(spec, snap, log):
    """Distinct keyframe frames on channels whose data_path starts with a prefix."""
    prefix = spec.get("path_prefix", "")
    for o in _objs(spec):
        frames = set()
        for fc in _fcurves(o):
            if fc.data_path.startswith(prefix):
                frames.update(round(k.co.x, 2) for k in fc.keyframe_points)
        if _cmp(len(frames), spec.get("op", "ge"), spec.get("value", 1)):
            return True
    return False


RENDERS = {"t": 0.0, "count": 0}


def _on_render_complete(*_):
    RENDERS["t"] = time.monotonic()
    RENDERS["count"] += 1


def c_rendered(spec, snap, log):
    return RENDERS["t"] >= snap.get("t", 0)


SAVES = {"t": 0.0}


def _on_save_post(*_):
    SAVES["t"] = time.monotonic()


def c_saved(spec, snap, log):
    return SAVES["t"] >= snap.get("t", 0)


def c_transformed(spec, snap, log):
    """An object's world matrix changed since the bite started (move, turn, scale)."""
    for o in _objs(spec):
        before = snap["objs"].get(o.name)
        if before is None:
            continue
        m0, m1 = before["matrix"], o.matrix_world
        if any(abs(m0[i][j] - m1[i][j]) > spec.get("tol", 1e-3) for i in range(4) for j in range(4)):
            return True
    return False


def c_count(spec, snap, log):
    return _cmp(len(_objs(spec)), spec.get("op", "ge"), spec.get("value", 1))


def c_added(spec, snap, log):
    return any(o.name not in snap.get("names", ()) for o in _objs(spec))


def c_gone(spec, snap, log):
    return not _objs(spec)


def c_cursor_moved(spec, snap, log):
    cur = bpy.context.scene.cursor.location
    return (cur - snap.get("cursor", cur)).length >= spec.get("distance", 0.5)


def c_stacked(spec, snap, log):
    """An object sits on top of another: resting on its top face, roughly centered."""
    base = _obj({"object": spec.get("base", "Cube")})
    tops = _objs({"prefix": spec.get("top", "Suzanne")})
    if base is None or not tops:
        return False
    blo, bhi = _bbox(base)
    reach = max(bhi.x - blo.x, bhi.y - blo.y) / 2 + spec.get("slack", 0.3)
    bc = (blo + bhi) / 2
    for t in tops:
        tlo, thi = _bbox(t)
        tc = (tlo + thi) / 2
        resting = bhi.z - spec.get("sink", 0.35) <= tlo.z <= bhi.z + spec.get("hover", 1.0)
        centered = math.hypot(tc.x - bc.x, tc.y - bc.y) <= reach
        if resting and centered:
            return True
    return False


def c_mode(spec, snap, log):
    return _cmp(bpy.context.mode, spec.get("op", "eq"), spec.get("value", "OBJECT"))


def c_explained(spec, snap, log):
    last = explain.LAST
    if not last or last.get("t", 0) < snap.get("t", 0):
        return False
    return last.get("key", "").startswith(spec.get("key", ""))


# ---- operator log ----------------------------------------------------
def c_operator(spec, snap, log):
    want = spec.get("props", {})
    for rec in log.records:
        if rec["id"] != spec["idname"]:
            continue
        ok = True
        for k, v in want.items():
            if k not in rec:
                ok = False
            elif isinstance(v, dict):
                ok = _spec_cmp(rec[k], v)
            else:
                ok = _match(v, rec[k])
            if not ok:
                break
        if ok:
            return True
    return False


# ---- combinators -----------------------------------------------------
def c_all(spec, snap, log):
    return all(run(s, snap, log) for s in spec["checks"])


def c_any(spec, snap, log):
    return any(run(s, snap, log) for s in spec["checks"])


def c_not(spec, snap, log):
    return not run(spec["check"], snap, log)


def c_seq(spec, snap, log):
    """Checks that must pass in order (toggle off, then back on)."""
    progress = snap.setdefault("_seq", {})
    i = progress.get(id(spec), 0)
    steps = spec["checks"]
    if i < len(steps) and run(steps[i], snap, log):
        i += 1
        progress[id(spec)] = i
    return i >= len(steps)


CHECKS = {
    "read": c_read,
    "view_rotated": c_view_rotated,
    "view_zoomed": c_view_zoomed,
    "view_panned": c_view_panned,
    "view_axis": c_view_axis,
    "view_framed": c_view_framed,
    "selected": c_selected,
    "moved": c_moved,
    "scale_is": c_scale_is,
    "space": c_space,
    "prop": c_prop,
    "mesh": c_mesh,
    "modifier": c_modifier,
    "modifier_count": c_modifier_count,
    "node": c_node,
    "keyframes": c_keyframes,
    "rendered": c_rendered,
    "saved": c_saved,
    "transformed": c_transformed,
    "object": c_object,
    "count": c_count,
    "added": c_added,
    "gone": c_gone,
    "cursor_moved": c_cursor_moved,
    "stacked": c_stacked,
    "mode": c_mode,
    "explained": c_explained,
    "operator": c_operator,
    "all": c_all,
    "any": c_any,
    "not": c_not,
    "seq": c_seq,
}


def run(spec, snap, log):
    fn = CHECKS.get(spec.get("type", "read"))
    if fn is None:
        print("[Bites] unknown check", spec)
        return False
    try:
        return fn(spec, snap, log)
    except Exception as e:  # a broken check should never break Blender
        print("[Bites] check error", spec.get("type"), e)
        return False


_HANDLERS = (("render_complete", _on_render_complete), ("save_post", _on_save_post))


def register():
    for name, fn in _HANDLERS:
        lst = getattr(bpy.app.handlers, name)
        if fn not in lst:
            lst.append(fn)


def unregister():
    for name, fn in _HANDLERS:
        lst = getattr(bpy.app.handlers, name)
        if fn in lst:
            lst.remove(fn)
