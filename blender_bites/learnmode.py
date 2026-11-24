# SPDX-License-Identifier: GPL-3.0-or-later
"""Learn mode: Blender Bites lives in its own throwaway workspace.

The user's own workspaces are never modified. On enter we duplicate the
active workspace into "Blender Bites", close every area except the main 3D
Viewport, then split in the editors the student has earned (Outliner,
Properties, Shader Editor, Timeline). On exit we delete that
workspace and switch back.

Blender 5.3 traps this module is built around:
- Workspace switches and deletes are deferred to the next event-loop pass,
  so layout changes run as a queue of small steps on a timer (one per tick).
- screen.area_split refuses to run inside a fullscreen screen.
- workspace.delete ignores temp_override(workspace=...) and deletes the
  window's ACTIVE workspace. Only call it while ours is active.
- SpaceView3D.show_region_* segfaults without temp_override(window, screen,
  area, region) when set from a timer.
- Focus mode (screen_full_area(use_hide_panels=True)) hides the window's top
  bar and status bar for good when left by script. We never fullscreen at all.
"""
from collections import deque

import bpy

WS_NAME = "Blender Bites"

REGION_FLAGS = {
    "header": "show_region_header",
    "toolbar": "show_region_toolbar",
    "sidebar": "show_region_ui",
    "hud": "show_region_hud",
    "tool_header": "show_region_tool_header",
    "asset_shelf": "show_region_asset_shelf",
}

# Earned editors, split in as they unlock. The original area always keeps the
# larger piece of a split, and `factor` puts the split line that far from the
# bottom (HORIZONTAL) or left (VERTICAL) edge.
EDITORS = {
    "outliner":   {"type": "OUTLINER", "from": "VIEW_3D", "side": "right", "share": 0.20},
    "properties": {"type": "PROPERTIES", "from": "OUTLINER", "side": "bottom", "share": 0.62},
    "shader":     {"ui_type": "ShaderNodeTree", "from": "VIEW_3D", "side": "bottom", "share": 0.40},
    "timeline":   {"ui_type": "TIMELINE", "from": "VIEW_3D", "side": "bottom", "share": 0.16},
}
EDITOR_ORDER = ("outliner", "properties", "shader", "timeline")

_state = {"active": False, "orig_ws": None, "unlocked": set()}
_steps = deque()
_MAX_TRIES = 80


# ---- helpers ---------------------------------------------------------
def _win():
    wins = bpy.context.window_manager.windows
    return wins[0] if len(wins) else None


def _size(a):
    return a.width * a.height


def _region(area):
    return next((r for r in area.regions if r.type == 'WINDOW'), None)


def _ctx(win, area=None):
    d = {"window": win, "screen": win.screen}
    if area is not None:
        d["area"] = area
        r = _region(area)
        if r is not None:
            d["region"] = r
    return d


def _main_view(screen):
    views = [a for a in screen.areas if a.type == 'VIEW_3D']
    return max(views, key=_size) if views else None


def find_view3d():
    """Largest 3D viewport across all windows: (window, area, region, space, rv3d)."""
    best = None
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            if best is None or _size(area) > _size(best[1]):
                best = (win, area)
    if best is None:
        return None
    win, area = best
    space = area.spaces.active
    return win, area, _region(area), space, space.region_3d


def _set_regions(v, **values):
    """Toggle space region flags with a full window/area/region context."""
    win, area, region, space, _ = v
    with bpy.context.temp_override(window=win, screen=win.screen, area=area, region=region):
        for k, val in values.items():
            if not hasattr(space, k) or getattr(space, k) == val:
                continue
            try:
                setattr(space, k, val)
            except Exception as e:
                print("[Bites] region toggle failed", k, e)
    area.tag_redraw()


def _away():
    """The student has clicked over to another workspace. Layout work must
    wait (and must never touch that workspace's areas). Marks the room dirty
    so the runner can rebuild it when they come back."""
    win = _win()
    if win is not None and win.workspace.name != WS_NAME and bpy.data.workspaces.get(WS_NAME):
        _state["dirty"] = True
        return True
    return False


def relayout_if_needed():
    """Called by the runner each tick: rebuild the room after a trip away."""
    win = _win()
    if _state.get("dirty") and not busy() and win is not None and win.workspace.name == WS_NAME:
        _state["dirty"] = False
        _queue(_step_prune, _step_layout, _make_regions(hide_rest=False))


