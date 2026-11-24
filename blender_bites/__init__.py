# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender Bites: learn Blender one bite at a time, starting from one viewport."""
import bpy
from bpy.app.handlers import persistent

from . import card, checks, explain, learnmode, runner


class BITES_OT_start(bpy.types.Operator):
    """Start Blender Bites in its own workspace (empty lesson = continue where you left off)"""
    bl_idname = "bites.start"
    bl_label = "Start Blender Bites"

    lesson: bpy.props.StringProperty(default="", options={'SKIP_SAVE'})

    def execute(self, context):
        r = runner.get()
        try:
            r.start(self.lesson)
        except Exception as e:
            self.report({'ERROR'}, f"Blender Bites could not start: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}


class BITES_OT_stop(bpy.types.Operator):
    """Leave Learn mode and go back to your own workspace"""
    bl_idname = "bites.stop"
    bl_label = "Exit Blender Bites"

    def execute(self, context):
        runner.get().stop()
        return {'FINISHED'}


class BITES_MT_lessons(bpy.types.Menu):
    bl_idname = "BITES_MT_lessons"
    bl_label = "Blender Bites"

    def draw(self, context):
        layout = self.layout
        r = runner.get()
        layout.operator("bites.start", text="Continue", icon='PLAY').lesson = ""
        layout.separator()
        done = set(runner.load_progress().get("completed", []))
        for entry in runner.lesson_index():
            if not (runner.CONTENT / f"{entry['id']}.json").exists():
                layout.label(text=entry["title"], icon='TIME')
                continue
            icon = 'CHECKMARK' if entry["id"] in done else 'DOT'
            layout.operator("bites.start", text=entry["title"], icon=icon).lesson = entry["id"]
        if r.active:
            layout.separator()
            layout.operator("bites.stop", icon='CANCEL')


def help_menu(self, context):
    self.layout.separator()
    self.layout.menu("BITES_MT_lessons", icon='LIGHT')


@persistent
def _on_load_pre(*_):
    # A new file replaces our workspace and screens; just drop our state.
    runner.get().active = False
    learnmode.reset()


CLASSES = (BITES_OT_start, BITES_OT_stop, BITES_MT_lessons)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    card.register()
    explain.register()
    checks.register()
    bpy.types.TOPBAR_MT_help.append(help_menu)
    bpy.app.handlers.load_pre.append(_on_load_pre)


def unregister():
    r = runner.get()
    if r.active:
        r.active = False
        learnmode.exit_now()
    if _on_load_pre in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_on_load_pre)
    bpy.types.TOPBAR_MT_help.remove(help_menu)
    checks.unregister()
    explain.unregister()
    card.unregister()
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
