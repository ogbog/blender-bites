# SPDX-License-Identifier: GPL-3.0-or-later
"""EXPLAIN: hover anything + F1, or right-click > EXPLAIN, get a plain-language card."""
import json
import textwrap
import time
from pathlib import Path

import bpy
from bpy_extras import view3d_utils

CONTENT = Path(__file__).parent / "content"
_db = None
_keymaps = []
# Last thing explained, for "explained" checks: {"key": ..., "t": monotonic}
LAST = {}


def db():
    """explain_db.json plus any explain_db_*.json, merged (later files win)."""
    global _db
    if _db is None:
        _db = {}
        for f in sorted(CONTENT.glob("explain_db*.json")):
            try:
                _db.update(json.loads(f.read_text(encoding="utf-8")))
            except Exception as e:
                print("[Bites] explain db failed to load", f.name, e)
    return _db


def _op_rna_id(idname):
    mod, _, fn = idname.partition("_OT_")
    return f"bpy.ops.{mod.lower()}.{fn}"


def _manual_url(rna_id):
    if not rna_id:
        return None
    try:
        from bl_operators.wm import WM_OT_doc_view_manual
        return WM_OT_doc_view_manual._lookup_rna_url(rna_id, verbose=False)
    except Exception:
        return None


def resolve(context, event=None):
    """Work out what the user is pointing at. Returns a dict for the popup."""
    entries = db()
    op = getattr(context, "button_operator", None)
    prop = getattr(context, "button_prop", None)
    ptr = getattr(context, "button_pointer", None)

    if op is not None:
        idname = op.bl_rna.identifier
        if idname == "WM_OT_tool_set_by_id" and getattr(op, "name", ""):
            key = "tool:" + op.name
            rna_id = None
        else:
            key, rna_id = idname, _op_rna_id(idname)
        found = entries.get(key)
        if found:
            return dict(found, key=key, url=_manual_url(rna_id), source="bites")
        rna = op.bl_rna
        return {"key": key, "title": rna.name or key, "body": rna.description or "",
                "url": _manual_url(rna_id), "source": "blender"}

    if prop is not None and ptr is not None:
        owner = ptr.bl_rna.identifier
        key = f"{owner}.{prop.identifier}"
        rna_id = f"bpy.types.{key}"
        # Walk up the class chain so one "Light.energy" entry covers AreaLight,
        # PointLight, SpotLight and SunLight (likewise Modifier.show_viewport).
        rna = ptr.bl_rna
        while rna is not None:
            k = f"{rna.identifier}.{prop.identifier}"
            found = entries.get(k)
            if found:
                return dict(found, key=key, url=_manual_url(rna_id), source="bites")
            rna = rna.base
        return {"key": key, "title": prop.name or prop.identifier, "body": prop.description or "",
                "url": _manual_url(rna_id), "source": "blender"}

    area = context.area
    if area is not None and area.type == 'VIEW_3D' and event is not None:
        obj = _object_under_mouse(context, event)
        if obj is not None:
            base = entries.get("viewport.object." + obj.type) or entries.get("viewport.object", {})
            return {"key": "viewport.object", "title": f"{obj.name} ({obj.type.title()})",
                    "body": base.get("body", ""), "try": base.get("try"), "shortcut": base.get("shortcut"),
                    "url": None, "source": "bites"}
    if area is not None:
        key = "area." + area.type
        found = entries.get(key)
        if found:
            return dict(found, key=key, url=None, source="bites")
    return entries.get("fallback", {"title": "Hmm", "body": "Nothing here to explain yet."})


def _object_under_mouse(context, event):
    region, rv3d = context.region, context.region_data
    if region is None or rv3d is None or region.type != 'WINDOW':
        return None
    co = (event.mouse_region_x, event.mouse_region_y)
    origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, co)
    direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, co)
    hit, _loc, _n, _i, obj, _m = context.scene.ray_cast(
        context.evaluated_depsgraph_get(), origin, direction)
    return obj if hit else None


class BITES_OT_explain(bpy.types.Operator):
    """Explain this in plain language (Blender Bites)"""
    bl_idname = "bites.explain"
    bl_label = "Explain"

    def invoke(self, context, event):
        self.info = resolve(context, event)
        LAST.clear()
        LAST.update(key=self.info.get("key", ""), t=time.monotonic())
        width = int(440 * context.preferences.system.ui_scale)
        return context.window_manager.invoke_popup(self, width=width)

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        info = getattr(self, "info", None) or {}
        layout = self.layout
        col = layout.column(align=False)
        col.label(text=info.get("title", "?"), icon='QUESTION')
        chars = 62
        body = col.column(align=True)
        for line in textwrap.wrap(info.get("body", ""), chars) or [""]:
            body.label(text=line)
        if info.get("shortcut"):
            col.separator()
            col.label(text="Shortcut: " + info["shortcut"], icon='EVENT_F')
        if info.get("try"):
            col.separator()
            tri = col.column(align=True)
            for i, line in enumerate(textwrap.wrap("Try it: " + info["try"], chars)):
                tri.label(text=line, icon='PLAY' if i == 0 else 'BLANK1')
        col.separator()
        row = col.row()
        if info.get("url"):
            row.operator("wm.url_open", text="Full manual page", icon='HELP').url = info["url"]
        src = "Blender Bites (CC-BY-SA 4.0)" if info.get("source") == "bites" else "Blender's own tooltip"
        row.label(text=src)


def button_menu(self, context):
    if getattr(context, "button_prop", None) or getattr(context, "button_operator", None):
        self.layout.separator()
        self.layout.operator("bites.explain", text="EXPLAIN", icon='QUESTION')


def object_menu(self, context):
    self.layout.separator()
    self.layout.operator("bites.explain", text="EXPLAIN", icon='QUESTION')


def register():
    bpy.utils.register_class(BITES_OT_explain)
    bpy.types.UI_MT_button_context_menu.append(button_menu)
    bpy.types.VIEW3D_MT_object_context_menu.append(object_menu)
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        for name, space in (("Window", 'EMPTY'), ("User Interface", 'EMPTY'), ("3D View", 'VIEW_3D')):
            km = kc.keymaps.new(name=name, space_type=space)
            kmi = km.keymap_items.new("bites.explain", 'F1', 'PRESS')
            _keymaps.append((km, kmi))


def unregister():
    for km, kmi in _keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _keymaps.clear()
    bpy.types.VIEW3D_MT_object_context_menu.remove(object_menu)
    bpy.types.UI_MT_button_context_menu.remove(button_menu)
    bpy.utils.unregister_class(BITES_OT_explain)