# ---- step queue ------------------------------------------------------
def busy():
    return bool(_steps)


def _pump():
    if not _steps:
        return None
    fn, tries = _steps[0]
    try:
        done = fn()
    except Exception as e:
        print("[Bites] layout step failed:", getattr(fn, "__name__", fn), e)
        done = True
    if done or tries >= _MAX_TRIES:
        if not done:
            print("[Bites] layout step gave up:", getattr(fn, "__name__", fn))
        _steps.popleft()
    else:
        _steps[0] = (fn, tries + 1)
    return 0.05 if _steps else None


def _queue(*fns):
    _steps.extend((f, 0) for f in fns)
    if not bpy.app.timers.is_registered(_pump):
        bpy.app.timers.register(_pump, first_interval=0.05, persistent=True)


# ---- steps -----------------------------------------------------------
def _step_unfull():
    win = _win()
    if win and win.screen.show_fullscreen:
        with bpy.context.temp_override(**_ctx(win, win.screen.areas[0])):
            bpy.ops.screen.back_to_previous()
    return True


def _step_make_ws():
    win = _win()
    ws = bpy.data.workspaces.get(WS_NAME)
    if ws is not None:
        if win.workspace != ws:
            win.workspace = ws
        return True
    before = {w.name for w in bpy.data.workspaces}
    area = max(win.screen.areas, key=_size)
    with bpy.context.temp_override(**_ctx(win, area)):
        bpy.ops.workspace.duplicate()
    new = [w for w in bpy.data.workspaces if w.name not in before]
    if new:
        new[0].name = WS_NAME
        if win.workspace != new[0]:
            win.workspace = new[0]
    return True


def _step_wait_ws():
    win = _win()
    if win.workspace.name == WS_NAME:
        return True
    ws = bpy.data.workspaces.get(WS_NAME)
    if ws is not None and win.workspace != ws:
        win.workspace = ws
    return False


def _step_clean():
    """Close every area except the main 3D viewport, one per tick."""
    win = _win()
    if _away():
        return True
    scr = win.screen
    if scr.show_fullscreen:
        return _step_unfull() and False
    keep = _main_view(scr)
    if keep is None:
        max(scr.areas, key=_size).type = 'VIEW_3D'
        return False
    for a in scr.areas:
        if a != keep:
            with bpy.context.temp_override(**_ctx(win, a)):
                bpy.ops.screen.area_close()
            return False
    return True


def _is_editor(area, spec):
    if "ui_type" in spec:
        return area.ui_type == spec["ui_type"]
    return area.type == spec["type"]


def _find_area(screen, kind):
    if kind == 'VIEW_3D':
        return _main_view(screen)
    found = [a for a in screen.areas if a.type == kind or a.ui_type == kind]
    return max(found, key=_size) if found else None


def _set_editor(area, spec):
    if "ui_type" in spec:
        area.ui_type = spec["ui_type"]
    else:
        area.type = spec["type"]


def _split_for(win, scr, spec):
    src = _find_area(scr, spec["from"])
    if src is None:
        return
    side, share = spec["side"], spec["share"]
    direction = 'HORIZONTAL' if side in ("top", "bottom") else 'VERTICAL'
    target_first = side in ("bottom", "left")
    factor = share if target_first else 1.0 - share
    before = {a.as_pointer() for a in scr.areas}
    with bpy.context.temp_override(**_ctx(win, src)):
        bpy.ops.screen.area_split(direction=direction, factor=factor)
    new = [a for a in scr.areas if a.as_pointer() not in before]
    if not new:
        return
    new = new[0]
    new_is_first = factor < 0.5          # the original keeps the larger piece
    target = new if new_is_first == target_first else src
    if target is src:
        new.ui_type = src.ui_type        # the leftover piece keeps the source editor
    _set_editor(target, spec)
    if target.type == 'NODE_EDITOR':
        # A fresh node editor opens with its sidebar showing; a first look at
        # nodes should be just nodes.
        with bpy.context.temp_override(**_ctx(win, target)):
            target.spaces.active.show_region_ui = False


