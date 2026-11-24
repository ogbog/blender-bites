# SPDX-License-Identifier: GPL-3.0-or-later
"""The scrolly card: drawn straight onto the viewport, scrolled with the wheel."""
import math
import time

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from . import runner

FONT = 0
BG = (0.07, 0.07, 0.09, 0.92)
TEXT = (0.94, 0.94, 0.94, 1.0)
MUTED = (0.62, 0.62, 0.66, 1.0)
ACCENT = (1.0, 0.55, 0.12, 1.0)
GOOD = (0.35, 0.86, 0.45, 1.0)
AXIS = {"X": (1.0, 0.2, 0.3), "Y": (0.5, 0.86, 0.15), "Z": (0.2, 0.55, 1.0)}

# window-space hit zones, rebuilt every draw: name -> (x0, y0, x1, y1)
_zones = {}
_handles = []


def _ui_scale():
    return bpy.context.preferences.system.ui_scale


def _wrap(text, size, width):
    blf.size(FONT, size)
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            trial = word if not line else line + " " + word
            if blf.dimensions(FONT, trial)[0] <= width:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


def _rect(x, y, w, h, color):
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(
        shader, 'TRIS',
        {"pos": ((x, y), (x + w, y), (x + w, y + h), (x, y + h))},
        indices=((0, 1, 2), (2, 3, 0)),
    )
    shader.uniform_float("color", color)
    batch.draw(shader)


def _text(x, y, s, size, color):
    blf.size(FONT, size)
    blf.color(FONT, *color)
    blf.position(FONT, x, y, 0)
    blf.draw(FONT, s)
    return blf.dimensions(FONT, s)[0]


def _left_inset(region):
    """With region overlap on, the toolbar floats over the viewport region.
    Push the card right by however much of it overlaps."""
    area = bpy.context.area
    if area is None:
        return 0
    for r in area.regions:
        if r.type == 'TOOLS' and r.width > 1:
            return max(0, r.x + r.width - region.x)
    return 0


def draw_card():
    r = runner.get()
    region = bpy.context.region
    if not r.active or region is None or r.lesson is None:
        return
    s = _ui_scale()
    bite = r.bite
    passed = r.passed_at is not None
    pad, w = 18 * s, min(400 * s, region.width - 48 * s)
    inner = w - 2 * pad

    head = f"{r.lesson.get('title', '').upper()}    {r.idx + 1}/{r.count}"
    title_lines = _wrap(bite.get("title", ""), 22 * s, inner)
    body_lines = _wrap(bite.get("body", ""), 15 * s, inner)
    hint_lines = _wrap("Hint: " + bite["hint"], 13 * s, inner) if bite.get("hint") and r.show_hint() else []

    if time.monotonic() < r.toast_until:
        foot, foot_col = r.toast_text, ACCENT
    elif r.pending:
        foot, foot_col = "Rearranging the room...", MUTED
    elif r.is_read():
        foot, foot_col = "Scroll down on this card to continue", ACCENT
    elif passed:
        foot, foot_col = bite.get("praise", "Nailed it!"), GOOD
    elif time.monotonic() < r.nudge_until:
        foot, foot_col = "Do it in the viewport first!", ACCENT
    else:
        foot, foot_col = "Your turn: do it in the viewport", MUTED

    lh_title, lh_body, lh_small = 28 * s, 21 * s, 18 * s
    h = (pad + lh_small + 8 * s + lh_title * len(title_lines) + 6 * s
         + lh_body * len(body_lines) + (8 * s + lh_small * len(hint_lines) if hint_lines else 0)
         + 14 * s + lh_small + 12 * s + 8 * s + pad)

    x = _left_inset(region) + 24 * s
    y = region.height - 24 * s - h

    gpu.state.blend_set('ALPHA')
    _rect(x, y, w, h, BG)
    bar = GOOD if passed else ACCENT
    _rect(x, y, 5 * s, h, bar)

    cy = y + h - pad - 13 * s
    _text(x + pad, cy, head, 12 * s, MUTED)
    _text(x + w - pad - 40 * s, cy, "EXIT", 12 * s, MUTED)
    cy -= 8 * s
    for line in title_lines:
        cy -= lh_title
        _text(x + pad, cy + 6 * s, line, 22 * s, TEXT)
    cy -= 6 * s
    for line in body_lines:
        cy -= lh_body
        _text(x + pad, cy + 4 * s, line, 15 * s, TEXT)
    if hint_lines:
        cy -= 8 * s
        for line in hint_lines:
            cy -= lh_small
            _text(x + pad, cy + 4 * s, line, 13 * s, MUTED)
    cy -= 14 * s + lh_small
    _text(x + pad, cy + 4 * s, foot, 14 * s, foot_col)
    skip_x = None
    if not r.is_read() and not passed:
        skip_x = x + w - pad - 40 * s
        _text(skip_x, cy + 4 * s, "skip", 12 * s, MUTED)

    # progress dots
    cy -= 12 * s + 6 * s
    dot = 6 * s
    for i in range(r.count):
        col = GOOD if i < r.idx else (bar if i == r.idx else (0.3, 0.3, 0.34, 1.0))
        _rect(x + pad + i * (dot + 5 * s), cy, dot, dot, col)
    gpu.state.blend_set('NONE')

    # hit zones in window coordinates
    ox, oy = region.x, region.y
    _zones.clear()
    _zones["card"] = (ox + x, oy + y, ox + x + w, oy + y + h)
    ey = y + h - pad - 16 * s
    _zones["exit"] = (ox + x + w - pad - 46 * s, oy + ey, ox + x + w, oy + y + h)
    if skip_x is not None:
        _zones["skip"] = (ox + skip_x - 6 * s, oy + cy + 12 * s, ox + x + w, oy + cy + 12 * s + lh_small + 8 * s)