def _step_layout():
    """Split in every earned editor that isn't on screen yet, one per tick.

    No fullscreen or maximize: with every other area closed, the Bites screen
    already is one big viewport, and normal screens dodge a nest of traps.
    """
    win = _win()
    if _away():
        return True
    scr = win.screen
    if scr.show_fullscreen:
        _step_unfull()
        return False
    for name in EDITOR_ORDER:
        if name not in _state["unlocked"]:
            continue
        spec = EDITORS[name]
        if any(_is_editor(a, spec) for a in scr.areas):
            continue
        _split_for(win, scr, spec)
        return False
    return True


def _step_prune():
    """Close earned editors the current lesson doesn't list, one per tick."""
    win = _win()
    if _away():
        return True
    scr = win.screen
    for a in scr.areas:
        for name, spec in EDITORS.items():
            if name not in _state["unlocked"] and _is_editor(a, spec):
                with bpy.context.temp_override(**_ctx(win, a)):
                    bpy.ops.screen.area_close()
                return False
    return True


def _make_regions(hide_rest):
    def _step_regions():
        if _away():
            return True
        v = find_view3d()
        if v is None:
            return False
        flags = {}
        for name, flag in REGION_FLAGS.items():
            if name in _state["unlocked"]:
                flags[flag] = True
            elif hide_rest:
                flags[flag] = False
        if hide_rest:
            flags.update(show_gizmo=True, show_gizmo_navigate=True)
        _set_regions(v, **flags)
        return True
    return _step_regions


def _step_exit_delete():
    win = _win()
    ws = bpy.data.workspaces.get(WS_NAME)
    if ws is None:
        return True
    if win.workspace != ws:
        win.workspace = ws          # deferred; delete next tick
        return False
    if win.screen.show_fullscreen:
        _step_unfull()
        return False
    with bpy.context.temp_override(**_ctx(win, max(win.screen.areas, key=_size))):
        bpy.ops.workspace.delete()  # deletes the ACTIVE workspace, which is ours
    return True


def _step_exit_restore():
    win = _win()
    if win.workspace.name == WS_NAME:
        return False                # deletion still pending
    orig = bpy.data.workspaces.get(_state.get("orig_ws") or "")
    if orig is not None and win.workspace != orig:
        win.workspace = orig
    return True


# ---- public API ------------------------------------------------------
def enter(unlocked=()):
    win = _win()
    if win is None:
        raise RuntimeError("Blender Bites needs an open window.")
    if win.workspace.name != WS_NAME:
        _state["orig_ws"] = win.workspace.name
    _state["active"] = True
    _state["unlocked"] = set(unlocked)
    _steps.clear()
    _queue(_step_unfull, _step_make_ws, _step_wait_ws, _step_clean,
           _step_layout, _make_regions(hide_rest=True))


def unlock(what):
    if what in _state["unlocked"]:
        return
    _state["unlocked"].add(what)
    if what in EDITORS:
        _queue(_step_layout, _make_regions(hide_rest=False))
    elif what in REGION_FLAGS:
        if busy() or _away():
            _queue(_make_regions(hide_rest=False))
        else:
            v = find_view3d()
            if v is not None:
                _set_regions(v, **{REGION_FLAGS[what]: True})


def apply_lesson(unlocked):
    """Each lesson gets exactly the editors it lists; earned regions stay earned."""
    unlocked = set(unlocked)
    editors = {u for u in unlocked if u in EDITORS}
    regions = (_state["unlocked"] - set(EDITORS)) | {u for u in unlocked if u not in EDITORS}
    _state["unlocked"] = regions | editors
    _queue(_step_prune, _step_layout, _make_regions(hide_rest=False))


def exit():
    _steps.clear()
    _state["active"] = False
    _queue(_step_unfull, _step_exit_delete, _step_exit_restore)


def exit_now():
    """Best effort for add-on unregister: no queue, leave the workspace behind."""
    _steps.clear()
    _state["active"] = False
    try:
        _step_unfull()
        orig = bpy.data.workspaces.get(_state.get("orig_ws") or "")
        win = _win()
        if orig is not None and win is not None:
            win.workspace = orig
    except Exception as e:
        print("[Bites] exit_now", e)


def reset():
    _steps.clear()
    _state["active"] = False
    _state["dirty"] = False


def start_card_modal():
    win = _win()
    if win is None:
        return
    with bpy.context.temp_override(window=win):
        bpy.ops.bites.card_input('INVOKE_DEFAULT')