def draw_pulse():
    r = runner.get()
    region = bpy.context.region
    if not r.active or r.lesson is None or region is None:
        return
    pulse = r.bite.get("pulse")
    if not pulse or r.passed_at is not None:
        return
    obj = bpy.data.objects.get(pulse.get("object", "Cube"))
    if obj is None:
        return
    axis = pulse.get("axis_line", "X")
    c = obj.matrix_world.translation
    d = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis]
    a = (c[0] - d[0] * 50, c[1] - d[1] * 50, c[2] - d[2] * 50)
    b = (c[0] + d[0] * 50, c[1] + d[1] * 50, c[2] + d[2] * 50)
    t = 0.5 + 0.5 * math.sin(time.monotonic() * 5.0)
    shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": (a, b)})
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("lineWidth", (2.0 + 4.0 * t) * _ui_scale())
    shader.uniform_float("color", (*AXIS[axis], 0.35 + 0.5 * t))
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    batch.draw(shader)
    gpu.state.blend_set('NONE')


def _over_view3d(window, mx, my):
    for a in window.screen.areas:
        if a.type == 'VIEW_3D' and a.x <= mx <= a.x + a.width and a.y <= my <= a.y + a.height:
            return True
    return False


def _locked(r, context, event):
    """Shortcuts a lesson keeps locked until they're earned. Returns the message."""
    if event.value != 'PRESS' or r.lesson is None:
        return None
    for lock in r.lesson.get("locked", ()):
        if (event.type == lock.get("type")
                and event.shift == lock.get("shift", False)
                and event.ctrl == lock.get("ctrl", False)
                and event.alt == lock.get("alt", False)
                and context.window is not None
                and _over_view3d(context.window, event.mouse_x, event.mouse_y)):
            return lock.get("say", "Not yet! You'll earn that soon.")
    return None


def hit(mx, my):
    for name in ("exit", "skip", "card"):
        z = _zones.get(name)
        if z and z[0] <= mx <= z[2] and z[1] <= my <= z[3]:
            return name
    return None


class BITES_OT_card_input(bpy.types.Operator):
    """Listens for wheel and clicks over the lesson card, passes everything else through"""
    bl_idname = "bites.card_input"
    bl_label = "Blender Bites Card Input"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        r = runner.get()
        if not r.active:
            return {'FINISHED'}
        msg = _locked(r, context, event)
        if msg:
            r.toast(msg)
            return {'RUNNING_MODAL'}
        if event.type not in {'WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'LEFTMOUSE'}:
            return {'PASS_THROUGH'}
        zone = hit(event.mouse_x, event.mouse_y)
        if zone is None:
            return {'PASS_THROUGH'}
        if event.type == 'WHEELDOWNMOUSE':
            r.scroll_next()
        elif event.type == 'WHEELUPMOUSE':
            r.scroll_prev()
        elif event.value == 'PRESS':
            if zone == "exit":
                r.stop()
                return {'FINISHED'}
            if zone == "skip":
                r.next()
            elif r.is_read():
                r.next()
        return {'RUNNING_MODAL'}


def register():
    bpy.utils.register_class(BITES_OT_card_input)
    _handles.append(bpy.types.SpaceView3D.draw_handler_add(draw_card, (), 'WINDOW', 'POST_PIXEL'))
    _handles.append(bpy.types.SpaceView3D.draw_handler_add(draw_pulse, (), 'WINDOW', 'POST_VIEW'))


def unregister():
    for h in _handles:
        bpy.types.SpaceView3D.draw_handler_remove(h, 'WINDOW')
    _handles.clear()
    bpy.utils.unregister_class(BITES_OT_card_input)
